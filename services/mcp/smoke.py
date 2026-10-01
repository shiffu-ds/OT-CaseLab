"""Disposable migration/seed/real MCP round-trip with fictional data only."""

from __future__ import annotations

import argparse
import asyncio
import copy
import hashlib
import json
import os
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path


async def exercise(output: Path):
    # Environment is fixed before API database modules are imported.
    with tempfile.TemporaryDirectory(prefix="otcaselab-mcp-smoke-") as directory:
        os.environ.update(
            {
                "DATABASE_URL": f"sqlite:///{directory}/fixture.db",
                "ENVIRONMENT": "development",
                "MCP_TRANSPORT": "stdio",
                "MCP_SERVICE_SECRET": "disposable-protocol-smoke-service-secret-" * 2,
                "NLP_MODE": "baseline",
                "PROVIDER_MODE": "scripted",
                "ALLOW_DEMO": "true",
            }
        )
        from alembic import command
        from alembic.config import Config
        from sqlalchemy import func, select

        from ai.agent import run_feedback
        from services.api.config import ROOT, get_settings
        from services.api.database import SessionLocal, engine
        from services.api.models import (
            Attempt,
            CaseVersion,
            Feedback,
            Message,
            RubricVersion,
            Submission,
        )
        from services.api.seed import seed_content, seed_user
        from services.mcp.auth import issue_token
        from services.mcp.client import ToolError, connect

        get_settings.cache_clear()
        command.upgrade(Config(str(ROOT / "alembic.ini")), "head")
        content = {
            "profile": "The priority is morning dressing. Ask about support and routine.",
            "observations": "I observe a chair and door. Measure the space before interpreting access.",
            "goals": "Goal: choose clothes and dress before breakfast. Review agreed minutes.",
            "rationale": "Because the priority matters, ask about uncertainty and educator review.",
            "evidence_ids": [],
        }
        with SessionLocal() as db:
            seed_content(db)
            owner, _ = seed_user(db, "smoke-owner@example.test", "Fictional learner")
            other, _ = seed_user(db, "smoke-other@example.test", "Other fictional learner")
            version = db.scalar(select(CaseVersion).where(CaseVersion.case_id == "stroke-home"))
            rubric = db.scalar(
                select(RubricVersion).where(RubricVersion.case_version_id == version.id)
            )
            attempt = Attempt(
                user_id=owner.id,
                case_version_id=version.id,
                rubric_version_id=rubric.id,
                state="evaluating",
                draft=content,
            )
            db.add(attempt)
            db.flush()
            db.add(
                Submission(
                    attempt_id=attempt.id,
                    content=content,
                    checksum=hashlib.sha256(json.dumps(content).encode()).hexdigest(),
                    idempotency_key="disposable-smoke-submission",
                )
            )
            db.add(
                Message(
                    attempt_id=attempt.id,
                    role="student",
                    text="What is important in your routine? Who provides support?",
                    ordinal=1,
                )
            )
            db.add(
                Message(
                    attempt_id=attempt.id,
                    role="patient",
                    text="I want to choose my own clothes.",
                    ordinal=2,
                    provenance={"fact_ids": ["stroke-home-priority"]},
                )
            )
            db.commit()
            scope = {
                "user_id": owner.id,
                "attempt_id": attempt.id,
                "cohort_id": "demo",
                "permissions": ["read", "analyze", "write"],
                "exp": int(time.time()) + 120,
            }
            other_id = other.id
        report = await run_feedback(scope, content)
        checks = {
            "initialized": report["mcp"]["initialized"],
            "discovered_tools": len(report["mcp"]["discovered_tools"]),
            "actual_tool_calls": len(report["trace"]),
            "all_calls_completed": all(e["status"] == "completed" for e in report["trace"]),
            "migrations_applied": True,
        }
        async with connect(issue_token({**scope, "user_id": other_id})) as client:
            try:
                await client.call("get_case_context")
                raise AssertionError("Cross-owner tool call unexpectedly succeeded")
            except ToolError:
                checks["cross_owner_rejected"] = True
        retry = copy.deepcopy(report)
        retry.pop("feedback_id", None)
        for event in retry["trace"]:
            if event["tool"] == "save_feedback":
                event["status"] = "requested"
        key = hashlib.sha256(
            (
                scope["attempt_id"]
                + ":"
                + json.dumps(content, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
            ).encode()
        ).hexdigest()
        async with connect(issue_token(scope)) as client:
            saved = await client.call("save_feedback", report=retry, idempotency_key=key)
            checks["idempotent_write_retry"] = saved["idempotent_retry"]
        with SessionLocal() as db:
            checks["persisted_feedback_count"] = db.scalar(
                select(func.count()).select_from(Feedback)
            )
        engine.dispose()
        artifact = {
            "executed_at": datetime.now(UTC).isoformat(),
            "status": "actual_official_mcp_stdio_smoke",
            "data": "disposable fictional fixture",
            "checks": checks,
            "report": report,
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(artifact, indent=2, ensure_ascii=False) + "\n")
        print(json.dumps({"output": str(output), "status": artifact["status"], "checks": checks}))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("ml/reports/mcp-protocol-smoke.json"))
    args = parser.parse_args()
    asyncio.run(exercise(args.output))


if __name__ == "__main__":
    main()
