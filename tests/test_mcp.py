import asyncio
import hashlib
import json
import os
import socket
import subprocess
import sys
import time

import pytest

from services.mcp.auth import ScopeError, issue_token, verify_token
from services.mcp.client import ToolError, connect


def scope(**updates):
    return {
        "user_id": "fixture-learner",
        "attempt_id": "fixture-attempt",
        "cohort_id": "fixture-cohort",
        "exp": int(time.time()) + 60,
        "permissions": ["read", "analyze", "write"],
        **updates,
    }


def test_signed_identity_cannot_be_changed(monkeypatch):
    monkeypatch.setenv("MCP_SERVICE_SECRET", "a" * 48)
    token = issue_token(scope())
    assert verify_token(token, "read")["user_id"] == "fixture-learner"
    payload, signature = token.split(".")
    with pytest.raises(ScopeError):
        verify_token(payload[:-2] + "XX." + signature, "read")


def test_expiry_and_write_scope_are_enforced(monkeypatch):
    monkeypatch.setenv("MCP_SERVICE_SECRET", "b" * 48)
    with pytest.raises(ScopeError, match="Expired"):
        verify_token(issue_token(scope(exp=int(time.time()) - 1)), "read")
    with pytest.raises(ScopeError, match="permission"):
        verify_token(issue_token(scope(permissions=["read"])), "write")


@pytest.mark.asyncio
async def test_real_stdio_initialization_discovery_and_forgery_rejection(monkeypatch):
    monkeypatch.setenv("MCP_SERVICE_SECRET", "c" * 48)
    monkeypatch.setenv("MCP_TRANSPORT", "stdio")
    from services.api.config import get_settings

    get_settings.cache_clear()
    token = issue_token(scope())
    forged = token[:-1] + ("0" if token[-1] != "0" else "1")
    async with connect(forged) as client:
        assert client.initialization
        assert {
            "get_case_context",
            "assess_rubric",
            "save_feedback",
            "search_approved_evidence",
        } <= set(client.tools)
        with pytest.raises(ToolError, match="rejected"):
            await client.call("get_case_context")
    get_settings.cache_clear()


@pytest.fixture
def mcp_attempt(tmp_path, monkeypatch):
    from sqlalchemy import select
    from sqlalchemy.orm import sessionmaker

    from services.api.config import get_settings
    from services.api.database import Base, make_engine
    from services.api.models import Attempt, CaseVersion, Message, RubricVersion, Submission
    from services.api.seed import seed_content, seed_user

    database_url = f"sqlite:///{tmp_path / 'mcp-test.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("MCP_SERVICE_SECRET", "protocol-test-internal-secret-" * 2)
    monkeypatch.setenv("MCP_TRANSPORT", "stdio")
    monkeypatch.setenv("PROVIDER_MODE", "scripted")
    monkeypatch.setenv("NLP_MODE", "baseline")
    monkeypatch.setenv("ALLOW_DEMO", "true")
    get_settings.cache_clear()
    engine = make_engine(database_url)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    submission = {
        "profile": "A priority is dressing. Ask about family support.",
        "observations": "I observe a chair and door. Measure the space.",
        "goals": "Goal: dress before breakfast. Ask about agreed minutes.",
        "rationale": "Because the priority matters, review uncertainty.",
        "evidence_ids": [],
    }
    with factory() as db:
        seed_content(db)
        owner, _ = seed_user(
            db, "owner@example.test", "Fixture owner", password="Fixture-password-a!3"
        )
        other, _ = seed_user(
            db, "other@example.test", "Fixture other", password="Fixture-password-b!3"
        )
        version = db.scalar(select(CaseVersion).where(CaseVersion.case_id == "stroke-home"))
        rubric = db.scalar(select(RubricVersion).where(RubricVersion.case_version_id == version.id))
        attempt = Attempt(
            user_id=owner.id,
            case_version_id=version.id,
            rubric_version_id=rubric.id,
            language="en",
            state="evaluating",
            draft=submission,
        )
        db.add(attempt)
        db.flush()
        db.add(
            Submission(
                attempt_id=attempt.id,
                content=submission,
                checksum=hashlib.sha256(json.dumps(submission).encode()).hexdigest(),
                idempotency_key="fixture-submission",
            )
        )
        db.add(
            Message(
                attempt_id=attempt.id,
                role="student",
                text="What is important in your routine? Who can support you?",
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
        claims = scope(user_id=owner.id, attempt_id=attempt.id, cohort_id="demo")
        other_id = other.id
    yield {"scope": claims, "submission": submission, "factory": factory, "other_id": other_id}
    engine.dispose()
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_actual_feedback_workflow_persists_protocol_trace(mcp_attempt):
    from sqlalchemy import select

    from ai.agent import run_feedback
    from services.api.models import Attempt, Feedback

    report = await run_feedback(mcp_attempt["scope"], mcp_attempt["submission"])
    assert report["mcp"]["initialized"] is True
    assert report["mcp"]["transport"] == "stdio"
    assert report["feedback_id"]
    assert len(report["trace"]) <= report["agent"]["action_budget"]
    assert {e["tool"] for e in report["trace"]} >= {
        "get_case_context",
        "extract_profile",
        "search_approved_evidence",
        "get_evaluation_rubric",
        "assess_rubric",
        "recommend_next_case",
        "save_feedback",
    }
    assert all(e["status"] == "completed" for e in report["trace"])
    assert report["evidence_retrieval"]["status"] == "no_approved_relevant_evidence"
    with mcp_attempt["factory"]() as db:
        stored = db.scalar(
            select(Feedback).where(Feedback.attempt_id == mcp_attempt["scope"]["attempt_id"])
        )
        assert stored.id == report["feedback_id"]
        assert db.get(Attempt, stored.attempt_id).state == "completed"


@pytest.mark.asyncio
async def test_signed_cross_owner_and_cohort_are_rejected(mcp_attempt):
    for updates in ({"user_id": mcp_attempt["other_id"]}, {"cohort_id": "other-cohort"}):
        async with connect(issue_token({**mcp_attempt["scope"], **updates})) as client:
            with pytest.raises(ToolError, match="rejected"):
                await client.call("get_case_context")


@pytest.mark.asyncio
async def test_mcp_write_retry_and_invalid_support(mcp_attempt):
    from sqlalchemy import func, select

    from services.api.models import Feedback

    async with connect(issue_token(mcp_attempt["scope"])) as client:
        report = await client.call("assess_rubric")
        original = json.loads(json.dumps(report))
        item = next(i for i in report["items"] if i["student_evidence"])
        item["student_evidence"][0]["text"] = "fabricated learner support"
        with pytest.raises(ToolError, match="rejected"):
            await client.call("save_feedback", report=report, idempotency_key="retry-key")
        first = await client.call("save_feedback", report=original, idempotency_key="retry-key")
        second = await client.call("save_feedback", report=original, idempotency_key="retry-key")
        assert first["feedback_id"] == second["feedback_id"]
        assert second["idempotent_retry"] is True
        with mcp_attempt["factory"]() as db:
            assert db.scalar(select(func.count()).select_from(Feedback)) == 1


@pytest.mark.asyncio
async def test_real_streamable_http_requires_bearer_and_scoped_identity(mcp_attempt, monkeypatch):
    import httpx

    from services.api.config import get_settings

    with socket.socket() as available:
        available.bind(("127.0.0.1", 0))
        port = available.getsockname()[1]
    token = "http-transport-fixture-token-" * 2
    monkeypatch.setenv("MCP_TRANSPORT", "http")
    monkeypatch.setenv("MCP_HTTP_BEARER_TOKEN", token)
    monkeypatch.setenv("MCP_PORT", str(port))
    monkeypatch.setenv("MCP_URL", f"http://127.0.0.1:{port}/mcp")
    get_settings.cache_clear()
    process = subprocess.Popen(
        [sys.executable, "-m", "services.mcp.server"],
        env=os.environ.copy(),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        async with httpx.AsyncClient() as probe:
            for _ in range(150):
                try:
                    response = await probe.post(
                        get_settings().mcp_url,
                        json={"jsonrpc": "2.0", "method": "initialize", "id": 1, "params": {}},
                    )
                    assert response.status_code == 401
                    break
                except httpx.ConnectError:
                    if process.poll() is not None:
                        raise AssertionError("MCP HTTP process failed before readiness")
                    await asyncio.sleep(0.1)
            else:
                raise AssertionError("MCP HTTP server did not become ready")
            internal_host = await probe.post(
                get_settings().mcp_url,
                headers={
                    "Authorization": "Bearer " + token,
                    "Host": "mcp:9000",
                    "Accept": "application/json, text/event-stream",
                },
                json={
                    "jsonrpc": "2.0",
                    "method": "initialize",
                    "id": 1,
                    "params": {
                        "protocolVersion": "2025-11-25",
                        "capabilities": {},
                        "clientInfo": {"name": "internal-host-fixture", "version": "0.1"},
                    },
                },
            )
            assert internal_host.status_code == 200
        async with connect(issue_token(mcp_attempt["scope"])) as client:
            context = await client.call("get_case_context")
            assert context["case_id"] == "stroke-home"
            assert client.initialization
            assert "save_feedback" in client.tools
        forged = issue_token({**mcp_attempt["scope"], "user_id": mcp_attempt["other_id"]})
        async with connect(forged) as client:
            with pytest.raises(ToolError):
                await client.call("get_case_context")
    finally:
        process.terminate()
        process.wait(timeout=10)
        get_settings.cache_clear()


def test_job_atomic_duplicate_claim_and_retry(mcp_attempt, monkeypatch):
    import threading
    from concurrent.futures import ThreadPoolExecutor
    from datetime import timedelta

    from ai import cv
    from services.api import jobs
    from services.api.models import Job, now

    monkeypatch.setattr(jobs, "SessionLocal", mcp_attempt["factory"])
    with mcp_attempt["factory"]() as db:
        job = Job(
            attempt_id=mcp_attempt["scope"]["attempt_id"],
            kind="image",
            input_checksum="claim-fixture",
            input={"asset_id": "room-home"},
        )
        db.add(job)
        db.commit()
        job_id = job.id
    started, release = threading.Event(), threading.Event()
    calls = []

    def inference(path, mode):
        calls.append(str(path))
        started.set()
        assert release.wait(timeout=5)
        return {"mode": "test_inference", "predictions": []}

    monkeypatch.setattr(cv, "analyze_asset", inference)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(jobs.execute_job, job_id)
        assert started.wait(timeout=5)
        with pytest.raises(jobs.JobLeaseBusy):
            jobs.execute_job(job_id)
        release.set()
        assert first.result(timeout=5)["status"] == "completed"
    assert len(calls) == 1
    assert jobs.execute_job(job_id)["status"] == "completed"
    with mcp_attempt["factory"]() as db:
        job = db.get(Job, job_id)
        assert job.retry_count == 1
        job.state, job.updated_at = "running", now() - timedelta(seconds=jobs.LEASE_SECONDS + 1)
        db.commit()
    assert jobs.execute_job(job_id)["status"] == "completed"
    with mcp_attempt["factory"]() as db:
        assert db.get(Job, job_id).retry_count == 2


def test_job_superseded_claim_cannot_overwrite_and_restart_recovers(mcp_attempt, monkeypatch):
    import threading
    from concurrent.futures import ThreadPoolExecutor

    from ai import cv
    from services.api import jobs
    from services.api.models import Job, now

    monkeypatch.setattr(jobs, "SessionLocal", mcp_attempt["factory"])
    with mcp_attempt["factory"]() as db:
        job = Job(
            attempt_id=mcp_attempt["scope"]["attempt_id"],
            kind="image",
            input_checksum="supersede-fixture",
            input={"asset_id": "room-home"},
        )
        db.add(job)
        db.commit()
        job_id = job.id
    started, release = threading.Event(), threading.Event()

    def inference(path, mode):
        started.set()
        assert release.wait(timeout=5)
        return {"mode": "obsolete-result", "predictions": []}

    monkeypatch.setattr(cv, "analyze_asset", inference)
    with ThreadPoolExecutor(max_workers=1) as pool:
        first = pool.submit(jobs.execute_job, job_id)
        assert started.wait(timeout=5)
        with mcp_attempt["factory"]() as db:
            job = db.get(Job, job_id)
            job.updated_at, job.retry_count, job.output = (
                now(),
                job.retry_count + 1,
                {"newer_claim": True},
            )
            db.commit()
        release.set()
        assert first.result(timeout=5)["status"] == "superseded"
    scheduled = []
    monkeypatch.setattr(jobs, "dispatch_job", scheduled.append)
    monkeypatch.setenv("JOB_MODE", "local")
    from services.api.config import get_settings

    get_settings.cache_clear()
    assert jobs.recover_local_jobs() == [job_id]
    assert scheduled == [job_id]
    with mcp_attempt["factory"]() as db:
        assert db.get(Job, job_id).state == "queued"


def test_worker_busy_lease_schedules_bounded_retry(monkeypatch):
    from celery.exceptions import Retry

    from services.api import jobs
    from services.worker.tasks import process_job

    def busy(job_id):
        raise jobs.JobLeaseBusy(17)

    scheduled = []
    monkeypatch.setattr(jobs, "execute_job", busy)

    def retry(**kwargs):
        scheduled.append(kwargs)
        raise Retry("retry scheduled")

    monkeypatch.setattr(process_job, "retry", retry)
    with pytest.raises(Retry):
        process_job.run("worker-fixture")
    assert scheduled[0]["countdown"] == 17
    assert scheduled[0]["max_retries"] == 2
