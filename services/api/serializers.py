from sqlalchemy import select

from services.api.models import CaseVersion, Feedback, FeedbackReview, Job, Message, Recommendation


def public_case(version):
    p = version.payload
    asset = p.get("asset", {})
    return {
        "id": version.case_id,
        "version": version.version,
        **{
            key: p.get(key)
            for key in (
                "title",
                "summary",
                "introduction",
                "domain",
                "difficulty",
                "focus",
                "estimated_minutes",
                "patient",
                "objectives",
            )
        },
        "review_status": version.review_status,
        "published": version.published,
        "asset": {key: asset.get(key) for key in ("id", "url", "alt", "origin", "license")},
    }


def public_message(message):
    return {
        key: getattr(message, key)
        for key in ("id", "role", "text", "ordinal", "status", "created_at", "provenance")
    }


def public_job(job):
    return {
        **{
            key: getattr(job, key)
            for key in (
                "id",
                "kind",
                "state",
                "output",
                "error",
                "retry_count",
                "created_at",
                "updated_at",
            )
        },
        "status": job.state,
        "result": job.output,
        "mode": (job.output or {}).get("mode"),
    }


def report_json(db, feedback):
    if not feedback:
        return None
    result = {
        **feedback.report,
        "id": feedback.id,
        "created_at": feedback.created_at.isoformat() + "Z",
    }
    reviews = db.scalars(
        select(FeedbackReview)
        .where(FeedbackReview.feedback_id == feedback.id)
        .order_by(FeedbackReview.created_at)
    ).all()
    result["reviews"] = [
        {
            key: getattr(review, key)
            for key in ("id", "educator_name", "comment", "scores", "created_at")
        }
        for review in reviews
    ]
    if reviews:
        result["review_status"] = "educator_amended"
    recommendation = db.scalar(
        select(Recommendation).where(Recommendation.attempt_id == feedback.attempt_id)
    )
    result["recommendation"] = recommendation.result if recommendation else None
    return result


def attempt_json(db, attempt):
    version = db.get(CaseVersion, attempt.case_version_id)
    feedback = db.scalar(select(Feedback).where(Feedback.attempt_id == attempt.id))
    recommendation = db.scalar(
        select(Recommendation).where(Recommendation.attempt_id == attempt.id)
    )
    return {
        "id": attempt.id,
        "case_id": version.case_id,
        "case_version": version.version,
        "state": attempt.state,
        "language": attempt.language,
        "created_at": attempt.created_at,
        "submitted_at": attempt.submitted_at,
        "error": attempt.error,
        "case": public_case(version),
        "draft": attempt.draft,
        "messages": [
            public_message(m)
            for m in db.scalars(
                select(Message).where(Message.attempt_id == attempt.id).order_by(Message.ordinal)
            )
        ],
        "feedback": report_json(db, feedback),
        "jobs": [
            public_job(j)
            for j in db.scalars(
                select(Job).where(Job.attempt_id == attempt.id).order_by(Job.created_at)
            )
        ],
        "recommendation": recommendation.result if recommendation else None,
    }
