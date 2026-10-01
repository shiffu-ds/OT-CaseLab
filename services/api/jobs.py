"""Durable image jobs with atomic claims, bounded leases and scoped completion."""

import copy
import hashlib
import math
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path

from sqlalchemy import and_, or_, select, update
from sqlalchemy.exc import OperationalError

from services.api.config import get_settings
from services.api.content import asset_path
from services.api.database import SessionLocal
from services.api.models import Asset, Attempt, Audit, Case, CaseVersion, Job, Membership, User, now

LEASE_SECONDS = 190  # Exceeds the worker's 180-second hard task limit.
executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="image-analysis")
in_flight = set()
guard = threading.Lock()


class JobLeaseBusy(RuntimeError):
    def __init__(self, retry_after):
        self.retry_after = max(1, min(LEASE_SECONDS, math.ceil(float(retry_after))))
        super().__init__(self.retry_after)

    def __str__(self):
        return "Job already has an active inference lease"


def dispatch_job(job_id):
    if get_settings().job_mode == "celery":
        from services.worker.tasks import process_job

        process_job.delay(job_id)
        return
    with guard:
        if job_id in in_flight:
            return
        in_flight.add(job_id)
    future = executor.submit(execute_job, job_id)

    def finished(_):
        with guard:
            in_flight.discard(job_id)

    future.add_done_callback(finished)


def recover_local_jobs():
    """Single-process local startup recovery; never reset active Celery leases."""
    if get_settings().job_mode != "local":
        return []
    with SessionLocal() as db:
        db.execute(
            update(Job)
            .where(Job.state == "running")
            .values(
                state="queued",
                error="Interrupted local inference; queued for retry.",
                updated_at=now(),
            )
        )
        job_ids = list(db.scalars(select(Job.id).where(Job.state == "queued")))
        db.commit()
    for job_id in job_ids:
        dispatch_job(job_id)
    return job_ids


def _assigned_owner(db, job):
    attempt = db.get(Attempt, job.attempt_id)
    owner = db.get(User, attempt.user_id) if attempt else None
    version = db.get(CaseVersion, attempt.case_version_id) if attempt else None
    case = db.get(Case, version.case_id) if version else None
    membership = (
        db.scalar(
            select(Membership).where(
                Membership.user_id == owner.id, Membership.cohort_id == owner.cohort_id
            )
        )
        if owner
        else None
    )
    if (
        not owner
        or not owner.active
        or not case
        or case.cohort_id != owner.cohort_id
        or not membership
        or membership.role != owner.role
    ):
        raise ValueError("Job is outside the active learner/cohort scope")
    return attempt, owner, version


def execute_job(job_id):
    claimed_at = now()
    with SessionLocal() as db:
        claim = db.execute(
            update(Job)
            .where(
                Job.id == job_id,
                or_(
                    Job.state.in_(["queued", "failed"]),
                    and_(
                        Job.state == "running",
                        Job.updated_at <= claimed_at - timedelta(seconds=LEASE_SECONDS),
                    ),
                ),
            )
            .values(
                state="running",
                output=None,
                error=None,
                retry_count=Job.retry_count + 1,
                updated_at=claimed_at,
            )
            .execution_options(synchronize_session=False)
        )
        db.commit()
        job = db.get(Job, job_id)
        if not job:
            return {"status": "deleted", "job_id": job_id}
        if not claim.rowcount:
            if job.state == "running":
                raise JobLeaseBusy(
                    LEASE_SECONDS - (claimed_at - job.updated_at).total_seconds() + 1
                )
            return {"status": job.state, "job_id": job.id}
        claim_count = job.retry_count
        try:
            attempt, owner, version = _assigned_owner(db, job)
            if not attempt.draft.get("observations", "").strip():
                raise ValueError("Learner observations are required before image assistance")
            if job.kind == "image-upload":
                base = Path(get_settings().private_asset_path).resolve()
                path = (base / job.input["storage_key"]).resolve()
                if (
                    path.parent != (base / attempt.id).resolve()
                    or not path.is_file()
                    or hashlib.sha256(path.read_bytes()).hexdigest() != job.input["checksum"]
                ):
                    raise ValueError("Uploaded image is outside authenticated storage scope")
            elif job.kind == "image":
                asset = db.get(Asset, job.input.get("asset_id"))
                if (
                    not asset
                    or asset.cohort_id != owner.cohort_id
                    or version.payload["asset"]["id"] != asset.id
                ):
                    raise ValueError("Asset is not assigned to this attempt")
                path = asset_path(asset)
            else:
                raise ValueError("Unsupported image job kind")
            annotations = (
                copy.deepcopy(version.payload["asset"].get("annotations", []))
                if job.kind == "image"
                else []
            )
            reference_review_status = version.review_status
        except (ConnectionError, OperationalError):
            raise
        except Exception:
            db.execute(
                update(Job)
                .where(
                    Job.id == job_id,
                    Job.state == "running",
                    Job.updated_at == claimed_at,
                    Job.retry_count == claim_count,
                )
                .values(
                    state="failed",
                    error="The assigned educational image is unavailable for this learner",
                    updated_at=now(),
                )
            )
            db.commit()
            return {"status": "failed", "job_id": job_id}
    # No database transaction is held during potentially slow model loading.
    try:
        from ai.cv import analyze_asset

        result = analyze_asset(path, mode=get_settings().cv_mode)
        result["reference_annotations"] = annotations
        result["reference_review_status"] = reference_review_status
        result["notice"] = (
            "Student observations, authored annotations and detector predictions are separate. None establishes accessibility or clinical suitability."
        )
        state, error = "completed", None
    except Exception:
        state, result, error = (
            "failed",
            None,
            "Image inference failed. Check configured model dependencies and try again.",
        )
    with SessionLocal() as db:
        current = db.get(Job, job_id)
        if not current:
            return {"status": "deleted", "job_id": job_id}
        try:
            _, owner, _ = _assigned_owner(db, current)
        except ValueError:
            state, result, error = (
                "failed",
                None,
                "Learner access changed while image inference was running",
            )
            owner = None
        completion = db.execute(
            update(Job)
            .where(
                Job.id == job_id,
                Job.state == "running",
                Job.updated_at == claimed_at,
                Job.retry_count == claim_count,
            )
            .values(state=state, output=result, error=error, updated_at=now())
            .execution_options(synchronize_session=False)
        )
        if not completion.rowcount:
            db.rollback()
            return {"status": "superseded", "job_id": job_id}
        if owner:
            db.add(
                Audit(
                    actor_id=owner.id,
                    action="image.job." + state,
                    object_id=job_id,
                    details={"mode": get_settings().cv_mode},
                )
            )
        db.commit()
    return {"status": state, "job_id": job_id}
