import asyncio
import hashlib
import io
import json
import logging
import re
import shutil
import time
from contextlib import asynccontextmanager
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlparse

import anyio
from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    File,
    Header,
    HTTPException,
    Request,
    Response,
    UploadFile,
)
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from sqlalchemy import delete, func, select, text
from sqlalchemy.exc import IntegrityError

from services.api.config import get_settings
from services.api.content import asset_path, create_version, grading_case, validate_case
from services.api.database import SessionLocal, get_db
from services.api.limits import BodyLimitMiddleware
from services.api.models import (
    Asset,
    Attempt,
    Audit,
    Case,
    CaseVersion,
    Cohort,
    Consent,
    Feedback,
    FeedbackReview,
    Job,
    LoginFailure,
    Membership,
    Message,
    ReferencePassage,
    ResearchExport,
    RubricVersion,
    Session,
    Submission,
    User,
    now,
)
from services.api.policies import authorized_attempt, owned_case, visible_case_versions
from services.api.reports import markdown_report
from services.api.schemas import (
    AnalysisCreate,
    AttemptCreate,
    CaseInput,
    ConsentInput,
    Draft,
    Login,
    MessageCreate,
    Plan,
    Preferences,
    Publish,
    Register,
    Review,
    RoleChange,
)
from services.api.security import (
    COOKIE,
    DUMMY_HASH,
    administrator,
    administrator_write,
    audit,
    auth_payload,
    create_session,
    current_user,
    digest,
    educator,
    educator_write,
    hasher,
    public_user,
    require_csrf,
    throttle,
    verify_password,
)
from services.api.serializers import (
    attempt_json,
    public_case,
    public_job,
    public_message,
    report_json,
)

logger = logging.getLogger("otcaselab")


@asynccontextmanager
async def lifespan(_):
    with SessionLocal() as db:
        db.execute(text("SELECT 1"))
        # An interrupted local evaluation becomes explicitly retryable, never silently successful.
        for attempt in db.scalars(select(Attempt).where(Attempt.state == "evaluating")):
            if db.scalar(select(Feedback.id).where(Feedback.attempt_id == attempt.id)):
                attempt.state, attempt.error = "completed", None
            else:
                attempt.state, attempt.error = (
                    "failed",
                    "Evaluation interrupted; retry the original submission.",
                )
        db.commit()
        if get_settings().job_mode == "local":
            from services.api.jobs import recover_local_jobs

            recover_local_jobs()
    yield


app = FastAPI(title="OTCaseLab API", version="0.1.0", lifespan=lifespan)
app.add_middleware(BodyLimitMiddleware)


@app.middleware("http")
async def protections(request, call_next):
    started = time.monotonic()
    settings = get_settings()
    length = request.headers.get("content-length", "0")
    if not length.isdigit() or int(length) > settings.request_limit_bytes:
        return JSONResponse({"detail": "Request exceeds size limit"}, status_code=413)
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        origin = request.headers.get("origin")
        allowed_origin = not origin or origin.rstrip("/") == settings.app_origin.rstrip("/")
        if origin and settings.environment == "development":
            try:
                expected, received = urlparse(settings.app_origin), urlparse(origin)
                loopback = {"localhost", "127.0.0.1"}
                allowed_origin = allowed_origin or (
                    expected.scheme == received.scheme == "http"
                    and expected.hostname in loopback
                    and received.hostname in loopback
                    and expected.port == received.port
                )
            except ValueError:
                allowed_origin = False
        if not allowed_origin:
            return JSONResponse({"detail": "Request origin is not allowed"}, status_code=403)
        if request.url.path in ("/api/v1/auth/login", "/api/v1/auth/register") and not origin:
            return JSONResponse(
                {"detail": "Sign-in requests require the application Origin header"},
                status_code=403,
            )
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Server-Timing"] = f"api;dur={(time.monotonic() - started) * 1000:.1f}"
    return response


@app.exception_handler(IntegrityError)
async def conflict_handler(_, exc):
    # Never serialize SQL (which can contain input text or credential hashes).
    return JSONResponse(
        {"detail": "This action conflicted with another update. Refresh and retry."},
        status_code=409,
    )


@app.get("/api/v1/health")
@app.get("/api/v1/ready")
def health(db=Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {
        "status": "ok",
        "version": "0.1.0",
        "provider_mode": get_settings().provider_mode,
        "environment": get_settings().environment,
    }


@app.post("/api/v1/auth/register", status_code=201)
def register(body: Register, request: Request, response: Response, db=Depends(get_db)):
    keys = throttle(db, request, body.email)
    if db.scalar(select(User).where(User.email == body.email)):
        raise HTTPException(409, "An account with this email already exists")
    if not get_settings().allow_demo:
        raise HTTPException(403, "Registration requires an institutional invitation")
    if not db.get(Cohort, "demo"):
        raise HTTPException(503, "The learning studio has not been initialized")
    user = User(
        email=body.email,
        name=body.name,
        password_hash=hasher.hash(body.password),
        language=body.language,
        role="student",
        cohort_id="demo",
    )
    db.add(user)
    db.flush()
    db.add(Membership(user_id=user.id, cohort_id="demo", role="student"))
    session = create_session(db, user, response)
    for key in keys:
        db.add(LoginFailure(key=key))
    audit(db, user, "account.registered")
    db.commit()
    return auth_payload(user, session)


@app.post("/api/v1/auth/login")
def login(body: Login, request: Request, response: Response, db=Depends(get_db)):
    keys = throttle(db, request, body.email)
    user = db.scalar(select(User).where(User.email == body.email))
    valid = verify_password(body.password, user.password_hash if user else DUMMY_HASH)
    if not user or not valid or not user.active:
        for key in keys:
            db.add(LoginFailure(key=key))
        db.commit()
        raise HTTPException(401, "Email or password is incorrect")
    if hasher.check_needs_rehash(user.password_hash):
        user.password_hash = hasher.hash(body.password)
    old = request.cookies.get(COOKIE)
    if old:
        db.execute(delete(Session).where(Session.token_hash == digest(old)))
    session = create_session(db, user, response)
    audit(db, user, "session.created")
    db.commit()
    return auth_payload(user, session)


@app.get("/api/v1/auth/me")
def me(request: Request, user=Depends(current_user)):
    return auth_payload(user, request.state.session)


@app.patch("/api/v1/auth/me")
def preferences(
    body: Preferences, request: Request, user=Depends(require_csrf), db=Depends(get_db)
):
    user.language = body.language
    db.commit()
    return auth_payload(user, request.state.session)


@app.post("/api/v1/auth/logout")
def logout(request: Request, response: Response, user=Depends(require_csrf), db=Depends(get_db)):
    db.delete(request.state.session)
    audit(db, user, "session.revoked")
    db.commit()
    response.delete_cookie(COOKIE, path="/")
    return {"ok": True}


@app.get("/api/v1/cases")
def cases(user=Depends(current_user), db=Depends(get_db)):
    return {"items": [public_case(v) for v in visible_case_versions(db, user)]}


@app.get("/api/v1/cases/{case_id}")
def case_detail(case_id: str, user=Depends(current_user), db=Depends(get_db)):
    version = next((v for v in visible_case_versions(db, user) if v.case_id == case_id), None)
    if not version:
        raise HTTPException(404, "Case not found")
    return public_case(version)


@app.get("/api/v1/assets/{asset_id}")
def asset_file(asset_id: str, user=Depends(current_user), db=Depends(get_db)):
    asset = db.get(Asset, asset_id)
    if not asset or asset.cohort_id != user.cohort_id:
        raise HTTPException(404, "Asset not found")
    if user.role == "student" and not any(
        v.payload.get("asset", {}).get("id") == asset_id for v in visible_case_versions(db, user)
    ):
        raise HTTPException(404, "Asset not found")
    return FileResponse(
        asset_path(asset),
        media_type="image/svg+xml",
        headers={
            "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; sandbox"
        },
    )


@app.get("/api/v1/evidence")
def evidence(case_id: str, q: str = "", user=Depends(current_user), db=Depends(get_db)):
    version = next((v for v in visible_case_versions(db, user) if v.case_id == case_id), None)
    if not version:
        raise HTTPException(404, "Case not found")
    if len(q) > 1000:
        raise HTTPException(422, "Search text is too long")
    from ai import search_evidence

    case = grading_case(db, version)
    if q:
        output = search_evidence(case, q, 5)
        items = output.get("results", output.get("items", []))
    else:
        items = [p for p in case["evidence"] if p["approved"]]
    return {
        "items": [{k: p.get(k) for k in ("id", "title", "text", "url", "origin")} for p in items],
        "status": "educator_approved" if items else "awaiting_educator_approval",
    }


@app.post("/api/v1/attempts", status_code=201)
def create_attempt(body: AttemptCreate, user=Depends(require_csrf), db=Depends(get_db)):
    if user.role != "student":
        raise HTTPException(403, "Use a student account to practice")
    version = next((v for v in visible_case_versions(db, user) if v.case_id == body.case_id), None)
    if not version:
        raise HTTPException(404, "Case not found")
    recent = db.scalar(
        select(func.count())
        .select_from(Attempt)
        .where(Attempt.user_id == user.id, Attempt.created_at > now() - timedelta(hours=1))
    )
    if recent >= 30:
        raise HTTPException(429, "Practice session limit reached. Try again later.")
    rubric = db.scalar(select(RubricVersion).where(RubricVersion.case_version_id == version.id))
    attempt = Attempt(
        user_id=user.id,
        case_version_id=version.id,
        rubric_version_id=rubric.id,
        language=body.language,
        draft=Draft().model_dump(),
    )
    db.add(attempt)
    db.flush()
    intro = version.payload["introduction"].get(
        body.language, version.payload["introduction"]["en"]
    )
    db.add(
        Message(
            attempt_id=attempt.id,
            role="patient",
            text=intro,
            ordinal=0,
            provenance={"provider": "authored_intro", "case_version": version.version},
        )
    )
    audit(db, user, "attempt.created", attempt.id)
    db.commit()
    return attempt_json(db, attempt)


@app.get("/api/v1/attempts")
def list_attempts(limit: int = 50, offset: int = 0, user=Depends(current_user), db=Depends(get_db)):
    if not 1 <= limit <= 100 or offset < 0:
        raise HTTPException(422, "Invalid pagination")
    items = db.scalars(
        select(Attempt)
        .where(Attempt.user_id == user.id)
        .order_by(Attempt.created_at.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return {"items": [attempt_json(db, a) for a in items], "limit": limit, "offset": offset}


@app.get("/api/v1/attempts/{attempt_id}")
def get_attempt(attempt_id: str, user=Depends(current_user), db=Depends(get_db)):
    return attempt_json(db, authorized_attempt(db, attempt_id, user))


@app.patch("/api/v1/attempts/{attempt_id}/draft")
def save_draft(attempt_id: str, body: Draft, user=Depends(require_csrf), db=Depends(get_db)):
    attempt = authorized_attempt(db, attempt_id, user, False)
    if attempt.state != "active":
        raise HTTPException(409, "Submitted attempts are frozen")
    attempt.draft = body.model_dump()
    db.commit()
    return attempt_json(db, attempt)


async def interview(attempt_id, body, request, user, db):
    attempt = authorized_attempt(db, attempt_id, user, False)
    if attempt.state != "active":
        raise HTTPException(409, "This attempt is no longer open for interview")
    messages = db.scalars(
        select(Message).where(Message.attempt_id == attempt.id).order_by(Message.ordinal)
    ).all()
    if len(messages) >= 101:
        raise HTTPException(429, "Interview message budget reached")
    if messages and messages[-1].created_at > now() - timedelta(seconds=1):
        raise HTTPException(429, "Please wait a moment before sending another message")
    case = grading_case(db, db.get(CaseVersion, attempt.case_version_id))
    from ai import extract_profile, patient_reply

    try:
        result = await anyio.to_thread.run_sync(
            lambda: patient_reply(
                case, [public_message(m) for m in messages], body.text, attempt.language
            )
        )
    except Exception:
        audit(db, user, "provider.failed", attempt.id, mode=get_settings().provider_mode)
        db.commit()
        raise HTTPException(
            503, "The patient reply could not be generated. Your interview remains open; try again."
        ) from None
    if await request.is_disconnected():
        raise HTTPException(499, "Request cancelled before the reply was saved")
    if (
        not isinstance(result.get("text"), str)
        or not result["text"].strip()
        or len(result["text"]) > 6000
    ):
        raise HTTPException(503, "Patient output did not pass validation")
    # Re-check the mutable attempt after the slow provider operation.
    db.refresh(attempt)
    if attempt.state != "active":
        raise HTTPException(409, "Attempt was submitted while generating the reply")
    ordinal = max((m.ordinal for m in messages), default=-1) + 1
    student = Message(
        attempt_id=attempt.id,
        role="student",
        text=body.text,
        ordinal=ordinal,
        provenance={"source": "learner"},
    )
    patient = Message(
        attempt_id=attempt.id,
        role="patient",
        text=result["text"],
        ordinal=ordinal + 1,
        provenance={
            **result.get("provenance", {}),
            "mode": result.get("mode"),
            "disclosed_fact_ids": result.get("disclosed_fact_ids", []),
        },
    )
    db.add_all([student, patient])
    audit(db, user, "interview.completed", attempt.id, provider=result.get("mode"))
    db.commit()
    return {
        "student_message": public_message(student),
        "patient_message": public_message(patient),
        "extraction": extract_profile(body.text),
        "mode": result.get("mode"),
    }


@app.post("/api/v1/attempts/{attempt_id}/messages")
async def message(
    attempt_id: str,
    body: MessageCreate,
    request: Request,
    user=Depends(require_csrf),
    db=Depends(get_db),
):
    return await interview(attempt_id, body, request, user, db)


@app.post("/api/v1/attempts/{attempt_id}/messages/stream")
async def message_stream(
    attempt_id: str,
    body: MessageCreate,
    request: Request,
    user=Depends(require_csrf),
    db=Depends(get_db),
):
    # Honest event stream: bounded generation completes and validates before delivery;
    # this is not represented as token streaming.
    result = await interview(attempt_id, body, request, user, db)

    async def events():
        yield (
            "event: completed\ndata: "
            + json.dumps(result, default=str, ensure_ascii=False)
            + "\n\n"
        )

    return StreamingResponse(events(), media_type="text/event-stream")


@app.post("/api/v1/attempts/{attempt_id}/submit")
async def submit(
    attempt_id: str,
    body: Plan,
    idempotency_key: str = Header(default="", max_length=200),
    user=Depends(require_csrf),
    db=Depends(get_db),
):
    attempt = authorized_attempt(db, attempt_id, user, False)
    if not idempotency_key.strip():
        raise HTTPException(422, "Idempotency-Key is required")
    content = body.model_dump()
    checksum = hashlib.sha256(
        json.dumps(content, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()
    original = db.scalar(select(Submission).where(Submission.attempt_id == attempt.id))
    if original:
        if original.idempotency_key != idempotency_key or original.checksum != checksum:
            raise HTTPException(409, "This attempt already has a different frozen submission")
        if attempt.state == "completed":
            return attempt_json(db, attempt)
        if attempt.state == "evaluating":
            raise HTTPException(409, "Evaluation is already running; refresh shortly")
    if not db.scalar(
        select(Message.id).where(Message.attempt_id == attempt.id, Message.role == "student")
    ):
        raise HTTPException(422, "Interview the patient before submitting")
    case = grading_case(db, db.get(CaseVersion, attempt.case_version_id))
    approved = {p["id"] for p in case["evidence"] if p["approved"]}
    if any(eid not in approved for eid in content["evidence_ids"]):
        raise HTTPException(422, "Selected evidence is not approved for this case")
    if not original:
        db.add(
            Submission(
                attempt_id=attempt.id,
                content=content,
                checksum=checksum,
                idempotency_key=idempotency_key,
            )
        )
    attempt.draft, attempt.state, attempt.error, attempt.submitted_at = (
        content,
        "evaluating",
        None,
        now(),
    )
    audit(db, user, "submission.frozen", attempt.id, checksum=checksum)
    db.commit()
    scope = {
        "user_id": user.id,
        "attempt_id": attempt.id,
        "cohort_id": user.cohort_id,
        "permissions": ["read", "analyze", "write"],
        "exp": int(time.time()) + min(300, get_settings().agent_deadline_seconds + 30),
    }
    try:
        from ai.agent import run_feedback

        await asyncio.wait_for(
            run_feedback(scope, content), timeout=get_settings().agent_deadline_seconds
        )
    except Exception:
        db.expire_all()
        attempt = db.get(Attempt, attempt_id)
        # A timed-out protocol reply may follow a successful idempotent save.
        if not db.scalar(select(Feedback).where(Feedback.attempt_id == attempt_id)):
            attempt.state, attempt.error = (
                "failed",
                "Feedback could not complete. Retry the same frozen submission.",
            )
            audit(db, user, "feedback.failed", attempt.id)
            db.commit()
            raise HTTPException(503, attempt.error) from None
    db.expire_all()
    attempt = db.get(Attempt, attempt_id)
    return attempt_json(db, attempt)


@app.get("/api/v1/attempts/{attempt_id}/feedback")
def feedback(attempt_id: str, user=Depends(current_user), db=Depends(get_db)):
    attempt = authorized_attempt(db, attempt_id, user)
    result = report_json(db, db.scalar(select(Feedback).where(Feedback.attempt_id == attempt.id)))
    if not result:
        raise HTTPException(404, "Feedback is not available yet")
    return result


@app.get("/api/v1/attempts/{attempt_id}/report")
def report(attempt_id: str, user=Depends(current_user), db=Depends(get_db)):
    attempt = authorized_attempt(db, attempt_id, user)
    return Response(
        markdown_report(db, attempt),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="otcaselab-{attempt.id}.md"'},
    )


@app.post("/api/v1/attempts/{attempt_id}/analysis", status_code=202)
def analyze(
    attempt_id: str,
    body: AnalysisCreate,
    background: BackgroundTasks,
    user=Depends(require_csrf),
    db=Depends(get_db),
):
    attempt = authorized_attempt(db, attempt_id, user, False)
    version = db.get(CaseVersion, attempt.case_version_id)
    if not attempt.draft.get("observations", "").strip():
        raise HTTPException(422, "Write your own observations before requesting assistance")
    if body.asset_id != version.payload["asset"]["id"]:
        raise HTTPException(404, "Asset is not assigned to this attempt")
    asset = db.get(Asset, body.asset_id)
    checksum = asset.checksum + ":" + get_settings().cv_mode
    job = db.scalar(
        select(Job).where(
            Job.attempt_id == attempt.id, Job.input_checksum == checksum, Job.kind == "image"
        )
    )
    if not job:
        job = Job(
            attempt_id=attempt.id,
            kind="image",
            input_checksum=checksum,
            input={"asset_id": asset.id},
        )
        db.add(job)
        db.flush()
        db.commit()
    if job.state in ("queued", "failed"):
        from services.api.jobs import dispatch_job

        background.add_task(dispatch_job, job.id)
    return public_job(job)


@app.get("/api/v1/jobs/{job_id}")
def get_job(job_id: str, user=Depends(current_user), db=Depends(get_db)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    authorized_attempt(db, job.attempt_id, user)
    return public_job(job)


@app.post("/api/v1/attempts/{attempt_id}/uploads", status_code=202)
async def upload_image(
    attempt_id: str,
    background: BackgroundTasks,
    file: UploadFile = File(...),
    user=Depends(require_csrf),
    db=Depends(get_db),
):
    from PIL import Image, ImageOps, UnidentifiedImageError

    attempt = authorized_attempt(db, attempt_id, user, False)
    if not attempt.draft.get("observations", "").strip():
        raise HTTPException(
            422, "Write your own observations before uploading an educational image"
        )
    data = await file.read(5 * 1024 * 1024 + 1)
    if len(data) > 5 * 1024 * 1024:
        raise HTTPException(413, "Educational images must be 5 MB or smaller")
    try:
        with Image.open(io.BytesIO(data)) as source:
            if source.format not in ("JPEG", "PNG") or source.width * source.height > 12_000_000:
                raise ValueError("Unsupported image or dimensions")
            image = ImageOps.exif_transpose(source).convert("RGB")
            image.load()
            image.info.clear()
    except (UnidentifiedImageError, ValueError, OSError, Image.DecompressionBombError):
        raise HTTPException(
            422, "Use a valid PNG or JPEG educational image up to 12 megapixels"
        ) from None
    clean = io.BytesIO()
    image.save(clean, format="PNG", optimize=True)
    checksum = hashlib.sha256(clean.getvalue()).hexdigest()
    key = checksum + ":" + get_settings().cv_mode
    existing = db.scalar(
        select(Job).where(
            Job.attempt_id == attempt.id, Job.kind == "image-upload", Job.input_checksum == key
        )
    )
    if existing:
        if existing.state in ("queued", "failed"):
            from services.api.jobs import dispatch_job

            background.add_task(dispatch_job, existing.id)
        return public_job(existing)
    directory = Path(get_settings().private_asset_path) / attempt.id
    directory.mkdir(parents=True, exist_ok=True)
    filename = checksum + ".png"
    path = directory / filename
    path.write_bytes(clean.getvalue())
    path.chmod(0o600)
    job = Job(
        attempt_id=attempt.id,
        kind="image-upload",
        input_checksum=key,
        input={
            "storage_key": f"{attempt.id}/{filename}",
            "checksum": checksum,
            "origin": "learner-supplied educational image",
            "metadata_removed": True,
        },
    )
    db.add(job)
    db.flush()
    audit(db, user, "image.uploaded", job.id, metadata_removed=True)
    db.commit()
    from services.api.jobs import dispatch_job

    background.add_task(dispatch_job, job.id)
    return public_job(job)


@app.get("/api/v1/attempts/{attempt_id}/uploads/{checksum}")
def uploaded_image(attempt_id: str, checksum: str, user=Depends(current_user), db=Depends(get_db)):
    attempt = authorized_attempt(db, attempt_id, user)
    if not re.fullmatch(r"[0-9a-f]{64}", checksum):
        raise HTTPException(404, "Educational upload not found")
    job = db.scalar(
        select(Job).where(
            Job.attempt_id == attempt.id,
            Job.kind == "image-upload",
            Job.input_checksum.startswith(checksum + ":"),
        )
    )
    if not job:
        raise HTTPException(404, "Educational upload not found")
    path = Path(get_settings().private_asset_path) / attempt.id / (checksum + ".png")
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != checksum:
        raise HTTPException(404, "Educational upload not found")
    return FileResponse(path, media_type="image/png", headers={"Cache-Control": "no-store"})


@app.get("/api/v1/progress")
def progress(user=Depends(current_user), db=Depends(get_db)):
    attempts = db.scalars(
        select(Attempt).where(Attempt.user_id == user.id).order_by(Attempt.created_at.desc())
    ).all()
    completed = [a for a in attempts if a.state == "completed"]
    scores = {}
    for attempt in completed:
        f = db.scalar(select(Feedback).where(Feedback.attempt_id == attempt.id))
        if f:
            for item in f.report["items"]:
                scores.setdefault(item["dimension"], []).append(item["score"])
    last = attempt_json(db, completed[0]) if completed else None
    return {
        "completed": len(completed),
        "active": sum(a.state == "active" for a in attempts),
        "domain_scores": {
            d: {"score": round(sum(v) / len(v), 2), "max_score": 3, "count": len(v)}
            for d, v in scores.items()
        },
        "history": [
            {
                "id": a.id,
                "case_id": db.get(CaseVersion, a.case_version_id).case_id,
                "state": a.state,
                "created_at": a.created_at,
            }
            for a in attempts
        ],
        "recommendation": last["recommendation"] if last else None,
        "score_mode": "provisional_baseline_coverage",
    }


@app.get("/api/v1/educator/cases")
def educator_cases(user=Depends(educator), db=Depends(get_db)):
    versions = db.scalars(
        select(CaseVersion)
        .join(Case)
        .where(Case.cohort_id == user.cohort_id)
        .order_by(CaseVersion.case_id, CaseVersion.version.desc())
    ).all()
    return {
        "items": [
            {
                **grading_case(db, v),
                "published": v.published,
                "review_status": v.review_status,
                "review_note": v.review_note,
                "version": v.version,
            }
            for v in versions
        ]
    }


@app.post("/api/v1/educator/cases", status_code=201)
def educator_create_case(body: CaseInput, user=Depends(educator_write), db=Depends(get_db)):
    payload = validate_case(body.case)
    asset = db.get(Asset, payload["asset"]["id"])
    if not asset or asset.cohort_id != user.cohort_id:
        raise HTTPException(404, "Educational asset is outside your cohort")
    if db.get(Case, payload["id"]):
        raise HTTPException(409, "Choose a new case identifier")
    case = Case(id=payload["id"], cohort_id=user.cohort_id, author_id=user.id)
    db.add(case)
    db.flush()
    version = create_version(db, case, payload, 1)
    audit(db, user, "case.created", case.id)
    db.commit()
    return {**version.payload, "published": False}


@app.post("/api/v1/educator/cases/{case_id}/versions", status_code=201)
def educator_version_case(
    case_id: str, body: CaseInput, user=Depends(educator_write), db=Depends(get_db)
):
    case = owned_case(db, case_id, user)
    payload = validate_case(body.case, case_id)
    asset = db.get(Asset, payload["asset"]["id"])
    if not asset or asset.cohort_id != user.cohort_id:
        raise HTTPException(404, "Educational asset is outside your cohort")
    number = (
        db.scalar(select(func.max(CaseVersion.version)).where(CaseVersion.case_id == case_id)) + 1
    )
    version = create_version(db, case, payload, number)
    audit(db, user, "case.versioned", case.id, version=number)
    db.commit()
    return {**version.payload, "published": False}


@app.post("/api/v1/educator/cases/{case_id}/publish")
def publish_case(case_id: str, body: Publish, user=Depends(educator_write), db=Depends(get_db)):
    owned_case(db, case_id, user)
    version = db.scalar(
        select(CaseVersion)
        .where(CaseVersion.case_id == case_id)
        .order_by(CaseVersion.version.desc())
    )
    if version.published:
        raise HTTPException(409, "This version is already published; create a new version to edit")
    (
        version.published,
        version.review_status,
        version.reviewer_id,
        version.review_note,
        version.reviewed_at,
    ) = True, "reviewed", user.id, body.review_note, now()
    rubric = db.scalar(select(RubricVersion).where(RubricVersion.case_version_id == version.id))
    rubric.review_status = "reviewed"
    for ref in db.scalars(
        select(ReferencePassage).where(ReferencePassage.case_version_id == version.id)
    ):
        ref.approved = True
    audit(db, user, "case.published", case_id, version=version.version)
    db.commit()
    return public_case(version)


@app.get("/api/v1/educator/attempts")
def educator_attempts(limit: int = 50, offset: int = 0, user=Depends(educator), db=Depends(get_db)):
    if not 1 <= limit <= 100 or offset < 0:
        raise HTTPException(422, "Invalid pagination")
    attempts = db.scalars(
        select(Attempt)
        .join(User)
        .where(User.cohort_id == user.cohort_id)
        .order_by(Attempt.created_at.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return {
        "items": [
            {**attempt_json(db, a), "learner": public_user(db.get(User, a.user_id))}
            for a in attempts
        ]
    }


@app.post("/api/v1/educator/attempts/{attempt_id}/review")
def review_attempt(attempt_id: str, body: Review, user=Depends(educator_write), db=Depends(get_db)):
    attempt = authorized_attempt(db, attempt_id, user)
    f = db.scalar(select(Feedback).where(Feedback.attempt_id == attempt.id))
    if not f:
        raise HTTPException(409, "Feedback has not completed")
    maxima = {i["dimension"]: i["max_score"] for i in f.report["items"]}
    if any(d not in maxima or score < 0 or score > maxima[d] for d, score in body.scores.items()):
        raise HTTPException(422, "Educator scores must match original rubric bounds")
    db.add(
        FeedbackReview(
            feedback_id=f.id,
            educator_id=user.id,
            educator_name=user.name,
            comment=body.comment,
            scores=body.scores,
        )
    )
    audit(db, user, "feedback.amended", f.id)
    db.commit()
    return report_json(db, f)


@app.post("/api/v1/privacy/consent")
def consent(body: ConsentInput, user=Depends(require_csrf), db=Depends(get_db)):
    db.add(Consent(user_id=user.id, granted=body.granted))
    audit(db, user, "consent.updated", granted=body.granted)
    db.commit()
    return {
        "granted": body.granted,
        "version": "research-consent-v1",
        "research_collection_active": False,
    }


@app.delete("/api/v1/privacy/me")
def delete_me(response: Response, user=Depends(require_csrf), db=Depends(get_db)):
    if user.role != "student":
        raise HTTPException(409, "Educator account deletion requires institutional handover")
    actor_id = user.id
    upload_attempts = list(db.scalars(select(Attempt.id).where(Attempt.user_id == user.id)))
    db.delete(user)
    audit(db, None, "account.deleted")
    # Unlink prior audit identity; retain only operational events without learner text.
    for event in db.scalars(select(Audit).where(Audit.actor_id == actor_id)):
        event.actor_id, event.object_id, event.details = None, None, {}
    db.commit()
    for attempt_id in upload_attempts:
        directory = Path(get_settings().private_asset_path) / attempt_id
        if directory.is_dir():
            shutil.rmtree(directory)
    response.delete_cookie(COOKIE, path="/")
    return {
        "ok": True,
        "deleted": "account, sessions, attempts, submissions, reports and consent records",
    }


@app.get("/api/v1/admin/users")
def admin_users(user=Depends(administrator), db=Depends(get_db)):
    users = db.scalars(
        select(User).where(User.cohort_id == user.cohort_id).order_by(User.name)
    ).all()
    return {"items": [public_user(u) for u in users]}


@app.post("/api/v1/admin/users/{user_id}/role")
def admin_user_role(
    user_id: str, body: RoleChange, user=Depends(administrator_write), db=Depends(get_db)
):
    target = db.get(User, user_id)
    if not target or target.cohort_id != user.cohort_id:
        raise HTTPException(404, "User not found")
    if target.role == "admin":
        raise HTTPException(409, "Administrator handover requires the account management command")
    membership = db.scalar(
        select(Membership).where(
            Membership.user_id == target.id, Membership.cohort_id == user.cohort_id
        )
    )
    target.role, membership.role = body.role, body.role
    db.execute(delete(Session).where(Session.user_id == target.id))
    audit(db, user, "membership.role.changed", target.id, role=body.role)
    db.commit()
    return public_user(target)


@app.get("/api/v1/admin/operations")
def admin_operations(user=Depends(administrator), db=Depends(get_db)):
    settings = get_settings()
    users = select(User.id).where(User.cohort_id == user.cohort_id)
    events = db.scalars(
        select(Audit).where(Audit.actor_id.in_(users)).order_by(Audit.created_at.desc()).limit(100)
    ).all()
    return {
        "cohort_id": user.cohort_id,
        "health": "ok",
        "modes": {
            "dialogue": settings.provider_mode,
            "nlp": settings.nlp_mode,
            "vision": settings.cv_mode,
            "workflow": settings.agent_planner,
            "jobs": settings.job_mode,
            "mcp": settings.mcp_transport,
        },
        "limits": {
            "attempts_per_hour": 30,
            "interview_exchanges_per_attempt": 50,
            "image_upload_mb": 5,
            "agent_max_calls": settings.agent_max_calls,
            "agent_deadline_seconds": settings.agent_deadline_seconds,
        },
        "audit_events": [
            {"id": e.id, "action": e.action, "created_at": e.created_at} for e in events
        ],
        "configuration_note": "Runtime mode changes use the deployment environment and a controlled restart.",
    }


@app.get("/api/v1/educator/research-export")
def research_export(user=Depends(educator), db=Depends(get_db)):
    import hmac

    settings = get_settings()
    if not settings.research_exports_enabled or len(settings.research_export_secret) < 32:
        raise HTTPException(
            403,
            "Research export is disabled pending institutional authorization and a dedicated export key",
        )

    def pseudonym(value):
        return hmac.new(
            settings.research_export_secret.encode(), value.encode(), hashlib.sha256
        ).hexdigest()[:24]

    rows = []
    for owner in db.scalars(
        select(User).where(User.cohort_id == user.cohort_id, User.role == "student")
    ):
        latest = db.scalar(
            select(Consent).where(Consent.user_id == owner.id).order_by(Consent.created_at.desc())
        )
        if not latest or not latest.granted:
            continue
        for attempt in db.scalars(
            select(Attempt).where(Attempt.user_id == owner.id, Attempt.state == "completed")
        ):
            f = db.scalar(select(Feedback).where(Feedback.attempt_id == attempt.id))
            reviews = db.scalars(
                select(FeedbackReview)
                .where(FeedbackReview.feedback_id == f.id)
                .order_by(FeedbackReview.created_at)
            ).all()
            version = db.get(CaseVersion, attempt.case_version_id)
            rows.append(
                {
                    "learner_group": pseudonym("learner:" + owner.id),
                    "attempt_key": pseudonym("attempt:" + attempt.id),
                    "case_id": version.case_id,
                    "case_version": version.version,
                    "case_review_status": version.review_status,
                    "language": attempt.language,
                    "baseline_scores": {i["dimension"]: i["score"] for i in f.report["items"]},
                    "educator_scores": reviews[-1].scores if reviews else None,
                    "mode": f.report["mode"],
                    "consent_version": latest.version,
                }
            )
    manifest = {
        "version": "structured-export-v1",
        "record_count": len(rows),
        "created_at": now().isoformat() + "Z",
        "excluded": [
            "names",
            "email",
            "dialogue",
            "submitted free text",
            "images",
            "withdrawn and unconsented learners",
        ],
    }
    export = ResearchExport(cohort_id=user.cohort_id, educator_id=user.id, manifest=manifest)
    db.add(export)
    audit(db, user, "research.exported", record_count=len(rows))
    db.commit()
    return {
        "manifest": manifest,
        "items": rows,
        "status": "pseudonymized structured records; not a validated research dataset",
    }
