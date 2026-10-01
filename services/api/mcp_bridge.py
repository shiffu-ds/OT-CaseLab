"""One authoritative application-policy gateway used by real internal MCP tools.

Transport verifies signatures. This gateway independently checks live identities,
attempt ownership, cohort scope, permissions, state and exact feedback supports.
"""

import copy
import hashlib
import json
import time

from sqlalchemy import select

from services.api.config import get_settings
from services.api.content import asset_path, grading_case
from services.api.database import SessionLocal
from services.api.models import (
    Asset,
    Attempt,
    Case,
    CaseVersion,
    Feedback,
    Membership,
    Message,
    Recommendation,
    RubricVersion,
    Submission,
    User,
    now,
)
from services.api.policies import visible_case_versions
from services.api.security import audit


class AccessDenied(ValueError):
    pass


def frozen_input(db, attempt):
    submission = db.scalar(select(Submission).where(Submission.attempt_id == attempt.id))
    if not submission:
        raise AccessDenied("A frozen learner submission is required")
    content = copy.deepcopy(submission.content)
    messages = db.scalars(
        select(Message).where(Message.attempt_id == attempt.id).order_by(Message.ordinal)
    ).all()
    content["disclosed_fact_ids"] = list(
        {
            fact
            for m in messages
            if m.role == "patient"
            for fact in m.provenance.get("disclosed_fact_ids", m.provenance.get("fact_ids", []))
        }
    )
    return content, [
        {"id": m.id, "role": m.role, "text": m.text} for m in messages if m.role == "student"
    ]


def validate_report(db, attempt, report):
    if not isinstance(report, dict) or len(json.dumps(report, ensure_ascii=False)) > 200000:
        raise ValueError("Feedback report exceeds bounds")
    version = db.get(CaseVersion, attempt.case_version_id)
    case = grading_case(db, version)
    content, student_messages = frozen_input(db, attempt)
    fields = {k: content[k] for k in ("profile", "observations", "goals", "rationale")}
    messages = {m["id"]: m["text"] for m in student_messages}
    rubric = db.get(RubricVersion, attempt.rubric_version_id)
    anchors = {r["dimension"]: r for r in rubric.dimensions}
    refs = {r["id"]: r for r in case["evidence"] if r["approved"]}
    disclosed = set(content["disclosed_fact_ids"])
    facts = {f["id"]: f for f in case["facts"]}
    items = report.get("items", [])
    if (
        not isinstance(items, list)
        or len(items) != len(anchors)
        or {i.get("dimension") for i in items} != set(anchors)
    ):
        raise ValueError("Feedback must cover the pinned original rubric")
    for item in items:
        anchor = anchors[item["dimension"]]
        if (
            item.get("rubric_anchor") != anchor["anchor"]
            or item.get("max_score") != anchor["max_score"]
        ):
            raise ValueError("Feedback cannot change pinned rubric anchors")
        if type(item.get("score")) is not int or not 0 <= item["score"] <= anchor["max_score"]:
            raise ValueError("Feedback score exceeds rubric bounds")
        spans = item.get("student_evidence", [])
        if not isinstance(spans, list) or len(spans) > 10 or (item["score"] > 0 and not spans):
            raise ValueError("Positive coverage requires exact learner support")
        for span in spans:
            original = (
                messages.get(span.get("message_id"))
                if span.get("message_id")
                else fields.get(span.get("field"))
            )
            start, end = span.get("start"), span.get("end")
            if (
                original is None
                or type(start) is not int
                or type(end) is not int
                or not 0 <= start < end <= len(original)
                or span.get("text") != original[start:end]
            ):
                raise ValueError("Supporting spans must match learner text exactly")
        ref = item.get("reference_passage")
        if ref and (
            ref.get("id") not in refs
            or any(ref.get(k) != refs[ref["id"]].get(k) for k in ("title", "text", "url"))
        ):
            raise ValueError("Unsupported reference passage")
        fact = item.get("case_fact")
        if fact and (fact.get("id") not in facts or fact["id"] not in disclosed):
            raise ValueError("Undisclosed case facts cannot appear in learner feedback")
        if fact and fact.get("text") != facts[fact["id"]]["text"]["en"]:
            raise ValueError("Case fact text must match its permitted source exactly")
        observation = item.get("visual_observation")
        if observation and observation not in [
            a
            for a in case["asset"].get("annotations", [])
            if a.get("review_status") in ("approved", "educator_confirmed")
        ]:
            raise ValueError("Visual support must match a confirmed assigned observation")
        if item.get("review_status") != "provisional":
            raise ValueError("Generated feedback cannot claim educator review")
    if report.get("total") != sum(i["score"] for i in items) or report.get("max_total") != sum(
        i["max_score"] for i in items
    ):
        raise ValueError("Feedback totals do not match items")
    if report.get("review_status") != "provisional":
        raise ValueError("Generated report must remain provisional")
    recommendation = report.get("recommendation", {})
    if recommendation.get("case_id") and recommendation["case_id"] not in {
        v.case_id for v in visible_case_versions(db, db.get(User, attempt.user_id))
    }:
        raise ValueError("Recommended case is not eligible for this learner")
    return copy.deepcopy(report)


def recommend(db, attempt, case):
    from ai import assess_submission

    content, messages = frozen_input(db, attempt)
    report = assess_submission(case, content, messages)
    weak = min(report["items"], key=lambda i: (i["score"] / i["max_score"], i["dimension"]))
    eligible = visible_case_versions(db, db.get(User, attempt.user_id))
    candidates = sorted(
        eligible,
        key=lambda v: (v.case_id == case["id"], v.payload["focus"] != weak["dimension"], v.case_id),
    )
    selected = candidates[0] if candidates else None
    return {
        "case_id": selected.case_id if selected else None,
        "title": selected.payload["title"] if selected else "No eligible next case",
        "domain": weak["dimension"],
        "reason": f"Revisit {weak['label'].lower()}, the lowest provisional coverage dimension. An educator may choose a different focus; keyword coverage is not a diagnosis of skill.",
        "mode": "transparent_rule",
        "input_cutoff": now().isoformat() + "Z",
    }


def gateway(tool_name: str, scope: dict, arguments: dict) -> dict:
    permission = (
        "write"
        if tool_name == "save_feedback"
        else "analyze"
        if tool_name in ("extract_profile", "analyze_case_asset", "assess_rubric")
        else "read"
    )
    if scope.get("exp", 0) <= time.time() or permission not in scope.get("permissions", []):
        raise AccessDenied("Service scope expired or missing permission")
    with SessionLocal() as db:
        user = db.get(User, scope.get("user_id"))
        attempt = db.get(Attempt, scope.get("attempt_id"))
        membership = db.scalar(
            select(Membership).where(
                Membership.user_id == scope.get("user_id"),
                Membership.cohort_id == scope.get("cohort_id"),
            )
        )
        version = db.get(CaseVersion, attempt.case_version_id) if attempt else None
        owner_case = db.get(Case, version.case_id) if version else None
        if (
            not user
            or not user.active
            or not attempt
            or attempt.user_id != user.id
            or user.cohort_id != scope.get("cohort_id")
            or not membership
            or membership.role != user.role
            or not owner_case
            or owner_case.cohort_id != user.cohort_id
        ):
            raise AccessDenied("Attempt is outside authenticated learner/cohort scope")
        case = grading_case(db, version)
        if tool_name == "get_case_context":
            result = {
                "case_id": version.case_id,
                "case_version": version.version,
                "review_status": version.review_status,
                "state": attempt.state,
                "objectives": case["objectives"],
            }
        elif tool_name == "search_approved_evidence":
            from ai import search_evidence

            result = search_evidence(case, arguments["query"], arguments.get("k", 3))
        elif tool_name == "extract_profile":
            from ai.nlp import extract_profile

            content, _ = frozen_input(db, attempt)
            if arguments["text"] != content["profile"]:
                raise ValueError("Analysis must use the frozen scoped learner profile")
            result = extract_profile(content["profile"], get_settings().nlp_mode)
        elif tool_name == "analyze_case_asset":
            from ai.cv import analyze_asset

            if arguments.get("asset_id") != case["asset"]["id"]:
                raise AccessDenied("Asset is not assigned to this attempt")
            if not attempt.draft.get("observations", "").strip():
                raise ValueError("Learner observations are required before assistance")
            asset = db.get(Asset, case["asset"]["id"])
            result = analyze_asset(asset_path(asset), get_settings().cv_mode)
        elif tool_name == "get_learner_history":
            result = {
                "items": [
                    {
                        "attempt_id": a.id,
                        "state": a.state,
                        "case_version_id": a.case_version_id,
                        "created_at": a.created_at.isoformat() + "Z",
                    }
                    for a in db.scalars(
                        select(Attempt)
                        .where(Attempt.user_id == user.id, Attempt.created_at <= attempt.created_at)
                        .order_by(Attempt.created_at.desc())
                        .limit(50)
                    )
                ]
            }
        elif tool_name == "get_evaluation_rubric":
            if attempt.state not in ("evaluating", "completed", "failed"):
                raise AccessDenied("Rubric is restricted to submitted grading tasks")
            rubric = db.get(RubricVersion, attempt.rubric_version_id)
            result = {
                "rubric_version_id": rubric.id,
                "dimensions": rubric.dimensions,
                "review_status": rubric.review_status,
            }
        elif tool_name == "assess_rubric":
            from ai import assess_submission

            content, messages = frozen_input(db, attempt)
            result = assess_submission(case, content, messages)
        elif tool_name == "recommend_next_case":
            result = recommend(db, attempt, case)
        elif tool_name == "save_feedback":
            result = save_feedback(db, attempt, arguments)
        else:
            raise ValueError("Tool is not in the application allowlist")
        audit(db, user, "mcp." + tool_name, attempt.id)
        db.commit()
        if len(json.dumps(result, ensure_ascii=False)) > 250000:
            raise ValueError("Tool response exceeds size limit")
        return result


def save_feedback(db, attempt, arguments):
    report = validate_report(db, attempt, arguments["report"])
    key = arguments["idempotency_key"]
    canonical = copy.deepcopy(report)
    for event in canonical.get("trace", []):
        if event.get("tool") == "save_feedback":
            event["status"] = "completed"
    checksum = hashlib.sha256(
        json.dumps(canonical, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()
    existing = db.scalar(select(Feedback).where(Feedback.attempt_id == attempt.id))
    if existing:
        if existing.idempotency_key != key or existing.checksum != checksum:
            raise ValueError("Idempotent retry conflicts with the stored feedback")
        return {"feedback_id": existing.id, "report": existing.report, "idempotent_retry": True}
    if attempt.state != "evaluating":
        raise AccessDenied("Feedback may only complete a frozen evaluation")
    for event in report.get("trace", []):
        if event.get("tool") == "save_feedback" and event.get("status") == "requested":
            event["status"] = "completed"
    feedback = Feedback(
        attempt_id=attempt.id, report=report, checksum=checksum, idempotency_key=key
    )
    db.add(feedback)
    db.flush()
    attempt.state, attempt.error = "completed", None
    if report.get("recommendation"):
        db.add(
            Recommendation(
                attempt_id=attempt.id,
                result=report["recommendation"],
                mode=report["recommendation"]["mode"],
            )
        )
    return {"feedback_id": feedback.id, "report": report, "idempotent_retry": False}
