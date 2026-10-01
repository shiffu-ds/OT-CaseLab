import hashlib
import hmac
import secrets
from datetime import timedelta

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy import func, select

from services.api.config import get_settings
from services.api.database import get_db
from services.api.models import Audit, Consent, LoginFailure, Membership, Session, User, now

hasher = PasswordHasher()
COOKIE = "otcaselab_session"
DUMMY_HASH = hasher.hash(secrets.token_urlsafe(24))


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def verify_password(password, stored):
    try:
        return hasher.verify(stored, password)
    except (VerificationError, InvalidHashError):
        return False


def audit(db, actor, action, obj=None, **details):
    db.add(
        Audit(actor_id=actor.id if actor else None, action=action, object_id=obj, details=details)
    )


def public_user(user):
    return {
        **{k: getattr(user, k) for k in ("id", "email", "name", "role", "language", "cohort_id")},
        "research_consent": getattr(user, "research_consent", False),
    }


def auth_payload(user, session):
    return {
        "user": public_user(user),
        "csrf_token": session.csrf_token,
        "mode": get_settings().provider_mode,
    }


def create_session(db, user, response: Response):
    settings = get_settings()
    token = secrets.token_urlsafe(48)
    session = Session(
        token_hash=digest(token),
        user_id=user.id,
        csrf_token=secrets.token_urlsafe(32),
        expires_at=now() + timedelta(hours=settings.session_hours),
    )
    db.add(session)
    response.set_cookie(
        COOKIE,
        token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.session_hours * 3600,
        path="/",
    )
    return session


def current_user(request: Request, db=Depends(get_db)):
    token = request.cookies.get(COOKIE)
    session = db.get(Session, digest(token)) if token else None
    if not session or session.expires_at <= now():
        raise HTTPException(401, "Please sign in again")
    user = db.get(User, session.user_id)
    membership = (
        db.scalar(
            select(Membership).where(
                Membership.user_id == session.user_id, Membership.cohort_id == user.cohort_id
            )
        )
        if user
        else None
    )
    if not user or not user.active or not membership or membership.role != user.role:
        raise HTTPException(401, "Account access unavailable")
    request.state.session = session
    consent = db.scalar(
        select(Consent).where(Consent.user_id == user.id).order_by(Consent.created_at.desc())
    )
    user.research_consent = bool(consent and consent.granted)
    return user


def require_csrf(request: Request, user=Depends(current_user)):
    token = request.headers.get("X-CSRF-Token", "")
    if not token or not hmac.compare_digest(token, request.state.session.csrf_token):
        raise HTTPException(403, "Refresh the page before trying again")
    return user


def educator(user=Depends(current_user)):
    if user.role not in ("educator", "admin"):
        raise HTTPException(403, "Educator access required")
    return user


def educator_write(user=Depends(require_csrf)):
    if user.role not in ("educator", "admin"):
        raise HTTPException(403, "Educator access required")
    return user


def administrator(user=Depends(current_user)):
    if user.role != "admin":
        raise HTTPException(403, "Administrator access required")
    return user


def administrator_write(user=Depends(require_csrf)):
    if user.role != "admin":
        raise HTTPException(403, "Administrator access required")
    return user


def throttle(db, request, email):
    # Stored counters survive application restart; no raw IP/email in this table.
    ip = request.client.host if request.client else "unknown"
    keys = [digest("email:" + email), digest("ip:" + ip)]
    for key in keys:
        count = db.scalar(
            select(func.count())
            .select_from(LoginFailure)
            .where(LoginFailure.key == key, LoginFailure.created_at > now() - timedelta(minutes=15))
        )
        if count >= 20:
            raise HTTPException(429, "Too many sign-in attempts. Try again in 15 minutes.")
    return keys
