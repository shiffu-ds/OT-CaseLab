import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from services.api.database import Base


def uid():
    return str(uuid.uuid4())


def now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Cohort(Base):
    __tablename__ = "cohorts"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('student','educator','admin')"),
        CheckConstraint("language IN ('en','ur','roman')"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(20), default="student")
    language: Mapped[str] = mapped_column(String(10), default="en")
    cohort_id: Mapped[str] = mapped_column(ForeignKey("cohorts.id"), index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Membership(Base):
    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("user_id", "cohort_id"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    cohort_id: Mapped[str] = mapped_column(ForeignKey("cohorts.id"))
    role: Mapped[str] = mapped_column(String(20))


class LoginFailure(Base):
    __tablename__ = "login_failures"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    key: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now, index=True)


class Session(Base):
    __tablename__ = "sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    csrf_token: Mapped[str] = mapped_column(String(100))
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Case(Base):
    __tablename__ = "cases"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    cohort_id: Mapped[str] = mapped_column(ForeignKey("cohorts.id"), index=True)
    author_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class CaseVersion(Base):
    __tablename__ = "case_versions"
    __table_args__ = (
        UniqueConstraint("case_id", "version"),
        CheckConstraint("review_status IN ('pending_review','reviewed')"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    review_status: Mapped[str] = mapped_column(String(24), default="pending_review")
    published: Mapped[bool] = mapped_column(Boolean, default=False)
    eligible_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    payload: Mapped[dict] = mapped_column(JSON)
    reviewer_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class RubricVersion(Base):
    __tablename__ = "rubric_versions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    case_version_id: Mapped[str] = mapped_column(ForeignKey("case_versions.id"), unique=True)
    dimensions: Mapped[list] = mapped_column(JSON)
    review_status: Mapped[str] = mapped_column(String(24), default="pending_review")


class Asset(Base):
    __tablename__ = "assets"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    cohort_id: Mapped[str] = mapped_column(ForeignKey("cohorts.id"))
    storage_key: Mapped[str] = mapped_column(String(200))
    checksum: Mapped[str] = mapped_column(String(64))
    license: Mapped[str] = mapped_column(String(100))
    origin: Mapped[str] = mapped_column(String(200))
    annotations: Mapped[list] = mapped_column(JSON, default=list)


class ReferencePassage(Base):
    __tablename__ = "reference_passages"
    __table_args__ = (UniqueConstraint("case_version_id", "passage_id"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    case_version_id: Mapped[str] = mapped_column(ForeignKey("case_versions.id"))
    passage_id: Mapped[str] = mapped_column(String(100))
    title: Mapped[str] = mapped_column(String(300))
    text: Mapped[str] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    origin: Mapped[str] = mapped_column(String(200))
    approved: Mapped[bool] = mapped_column(Boolean, default=False)


class Attempt(Base):
    __tablename__ = "attempts"
    __table_args__ = (CheckConstraint("state IN ('active','evaluating','completed','failed')"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    case_version_id: Mapped[str] = mapped_column(ForeignKey("case_versions.id"))
    rubric_version_id: Mapped[str] = mapped_column(ForeignKey("rubric_versions.id"))
    language: Mapped[str] = mapped_column(String(10), default="en")
    state: Mapped[str] = mapped_column(String(20), default="active")
    draft: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (UniqueConstraint("attempt_id", "ordinal"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    attempt_id: Mapped[str] = mapped_column(
        ForeignKey("attempts.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(20))
    text: Mapped[str] = mapped_column(Text)
    ordinal: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="completed")
    provenance: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Submission(Base):
    __tablename__ = "submissions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    attempt_id: Mapped[str] = mapped_column(
        ForeignKey("attempts.id", ondelete="CASCADE"), unique=True
    )
    content: Mapped[dict] = mapped_column(JSON)
    checksum: Mapped[str] = mapped_column(String(64))
    idempotency_key: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (UniqueConstraint("attempt_id", "input_checksum", "kind"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    attempt_id: Mapped[str] = mapped_column(
        ForeignKey("attempts.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(24))
    state: Mapped[str] = mapped_column(String(24), default="queued")
    input_checksum: Mapped[str] = mapped_column(String(64))
    input: Mapped[dict] = mapped_column(JSON)
    output: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)


class Feedback(Base):
    __tablename__ = "feedback"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    attempt_id: Mapped[str] = mapped_column(
        ForeignKey("attempts.id", ondelete="CASCADE"), unique=True
    )
    report: Mapped[dict] = mapped_column(JSON)
    checksum: Mapped[str] = mapped_column(String(64))
    idempotency_key: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class FeedbackReview(Base):
    __tablename__ = "feedback_reviews"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    feedback_id: Mapped[str] = mapped_column(ForeignKey("feedback.id", ondelete="CASCADE"))
    educator_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    educator_name: Mapped[str] = mapped_column(String(100))
    comment: Mapped[str] = mapped_column(Text)
    scores: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Recommendation(Base):
    __tablename__ = "recommendations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    attempt_id: Mapped[str] = mapped_column(
        ForeignKey("attempts.id", ondelete="CASCADE"), unique=True
    )
    input_cutoff: Mapped[datetime] = mapped_column(DateTime, default=now)
    result: Mapped[dict] = mapped_column(JSON)
    mode: Mapped[str] = mapped_column(String(100), default="rule_baseline")


class Consent(Base):
    __tablename__ = "consents"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    version: Mapped[str] = mapped_column(String(30), default="research-consent-v1")
    granted: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class ResearchExport(Base):
    __tablename__ = "research_exports"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    cohort_id: Mapped[str] = mapped_column(ForeignKey("cohorts.id"))
    educator_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    manifest: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Audit(Base):
    __tablename__ = "audit_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    actor_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    action: Mapped[str] = mapped_column(String(100), index=True)
    object_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class ModelRegistry(Base):
    __tablename__ = "model_registry"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    manifest: Mapped[dict] = mapped_column(JSON)
    artifact_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="experimental")
