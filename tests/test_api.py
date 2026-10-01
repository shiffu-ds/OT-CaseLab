import copy
import io
import json
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from services.api import database, jobs, main, mcp_bridge
from services.api.config import get_settings
from services.api.models import (
    Attempt,
    Audit,
    Cohort,
    Feedback,
    FeedbackReview,
    Message,
    Session,
    User,
    now,
)
from services.api.security import COOKIE, digest
from services.api.seed import seed_content, seed_user

PLAN = {
    "profile": "Ayesha describes a dressing routine and family support. Her preference is to choose her shirt.",
    "observations": "The schematic contains a chair and rug. Ask about the doorway and seating preference before an interpretation.",
    "goals": "Within two weeks, Ayesha will choose her shirt before breakfast with agreed family help, reflecting her priority.",
    "rationale": "Ask what is important, then trial an agreed dressing sequence with educator support and review the functional goal.",
    "evidence_ids": [],
}


@pytest.fixture
def environment(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'test.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("MCP_SERVICE_SECRET", "test-service-secret-" + "x" * 40)
    monkeypatch.setenv("APP_ORIGIN", "http://localhost:3000")
    monkeypatch.setenv("NLP_MODE", "baseline")
    monkeypatch.setenv("CV_MODE", "baseline")
    monkeypatch.setenv("PROVIDER_MODE", "scripted")
    monkeypatch.setenv("MCP_TRANSPORT", "stdio")
    monkeypatch.setenv("PRIVATE_ASSET_PATH", str(tmp_path / "uploads"))
    get_settings.cache_clear()
    engine = database.make_engine(url)
    database.Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    for module in (database, main, jobs, mcp_bridge):
        monkeypatch.setattr(module, "SessionLocal", factory)

    def dependency():
        with factory() as db:
            yield db

    main.app.dependency_overrides[database.get_db] = dependency
    monkeypatch.setattr(jobs, "dispatch_job", jobs.execute_job)
    with factory() as db:
        seed_content(db)
        user, _ = seed_user(
            db, "educator@example.test", "Local educator", "educator", "EducatorPass123!"
        )
        db.add(Cohort(id="other", name="Other cohort"))
        db.commit()
        seed_user(
            db, "outsider@example.test", "Other educator", "educator", "EducatorPass123!", "other"
        )
    yield factory
    main.app.dependency_overrides.clear()
    engine.dispose()
    get_settings.cache_clear()


def client():
    return TestClient(main.app, headers={"Origin": "http://localhost:3000"})


def student(c, name="Learner", language="en"):
    r = c.post(
        "/api/v1/auth/register",
        json={
            "email": name.lower().replace(" ", "") + "@example.test",
            "password": "LearnerPass123!",
            "name": name,
            "language": language,
        },
    )
    assert r.status_code == 201, r.text
    c.headers["X-CSRF-Token"] = r.json()["csrf_token"]
    return r.json()["user"]


def login(c, email):
    r = c.post("/api/v1/auth/login", json={"email": email, "password": "EducatorPass123!"})
    assert r.status_code == 200, r.text
    c.headers["X-CSRF-Token"] = r.json()["csrf_token"]


def start(c, factory, language="en"):
    r = c.post("/api/v1/attempts", json={"case_id": "stroke-home", "language": language})
    assert r.status_code == 201, r.text
    aid = r.json()["id"]
    with factory() as db:
        for m in db.scalars(select(Message).where(Message.attempt_id == aid)):
            m.created_at = now() - timedelta(seconds=3)
        db.commit()
    return aid


def ask(c, aid, question="What activities are important and who helps you at home?"):
    r = c.post(f"/api/v1/attempts/{aid}/messages", json={"text": question})
    assert r.status_code == 200, r.text
    return r.json()


def submit(c, aid, plan=PLAN):
    r = c.post(
        f"/api/v1/attempts/{aid}/submit", json=plan, headers={"Idempotency-Key": "first-submission"}
    )
    assert r.status_code == 200, r.text
    return r.json()


@pytest.mark.parametrize(
    "language,question",
    [
        ("en", "Which activity and priority matter to you?"),
        ("ur", "آپ کی ترجیح اور روزمرہ کا کام کیا ہے؟"),
        ("roman", "Aap ki tarjeeh aur roz ka kaam kya hai?"),
    ],
)
def test_real_scripted_journey_and_mcp(environment, language, question):
    c = client()
    student(c, "Learner " + language, language)
    cases = c.get("/api/v1/cases").json()["items"]
    assert len(cases) == 5
    assert all(
        "facts" not in case and "rubric" not in case and "annotations" not in case["asset"]
        for case in cases
    )
    aid = start(c, environment, language)
    reply = ask(c, aid, question)
    assert reply["mode"] == "scripted"
    assert reply["patient_message"]["provenance"]["disclosed_fact_ids"]
    attempt = submit(c, aid)
    assert attempt["state"] == "completed"
    feedback = attempt["feedback"]
    assert feedback["mcp"]["initialized"] is True
    assert "save_feedback" in feedback["mcp"]["discovered_tools"]
    assert all(step["status"] == "completed" for step in feedback["trace"])
    assert feedback["review_status"] == "provisional"
    assert all(item["reference_passage"] is None for item in feedback["items"])
    assert attempt["recommendation"]["mode"] == "transparent_rule"
    report = c.get(f"/api/v1/attempts/{aid}/report")
    assert report.status_code == 200 and "application" not in report.headers["content-type"]
    assert "Provisional" in report.text
    progress = c.get("/api/v1/progress").json()
    assert progress["completed"] == 1
    assert all(score["max_score"] == 3 for score in progress["domain_scores"].values())


def test_cookie_csrf_origin_and_privilege_boundaries(environment):
    c = client()
    user = student(c)
    token = c.cookies[COOKIE]
    with environment() as db:
        session = db.get(Session, digest(token))
        assert session and session.token_hash != token
        assert db.get(User, user["id"]).password_hash.startswith("$argon2id$")
    assert (
        c.post(
            "/api/v1/attempts", json={"case_id": "stroke-home"}, headers={"X-CSRF-Token": "wrong"}
        ).status_code
        == 403
    )
    assert (
        c.post(
            "/api/v1/attempts",
            json={"case_id": "stroke-home"},
            headers={"Origin": "https://attacker.example"},
        ).status_code
        == 403
    )
    assert c.get("/api/v1/educator/cases").status_code == 403
    r = c.post(
        "/api/v1/auth/register",
        json={
            "email": "elevate@example.test",
            "password": "LearnerPass123!",
            "name": "Escalate",
            "role": "admin",
        },
    )
    assert r.status_code == 422
    r = c.post("/api/v1/auth/login", json={"email": user["email"], "password": "LearnerPass123!"})
    assert "HttpOnly" in r.headers["set-cookie"] and "SameSite=lax" in r.headers["set-cookie"]


def test_cross_learner_and_cross_cohort_access(environment):
    a, b, teacher = client(), client(), client()
    student(a, "First learner")
    student(b, "Second learner")
    aid = start(a, environment)
    for path in [
        f"/api/v1/attempts/{aid}",
        f"/api/v1/attempts/{aid}/report",
        f"/api/v1/attempts/{aid}/feedback",
    ]:
        assert b.get(path).status_code == 404
    assert b.patch(f"/api/v1/attempts/{aid}/draft", json=PLAN).status_code == 404
    login(teacher, "outsider@example.test")
    assert teacher.get(f"/api/v1/attempts/{aid}").status_code == 404
    assert teacher.get("/api/v1/educator/attempts").json()["items"] == []
    assert teacher.get("/api/v1/assets/room-home").status_code == 404


def test_idempotent_freeze_and_educator_amendment(environment):
    c, teacher = client(), client()
    student(c)
    aid = start(c, environment)
    ask(c, aid)
    original = submit(c, aid)
    repeated = submit(c, aid)
    assert repeated["feedback"]["id"] == original["feedback"]["id"]
    assert c.patch(f"/api/v1/attempts/{aid}/draft", json=PLAN).status_code == 409
    changed = {**PLAN, "goals": "An entirely different proposed fictional goal."}
    assert (
        c.post(
            f"/api/v1/attempts/{aid}/submit",
            json=changed,
            headers={"Idempotency-Key": "first-submission"},
        ).status_code
        == 409
    )
    login(teacher, "educator@example.test")
    r = teacher.post(
        f"/api/v1/educator/attempts/{aid}/review",
        json={
            "comment": "Please justify the goal using the patient's stated morning priority.",
            "scores": {"goals": 2},
        },
    )
    assert r.status_code == 200
    assert r.json()["review_status"] == "educator_amended"
    learner_report = c.get(f"/api/v1/attempts/{aid}/feedback").json()
    assert learner_report["items"] == original["feedback"]["items"]
    assert learner_report["reviews"][0]["scores"] == {"goals": 2}
    with environment() as db:
        assert len(db.scalars(select(Feedback).where(Feedback.attempt_id == aid)).all()) == 1
        assert db.scalar(select(FeedbackReview))


def test_published_version_pins_old_attempt(environment):
    c, teacher = client(), client()
    student(c)
    aid = start(c, environment)
    login(teacher, "educator@example.test")
    original = teacher.get("/api/v1/educator/cases").json()["items"][0]
    original = next(
        p for p in teacher.get("/api/v1/educator/cases").json()["items"] if p["id"] == "stroke-home"
    )
    version = copy.deepcopy(original)
    version["title"] = "Revised fictional dressing scenario"
    r = teacher.post("/api/v1/educator/cases/stroke-home/versions", json={"case": version})
    assert r.status_code == 201 and r.json()["version"] == 2
    r = teacher.post(
        "/api/v1/educator/cases/stroke-home/publish",
        json={
            "review_note": "Review performed within this test fixture, not a real content approval."
        },
    )
    assert r.status_code == 200
    assert c.get("/api/v1/cases/stroke-home").json()["version"] == 2
    old = c.get(f"/api/v1/attempts/{aid}").json()
    assert old["case_version"] == 1 and old["case"]["title"] == original["title"]
    assert (
        teacher.post(
            "/api/v1/educator/cases/stroke-home/publish",
            json={"review_note": "Repeat publish must be rejected; edits need a new version."},
        ).status_code
        == 409
    )


def test_provider_failure_preserves_open_attempt(environment, monkeypatch):
    c = client()
    student(c)
    aid = start(c, environment)
    import ai

    def fail(*args):
        raise RuntimeError("Sensitive provider details must not appear")

    monkeypatch.setattr(ai, "patient_reply", fail)
    r = c.post(f"/api/v1/attempts/{aid}/messages", json={"text": "What do you want to do?"})
    assert r.status_code == 503 and "Sensitive" not in r.text
    attempt = c.get(f"/api/v1/attempts/{aid}").json()
    assert attempt["state"] == "active" and len(attempt["messages"]) == 1


def test_analysis_scope_gate_and_durable_job(environment):
    c = client()
    student(c)
    aid = start(c, environment)
    assert (
        c.post(f"/api/v1/attempts/{aid}/analysis", json={"asset_id": "room-home"}).status_code
        == 422
    )
    c.patch(f"/api/v1/attempts/{aid}/draft", json=PLAN)
    assert (
        c.post(
            f"/api/v1/attempts/{aid}/analysis", json={"asset_id": "../../etc/passwd"}
        ).status_code
        == 404
    )
    r = c.post(f"/api/v1/attempts/{aid}/analysis", json={"asset_id": "room-home"})
    assert r.status_code == 202
    job = c.get("/api/v1/jobs/" + r.json()["id"]).json()
    assert job["status"] == "completed"
    assert job["output"]["mode"] == "reference_only"
    assert job["output"]["provenance"]["inference_executed"] is False
    repeated = c.post(f"/api/v1/attempts/{aid}/analysis", json={"asset_id": "room-home"})
    assert repeated.json()["id"] == job["id"]


def test_delete_personal_records_and_expiry(environment):
    c = client()
    user = student(c)
    aid = start(c, environment)
    c.post("/api/v1/privacy/consent", json={"granted": True})
    assert c.get("/api/v1/auth/me").json()["user"]["research_consent"] is True
    assert c.delete("/api/v1/privacy/me").status_code == 200
    assert c.get("/api/v1/auth/me").status_code == 401
    with environment() as db:
        assert db.get(User, user["id"]) is None and db.get(Attempt, aid) is None
        assert db.scalar(select(Audit).where(Audit.actor_id == user["id"])) is None
    student(c, "Expiring learner")
    with environment() as db:
        session = db.get(Session, digest(c.cookies[COOKIE]))
        session.expires_at = now() - timedelta(seconds=1)
        db.commit()
    assert c.get("/api/v1/auth/me").status_code == 401


def test_educational_upload_sanitizes_metadata_and_scope(environment):
    from PIL import Image, PngImagePlugin

    c, other = client(), client()
    student(c, "Image learner")
    student(other, "Other image learner")
    aid = start(c, environment)
    c.patch(f"/api/v1/attempts/{aid}/draft", json=PLAN)
    image = Image.new("RGB", (32, 32), "#a5bfbb")
    info = PngImagePlugin.PngInfo()
    info.add_text("private-test-note", "this metadata must be stripped")
    data = io.BytesIO()
    image.save(data, format="PNG", pnginfo=info)
    r = c.post(
        f"/api/v1/attempts/{aid}/uploads",
        files={"file": ("../../unsafe.png", data.getvalue(), "image/png")},
    )
    assert r.status_code == 202, r.text
    job = c.get("/api/v1/jobs/" + r.json()["id"]).json()
    assert job["status"] == "completed"
    assert job["output"]["reference_annotations"] == []
    with environment() as db:
        from services.api.models import Job

        stored = db.get(Job, job["id"])
        sha = stored.input["checksum"]
        assert stored.input["metadata_removed"]
    clean = c.get(f"/api/v1/attempts/{aid}/uploads/{sha}")
    assert clean.status_code == 200
    with Image.open(io.BytesIO(clean.content)) as restored:
        assert not restored.info
    assert other.get(f"/api/v1/attempts/{aid}/uploads/{sha}").status_code == 404
    r = c.post(
        f"/api/v1/attempts/{aid}/uploads",
        files={"file": ("bad.svg", b'<svg onload="bad()"/>', "image/svg+xml")},
    )
    assert r.status_code == 422
    repeated = c.post(
        f"/api/v1/attempts/{aid}/uploads",
        files={"file": ("same.png", data.getvalue(), "image/png")},
    )
    assert repeated.json()["id"] == job["id"]
    assert c.delete("/api/v1/privacy/me").status_code == 200
    from pathlib import Path

    assert not (Path(get_settings().private_asset_path) / aid).exists()


def test_admin_authorization_and_cohort_isolation(environment):
    with environment() as db:
        seed_user(db, "admin@example.test", "Test administrator", "admin", "EducatorPass123!")
    c, admin, outsider = client(), client(), client()
    target = student(c, "Pending educator")
    login(admin, "admin@example.test")
    login(outsider, "outsider@example.test")
    assert c.get("/api/v1/admin/users").status_code == 403
    assert outsider.get("/api/v1/admin/users").status_code == 403
    users = admin.get("/api/v1/admin/users").json()["items"]
    assert all(u["cohort_id"] == "demo" for u in users)
    assert "password_hash" not in json.dumps(users)
    r = admin.post(f"/api/v1/admin/users/{target['id']}/role", json={"role": "educator"})
    assert r.status_code == 200 and r.json()["role"] == "educator"
    assert c.get("/api/v1/auth/me").status_code == 401
    assert (
        admin.post(f"/api/v1/admin/users/{target['id']}/role", json={"role": "admin"}).status_code
        == 422
    )
    with environment() as db:
        other = db.scalar(select(User).where(User.email == "outsider@example.test"))
        other_id = other.id
    assert (
        admin.post(f"/api/v1/admin/users/{other_id}/role", json={"role": "student"}).status_code
        == 404
    )
    ops = admin.get("/api/v1/admin/operations").json()
    assert ops["health"] == "ok" and ops["modes"]["dialogue"] == "scripted"
    assert "learner text" not in json.dumps(ops)


def test_consent_filtered_structured_export(environment, monkeypatch):
    c, teacher = client(), client()
    student(c, "Consenting learner")
    aid = start(c, environment)
    ask(c, aid)
    submit(c, aid)
    login(teacher, "educator@example.test")
    assert teacher.get("/api/v1/educator/research-export").status_code == 403
    monkeypatch.setenv("RESEARCH_EXPORTS_ENABLED", "true")
    monkeypatch.setenv("RESEARCH_EXPORT_SECRET", "test-export-key-" + "y" * 40)
    get_settings.cache_clear()
    assert teacher.get("/api/v1/educator/research-export").json()["items"] == []
    c.post("/api/v1/privacy/consent", json={"granted": True})
    exported = teacher.get("/api/v1/educator/research-export").json()
    assert len(exported["items"]) == 1
    assert "example.test" not in json.dumps(exported) and PLAN["profile"] not in json.dumps(
        exported
    )
    c.post("/api/v1/privacy/consent", json={"granted": False})
    assert teacher.get("/api/v1/educator/research-export").json()["items"] == []


def test_streamed_body_limit_and_malformed_origin(environment, monkeypatch):
    c = client()
    monkeypatch.setenv("REQUEST_LIMIT_BYTES", "256")
    get_settings.cache_clear()
    r = c.post(
        "/api/v1/auth/register",
        content=(b"x" * 128 for _ in range(4)),
        headers={"Content-Type": "application/json"},
    )
    assert r.status_code == 413
    r = c.post(
        "/api/v1/auth/login",
        json={"email": "wrong@example.test", "password": "LearnerPass123!"},
        headers={"Origin": "http://localhost:bad-port"},
    )
    assert r.status_code == 403


def test_interrupted_evaluation_retry_is_recoverable(environment):
    c = client()
    student(c, "Interrupted learner")
    aid = start(c, environment)
    with environment() as db:
        attempt = db.get(Attempt, aid)
        attempt.state = "evaluating"
        attempt.submitted_at = now()
        db.commit()
    with TestClient(main.app, headers={"Origin": "http://localhost:3000"}):
        pass
    with environment() as db:
        attempt = db.get(Attempt, aid)
        assert attempt.state == "failed" and "retry" in attempt.error.lower()
