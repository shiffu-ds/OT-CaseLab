"""Bounded feedback state machine that actually invokes Model Context Protocol.

Default decisions are explicit rules. Optional Claude planning chooses the order
of analysis actions from an allowlist; it cannot supply arguments or identities.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import time
import uuid

from services.mcp.auth import issue_token
from services.mcp.client import connect


async def run_feedback(scope: dict, submission: dict) -> dict:
    from services.api.config import get_settings

    settings = get_settings()
    trace_id = str(uuid.uuid4())
    started = time.monotonic()
    trace = []
    calls = 0
    budget = min(8, max(1, settings.agent_max_calls))
    deadline = float(settings.agent_deadline_seconds)
    token = issue_token(scope)
    mode = "bounded_rule_workflow"

    async def work():
        nonlocal calls, mode
        async with connect(token) as client:

            async def call(name: str, **arguments):
                nonlocal calls
                if calls >= budget or time.monotonic() - started >= deadline:
                    raise RuntimeError("Feedback workflow action/deadline budget exhausted")
                calls += 1
                t = time.monotonic()
                result = await client.call(name, **arguments)
                trace.append(
                    {
                        "step": calls,
                        "tool": name,
                        "status": "completed",
                        "elapsed_ms": round((time.monotonic() - t) * 1000, 2),
                    }
                )
                return result

            await call("get_case_context")
            actions = (
                ["extract_profile", "search_approved_evidence"]
                if str(submission.get("profile", "")).strip()
                else ["search_approved_evidence"]
            )
            if os.getenv("AGENT_PLANNER", "rule") == "anthropic" and len(actions) > 1:
                from .providers import choose_agent_action

                chosen = await asyncio.to_thread(
                    choose_agent_action,
                    {
                        "profile_characters": len(str(submission.get("profile", ""))),
                        "rationale_characters": len(str(submission.get("rationale", ""))),
                        "eligible_actions": actions,
                    },
                    actions,
                )
                actions.remove(chosen)
                actions.insert(0, chosen)
                mode = "bounded_anthropic_planner"
            for action in actions:
                if action == "extract_profile":
                    await call(action, text=str(submission.get("profile", "")))
                else:
                    query = (
                        " ".join(str(submission.get(f, "")) for f in ("goals", "rationale"))[:12000]
                        or "occupational participation"
                    )
                    retrieval = await call(action, query=query, k=3)
            await call("get_evaluation_rubric")
            report = await call("assess_rubric")
            recommendation = await call("recommend_next_case")
            report["recommendation"] = recommendation
            report["agent"] = {
                "mode": mode,
                "trace_id": trace_id,
                "action_budget": budget,
                "deadline_seconds": deadline,
                "elapsed_ms_before_save": round((time.monotonic() - started) * 1000, 2),
                "limitations": "Rule mode is a bounded selective workflow. Model-directed planning is separately configured and not claimed in rule mode.",
            }
            report["mcp"] = {
                "sdk": "mcp==2.2.0",
                "transport": settings.mcp_transport,
                "initialized": True,
                "discovered_tools": client.tools,
                "protocol_version": client.initialization.get(
                    "protocol_version", client.initialization.get("protocolVersion")
                ),
                "server": client.initialization.get(
                    "server_info", client.initialization.get("serverInfo")
                ),
            }
            report["evidence_retrieval"] = {
                "mode": retrieval.get("mode"),
                "status": retrieval.get("status"),
                "passage_ids": [p["id"] for p in retrieval.get("results", [])],
            }
            report["trace"] = trace + [
                {"step": calls + 1, "tool": "save_feedback", "status": "requested"}
            ]
            frozen = json.dumps(
                submission, sort_keys=True, ensure_ascii=False, separators=(",", ":")
            )
            key = hashlib.sha256((scope["attempt_id"] + ":" + frozen).encode()).hexdigest()
            stored = await call("save_feedback", report=report, idempotency_key=key)
            output = stored.get("report", report)
            output["feedback_id"] = stored.get("feedback_id")
            return output

    # Timeout cancels SDK contexts and terminates a spawned stdio server.
    async with asyncio.timeout(deadline):
        return await work()
