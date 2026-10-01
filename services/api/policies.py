from fastapi import HTTPException
from sqlalchemy import select

from services.api.config import get_settings
from services.api.models import Attempt, Case, CaseVersion, User


def can_view_version(version):
    return version.published or (get_settings().allow_demo and version.eligible_demo)


def authorized_attempt(db, attempt_id, user, allow_educator=True):
    attempt = db.get(Attempt, attempt_id)
    if not attempt:
        raise HTTPException(404, "Attempt not found")
    owner = db.get(User, attempt.user_id)
    permitted = attempt.user_id == user.id or (
        allow_educator
        and user.role in ("educator", "admin")
        and owner
        and owner.cohort_id == user.cohort_id
    )
    if not permitted:
        raise HTTPException(404, "Attempt not found")
    return attempt


def owned_case(db, case_id, user):
    case = db.get(Case, case_id)
    if not case or case.cohort_id != user.cohort_id:
        raise HTTPException(404, "Case not found")
    return case


def visible_case_versions(db, user):
    versions = db.scalars(
        select(CaseVersion)
        .join(Case)
        .where(Case.cohort_id == user.cohort_id)
        .order_by(CaseVersion.version.desc())
    ).all()
    selected = {}
    for version in versions:
        if version.case_id not in selected and can_view_version(version):
            selected[version.case_id] = version
    return list(selected.values())
