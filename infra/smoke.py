"""Exercise the live private API + HTTP MCP + worker in a disposable stack.

Run through `docker compose exec -T api python < infra/smoke.py`.
The explicit session header models the trusted proxy's TLS termination; it does
not verify public HTTPS or browser secure-cookie behavior.
"""

import io
import json
import secrets
import time
import uuid

import httpx
from PIL import Image
from sqlalchemy import select, text

from services.api.config import get_settings
from services.api.database import SessionLocal
from services.api.models import Job, User
from services.api.seed import seed_user

settings = get_settings()
password = secrets.token_urlsafe(24)
run_id = uuid.uuid4().hex[:12]
with SessionLocal() as db:
    student, _ = seed_user(
        db, f"student-{run_id}@example.invalid", "Smoke student", "student", password
    )
    educator, _ = seed_user(
        db, f"educator-{run_id}@example.invalid", "Smoke educator", "educator", password
    )
    other, _ = seed_user(
        db, f"other-{run_id}@example.invalid", "Other student", "student", password
    )
    emails = {"student": student.email, "educator": educator.email, "other": other.email}
    role = db.execute(
        text(
            "SELECT rolname, rolsuper, rolcreatedb, rolcreaterole FROM pg_roles WHERE rolname=current_user"
        )
    ).one()
    assert role[0] == "otcase_app" and not any(role[1:]), (
        "Application database role must have limited privileges"
    )

clients = {}
for name, email in emails.items():
    client = httpx.Client(
        base_url="http://api:8000", headers={"Origin": settings.app_origin}, timeout=90
    )
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, (name, response.status_code)
    assert (
        "Secure" in response.headers["set-cookie"] and "HttpOnly" in response.headers["set-cookie"]
    )
    client.headers["Cookie"] = "otcaselab_session=" + response.cookies["otcaselab_session"]
    client.headers["X-CSRF-Token"] = response.json()["csrf_token"]
    clients[name] = client
s, e, o = (clients[k] for k in ("student", "educator", "other"))

assert s.get("/api/v1/health").status_code == 200
case_list = s.get("/api/v1/cases").json()["items"]
# Drafts must not appear with production demo allowance disabled.
assert all(c["review_status"] == "reviewed" for c in case_list), (
    "Production should hide unreviewed demo cases"
)
case_id = "infra-case-" + run_id
draft = next(c for c in e.get("/api/v1/educator/cases").json()["items"] if c["id"] == "stroke-home")
draft.update(
    {
        "id": case_id,
        "review_status": "pending_review",
        "published": False,
        "eligible_demo": False,
        "review_note": None,
    }
)
for passage in draft["evidence"]:
    passage["approved"] = False
new_case = e.post("/api/v1/educator/cases", json={"case": draft})
assert new_case.status_code == 201, new_case.text
assert s.get(f"/api/v1/cases/{case_id}").status_code == 404
published = e.post(
    f"/api/v1/educator/cases/{case_id}/publish",
    json={
        "review_note": "Disposable infrastructure smoke approval only; not an educator validation for release."
    },
)
assert published.status_code == 200, published.text
case = s.get(f"/api/v1/cases/{case_id}").json()
assert "facts" not in case and "rubric" not in case and "evidence" not in case
created = s.post("/api/v1/attempts", json={"case_id": case_id, "language": "en"})
assert created.status_code == 201, created.text
attempt_id = created.json()["id"]
assert o.get(f"/api/v1/attempts/{attempt_id}").status_code == 404
time.sleep(1.1)
message = s.post(
    f"/api/v1/attempts/{attempt_id}/messages",
    json={"text": "What activity is most important to you and who can help?"},
)
assert message.status_code == 200, message.text
plan = {
    "profile": "Ayesha's priority is choosing clothes before breakfast; ask about routine and support preferences.",
    "observations": "The image shows a chair, shelf and table. Measure space and ask about the room before interpreting access.",
    "goals": "Agree a goal to choose clothes and dress before breakfast with preferred support; review time and feasibility with the educator.",
    "rationale": "Because this addresses her stated priority, ask about missing measurements and clinical restrictions before choosing the approach.",
    "evidence_ids": [],
}
key = "infra-" + run_id
submitted = s.post(
    f"/api/v1/attempts/{attempt_id}/submit", json=plan, headers={"Idempotency-Key": key}
)
assert submitted.status_code in (200, 202), submitted.text
for _ in range(60):
    response = s.get(f"/api/v1/attempts/{attempt_id}/feedback")
    if response.status_code == 200:
        report = response.json()
        break
    time.sleep(1)
else:
    raise AssertionError("Feedback did not complete")
encoded = json.dumps(report)
assert '"initialized": true' in encoded, "MCP must genuinely initialize"
assert "search_approved_evidence" in encoded and "save_feedback" in encoded
assert "bounded_rule_workflow" in encoded
retried = s.post(
    f"/api/v1/attempts/{attempt_id}/submit", json=plan, headers={"Idempotency-Key": key}
)
assert retried.status_code == 200, retried.text
assert o.get(f"/api/v1/attempts/{attempt_id}/report").status_code == 404
assert s.get(f"/api/v1/attempts/{attempt_id}/report").status_code == 200
review = e.post(
    f"/api/v1/educator/attempts/{attempt_id}/review",
    json={
        "comment": "Disposable smoke amendment retained with the original provisional output.",
        "scores": {"goals": 2},
    },
)
assert review.status_code == 200, review.text
analysis = s.post(f"/api/v1/attempts/{attempt_id}/analysis", json={"asset_id": "room-home"})
assert analysis.status_code == 202, analysis.text
job_id = analysis.json()["id"]
for _ in range(30):
    job = s.get(f"/api/v1/jobs/{job_id}").json()
    if job["state"] in ("completed", "failed"):
        break
    time.sleep(1)
assert job["state"] == "completed", job
assert o.get(f"/api/v1/jobs/{job_id}").status_code == 404
image = Image.new("RGB", (80, 60), (124, 158, 147))
image_data = io.BytesIO()
image.save(image_data, format="JPEG", comment=b"metadata-to-remove")
upload = s.post(
    f"/api/v1/attempts/{attempt_id}/uploads",
    files={"file": ("educational.jpg", image_data.getvalue(), "image/jpeg")},
)
assert upload.status_code == 202, upload.text
upload_id = upload.json()["id"]
for _ in range(30):
    upload_job = s.get(f"/api/v1/jobs/{upload_id}").json()
    if upload_job["state"] in ("completed", "failed"):
        break
    time.sleep(1)
assert upload_job["state"] == "completed", upload_job

with SessionLocal() as db:
    checksum = db.get(Job, upload_id).input["checksum"]
asset_url = f"/api/v1/attempts/{attempt_id}/uploads/{checksum}"
cleaned = s.get(asset_url)
assert cleaned.status_code == 200
assert o.get(asset_url).status_code == 404
with Image.open(io.BytesIO(cleaned.content)) as cleaned_image:
    assert cleaned_image.format == "PNG" and not cleaned_image.getexif() and not cleaned_image.info
with SessionLocal() as db:
    assert db.scalar(select(User).where(User.email == emails["student"]))
print(
    json.dumps(
        {
            "status": "passed",
            "database_role": "otcase_app non-superuser",
            "transport": "live API over private HTTP; real MCP HTTP; Celery Redis worker",
            "cases_hidden_until_explicit_disposable_publication": True,
            "secure_cookie_headers": True,
            "cross_user_attempt_report_job_rejected": True,
            "idempotent_submission": True,
            "educator_amendment": True,
            "analysis_job_completed": True,
            "uploaded_image_metadata_removed_and_scoped": True,
            "attempt_id": attempt_id,
            "public_https_verified": False,
            "reviewed_educational_content": False,
        },
        indent=2,
    )
)
