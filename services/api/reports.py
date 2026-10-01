from sqlalchemy import select

from services.api.models import CaseVersion, Feedback, RubricVersion
from services.api.serializers import report_json


def markdown_report(db, attempt):
    version = db.get(CaseVersion, attempt.case_version_id)
    rubric = db.get(RubricVersion, attempt.rubric_version_id)
    feedback = report_json(db, db.scalar(select(Feedback).where(Feedback.attempt_id == attempt.id)))
    lines = [
        "# OTCaseLab learning report",
        "",
        "Educational simulation using fictional content. Provisional coverage feedback requires educator review.",
        "",
        f"Case: {version.payload['title']} (v{version.version})",
        f"Attempt: {attempt.id}",
        f"Created (UTC): {attempt.created_at.isoformat()}Z",
        f"Case review: {version.review_status}",
        f"Rubric version: {rubric.id}",
        f"Language: {attempt.language}",
        "",
    ]
    for field, value in attempt.draft.items():
        if field != "evidence_ids":
            lines.extend([f"## {field.capitalize()}", "", str(value), ""])
    if feedback:
        lines.extend(
            [
                "## Formative feedback",
                "",
                f"Mode: {feedback['mode']}",
                f"Review: {feedback['review_status']}",
                f"Baseline coverage: {feedback['total']}/{feedback['max_total']}",
                "",
            ]
        )
        for item in feedback["items"]:
            lines.extend(
                [
                    f"### {item['label']}",
                    "",
                    f"Provisional score: {item['score']}/{item['max_score']}",
                    f"Original rubric: {item['rubric_anchor']}",
                    "",
                    item["explanation"],
                    "",
                    "Uncertainty: " + item["uncertainty"],
                    "",
                ]
            )
            for span in item["student_evidence"]:
                lines.extend(
                    [
                        f"Learner support ({span['field']} [{span['start']}:{span['end']}]):",
                        "",
                        span["text"],
                        "",
                    ]
                )
            ref = item.get("reference_passage")
            if ref:
                lines.extend(
                    [f"Reference passage: {ref['id']} — {ref['title']}", "", ref["text"], ""]
                )
                if ref.get("url"):
                    lines.append(f"Source: {ref['url']}")
        for review in feedback.get("reviews", []):
            lines.extend(
                [
                    "## Educator amendment",
                    "",
                    f"{review['educator_name']} — {review['created_at']}",
                    review["comment"],
                    f"Educator scores (separate from original): {review['scores']}",
                    "",
                ]
            )
        recommendation = feedback.get("recommendation")
        if recommendation:
            lines.extend(
                [
                    "## Next practice",
                    "",
                    recommendation.get("title", ""),
                    recommendation.get("reason", ""),
                    f"Mode: {recommendation.get('mode')}",
                    "",
                ]
            )
        lines.extend(
            [
                "## Execution provenance",
                "",
                f"Feedback version: {feedback.get('version', 'unspecified')}",
                f"Feedback record: {feedback['id']}",
                "",
            ]
        )
        for event in feedback.get("trace", []):
            lines.append(f"- {event}")
    else:
        lines.append("Feedback has not completed.")
    return "\n".join(lines)
