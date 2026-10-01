import copy
import hashlib
import json
import re
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import select

from services.api.config import ROOT
from services.api.models import Asset, CaseVersion, ReferencePassage, RubricVersion

DIMENSIONS = {"interviewing", "goals", "environment", "rationale"}


def validate_case(payload, case_id=None):
    p = copy.deepcopy(payload)
    if not isinstance(p, dict) or not re.fullmatch(r"[a-z0-9-]{1,80}", str(p.get("id", ""))):
        raise HTTPException(422, "Case id must contain lowercase letters, numbers or hyphens")
    if case_id and p["id"] != case_id:
        raise HTTPException(422, "Case id cannot change between versions")
    if len(json.dumps(p, ensure_ascii=False)) > 100000:
        raise HTTPException(422, "Case is too large")
    for field in ("title", "summary", "domain", "difficulty", "focus"):
        if not isinstance(p.get(field), str) or not p[field].strip():
            raise HTTPException(422, f"Missing case {field}")
    if p["focus"] not in DIMENSIONS:
        raise HTTPException(422, "Invalid learning focus")
    if not isinstance(p.get("patient"), dict) or not all(
        key in p["patient"] for key in ("name", "age", "occupation")
    ):
        raise HTTPException(422, "Missing fictional patient details")
    for field in ("introduction", "unknown_response"):
        if not isinstance(p.get(field), dict) or not all(
            isinstance(p[field].get(lang), str) and p[field][lang].strip()
            for lang in ("en", "ur", "roman")
        ):
            raise HTTPException(422, f"{field} requires English, Urdu and Roman Urdu text")
    facts = p.get("facts")
    if not isinstance(facts, list) or not 1 <= len(facts) <= 50:
        raise HTTPException(422, "Provide 1 to 50 case facts")
    ids = set()
    for fact in facts:
        if not isinstance(fact, dict) or not isinstance(fact.get("id"), str) or fact["id"] in ids:
            raise HTTPException(422, "Fact identifiers must be unique")
        ids.add(fact["id"])
        if fact.get("disclosure") not in ("on_question", "visible"):
            raise HTTPException(422, "Fact disclosure must be on_question or visible")
        if not all(
            isinstance(fact.get("text", {}).get(lang), str)
            and isinstance(fact.get("keywords", {}).get(lang), list)
            for lang in ("en", "ur", "roman")
        ):
            raise HTTPException(422, "Facts require localized text and keyword lists")
    rubric = p.get("rubric", [])
    if {r.get("dimension") for r in rubric} != DIMENSIONS or len(rubric) != 4:
        raise HTTPException(422, "Provide all four original rubric dimensions")
    if any(not r.get("anchor") or not r.get("label") or r.get("max_score") != 3 for r in rubric):
        raise HTTPException(422, "Each rubric requires a label, anchor and max_score of 3")
    if p.get("asset", {}).get("id") not in ("room-home", "room-work"):
        raise HTTPException(422, "Select an existing educational asset")
    for ref in p.get("evidence", []):
        if not all(
            isinstance(ref.get(f), str) and ref[f].strip()
            for f in ("id", "title", "text", "origin")
        ):
            raise HTTPException(422, "Evidence requires identifiers, original text and provenance")
        if ref.get("url") and not re.match(r"^https://", ref["url"]):
            raise HTTPException(422, "Reference URL must use HTTPS")
    p["review_status"] = "pending_review"
    p["eligible_demo"] = False
    return p


def create_version(db, case, payload, number, demo=False):
    payload = copy.deepcopy(payload)
    payload["version"] = number
    payload["review_status"] = "pending_review"
    payload["eligible_demo"] = demo
    for ref in payload.get("evidence", []):
        ref["approved"] = False
    version = CaseVersion(case_id=case.id, version=number, payload=payload, eligible_demo=demo)
    db.add(version)
    db.flush()
    rubric = RubricVersion(case_version_id=version.id, dimensions=payload["rubric"])
    db.add(rubric)
    for ref in payload.get("evidence", []):
        db.add(
            ReferencePassage(
                case_version_id=version.id,
                passage_id=ref["id"],
                title=ref["title"],
                text=ref["text"],
                source_url=ref.get("url"),
                origin=ref["origin"],
                approved=False,
            )
        )
    return version


def grading_case(db, version):
    # Construct trusted service context without changing the version's original payload.
    result = copy.deepcopy(version.payload)
    result["review_status"] = version.review_status
    passages = db.scalars(
        select(ReferencePassage).where(ReferencePassage.case_version_id == version.id)
    ).all()
    result["evidence"] = [
        {
            "id": r.passage_id,
            "title": r.title,
            "text": r.text,
            "url": r.source_url,
            "origin": r.origin,
            "approved": r.approved,
        }
        for r in passages
    ]
    return result


def asset_path(asset: Asset):
    base = ROOT / "data" / "demo" / "assets"
    path = (base / asset.storage_key).resolve()
    if not path.is_relative_to(base.resolve()) or not path.is_file():
        raise HTTPException(404, "Educational asset not found")
    if hashlib.sha256(path.read_bytes()).hexdigest() != asset.checksum:
        raise HTTPException(409, "Educational asset changed; re-register before use")
    return Path(path)
