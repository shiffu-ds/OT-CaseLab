"""Original, deterministic formative baseline with traceable learner spans.

Keyword coverage is a demonstration heuristic, not an assessment of OT competence.
Every feedback item requires educator review. Source drafts cannot enter retrieval.
"""

from __future__ import annotations

import re
from typing import Any

AI_VERSION = "original-lexical-0.1"
LANGUAGES = {
    "en": "en",
    "english": "en",
    "ur": "ur",
    "urdu": "ur",
    "roman": "roman",
    "roman_ur": "roman",
}

LEXICON = {
    "activity": [
        "dressing",
        "dress",
        "shirt",
        "button",
        "bathing",
        "bath",
        "toilet",
        "cooking",
        "cook",
        "walk",
        "work",
        "typing",
        "stairs",
        "لباس",
        "قمیص",
        "نہانا",
        "کھانا",
        "کام",
        "سیڑھی",
        "kapray",
        "kapre",
        "kameez",
        "nahana",
        "khana",
        "kaam",
        "chalna",
        "seerhi",
    ],
    "priority": [
        "priority",
        "important",
        "prefer",
        "want",
        "meaningful",
        "اہم",
        "چاہ",
        "ترجیح",
        "zaroori",
        "tarjeeh",
        "chahta",
        "chahti",
        "pasand",
    ],
    "support": [
        "help",
        "assist",
        "family",
        "wife",
        "husband",
        "daughter",
        "مدد",
        "خاندان",
        "بیوی",
        "بیٹی",
        "madad",
        "ghar wal",
        "beti",
        "biwi",
    ],
    "environment": [
        "chair",
        "rug",
        "floor",
        "step",
        "door",
        "desk",
        "light",
        "clutter",
        "rail",
        "seat",
        "کرسی",
        "قالین",
        "فرش",
        "درواز",
        "روشنی",
        "kursi",
        "qaleen",
        "farsh",
        "darwaz",
        "roshni",
    ],
    "symptom": [
        "pain",
        "fatigue",
        "weak",
        "tired",
        "درد",
        "تھکن",
        "کمزور",
        "dard",
        "thakan",
        "kamzor",
    ],
    "goal": [
        "goal",
        "within",
        "week",
        "independent",
        "achieve",
        "ہدف",
        "ہفت",
        "خود",
        "hadaf",
        "haft",
        "khud",
    ],
}
NEGATION = re.compile(
    r"\b(?:no|not|never|without|cannot|can't|nahi|nahin|naheen|baghair)\b|نہیں|نہيں|بغیر", re.I
)
UNCERTAINTY = re.compile(
    r"\b(?:maybe|perhaps|might|possibly|uncertain|shayad|shaayad)\b|شاید|ممکن", re.I
)
CLAUSE_BOUNDARIES = re.compile(r"[.!?;\n،۔؟]|\bbut\b|\blekin\b|لیکن", re.I)


def _terms(value: Any) -> list[str]:
    if isinstance(value, dict):
        return list(
            dict.fromkeys(
                t
                for ts in value.values()
                for t in (ts if isinstance(ts, list) else [ts])
                if isinstance(t, str)
            )
        )
    return list(value or []) if isinstance(value, list) else []


def _matches(text: str, term: str):
    # Latin full words avoid "work" matching "homework"; Urdu lexemes may be stems.
    expression = re.escape(term)
    if re.match(r"^[a-z]", term, re.I):
        expression = r"(?<!\w)" + expression + (r"(?!\w)" if not term.endswith(" ") else "")
    return re.finditer(expression, text, re.I)


def _context_flags(text: str, start: int, end: int) -> tuple[bool, bool]:
    left = 0
    right = len(text)
    for boundary in CLAUSE_BOUNDARIES.finditer(text):
        if boundary.end() <= start:
            left = boundary.end()
        elif boundary.start() >= end:
            right = boundary.start()
            break
    # A bounded clause prevents a negation in one sentence from affecting the next.
    clause = text[max(left, start - 70) : min(right, end + 45)]
    return bool(NEGATION.search(clause)), bool(UNCERTAINTY.search(clause))


def extract_profile(text: str) -> dict:
    if not isinstance(text, str) or len(text) > 30000:
        raise ValueError("Profile must be text of at most 30000 characters")
    entities = []
    for label, terms in LEXICON.items():
        seen = set()
        for term in terms:
            for match in _matches(text, term):
                if (match.start(), match.end()) in seen:
                    continue
                seen.add((match.start(), match.end()))
                negated, uncertain = _context_flags(text, *match.span())
                entities.append(
                    {
                        "label": label,
                        "text": match.group(),
                        "start": match.start(),
                        "end": match.end(),
                        "negated": negated,
                        "uncertain": uncertain,
                    }
                )
    return {
        "entities": sorted(entities, key=lambda e: (e["start"], e["end"], e["label"])),
        "mode": "lexical_baseline",
        "version": AI_VERSION,
        "limitations": "Unvalidated multilingual lexicon; spans identify mentions, not confirmed patient facts.",
    }


def permitted_facts(case: dict, question: str) -> list[dict]:
    return [
        f
        for f in case.get("facts", [])
        if f.get("disclosure") in {"on_question", "interview", "public", "visible"}
        and any(
            next(_matches(question, term), None)
            for term in _terms(f.get("keywords", f.get("triggers", [])))
        )
    ]


def _localized(value: Any, language: str) -> str:
    if isinstance(value, dict):
        return value.get(language) or value.get("en") or ""
    return str(value or "")


def patient_reply(case: dict, messages: list, text: str, language: str = "en") -> dict:
    language = LANGUAGES.get(language, "en")
    if len(text) > 4000:
        raise ValueError("Interview message exceeds 4000 characters")
    # Answer-key requests never expose the rubric or hidden facts to a provider.
    if re.search(
        r"rubric|answer.?key|system prompt|hidden facts|marking scheme|ignore.*instructions",
        text,
        re.I,
    ):
        facts = []
    else:
        facts = permitted_facts(case, text)[:2]
    from services.api.config import get_settings

    mode = get_settings().provider_mode
    if mode == "anthropic":
        from .providers import generated_patient_reply

        return generated_patient_reply(case, messages, text, language, facts)
    if mode != "scripted":
        raise ValueError("Unsupported PROVIDER_MODE; choose scripted or anthropic")
    reply = " ".join(_localized(f.get("text"), language) for f in facts)
    if not reply:
        reply = (
            _localized(case.get("unknown_response"), language)
            or {
                "en": "I do not have that information in this fictional case. Please ask about my everyday activities.",
                "ur": "اس فرضی کیس میں میرے پاس یہ معلومات نہیں ہیں۔ روزمرہ کاموں کے بارے میں پوچھیے۔",
                "roman": "Is farzi case mein mere paas yeh maloomat nahi. Rozmarra kaamon ke bare mein poochhein.",
            }[language]
        )
    return {
        "text": reply,
        "mode": "scripted",
        "disclosed_fact_ids": [f["id"] for f in facts],
        "provenance": {
            "provider": "authored_case_script",
            "case_version": case.get("version"),
            "prompt_version": "patient-v1",
            "fact_ids": [f["id"] for f in facts],
        },
    }


def search_evidence(case: dict, query: str, k: int = 3) -> dict:
    words = set(re.findall(r"\w+", query.casefold()))
    results = []
    for passage in case.get("evidence", []):
        if passage.get("approved") is not True:
            continue
        # Passage text is data only. No passage can cause a tool call.
        body = set(
            re.findall(r"\w+", (passage.get("title", "") + " " + passage["text"]).casefold())
        )
        score = len(words & body) / max(1, len(words))
        if score:
            results.append(
                {
                    **passage,
                    "score": round(score, 4),
                    "case_id": case.get("id"),
                    "retrieval_mode": "lexical_baseline",
                    "provenance": passage.get("origin", "educator-approved passage"),
                }
            )
    results.sort(key=lambda x: (-x["score"], x["id"]))
    return {
        "results": results[: max(0, min(k, 10))],
        "mode": "lexical_baseline",
        "approved_only": True,
        "status": "retrieved" if results else "no_approved_relevant_evidence",
    }


def _span_for(text: str, terms: list[str], field: str) -> tuple[list[dict], bool]:
    supports, negated_mentions = [], False
    for term in terms:
        for match in _matches(text, term):
            negated, uncertain = _context_flags(text, *match.span())
            if negated:
                negated_mentions = True
                continue
            # Store whole local sentence so the reason for coverage stays inspectable.
            left = (
                max(
                    text.rfind(".", 0, match.start()),
                    text.rfind("\n", 0, match.start()),
                    text.rfind("۔", 0, match.start()),
                )
                + 1
            )
            stops = [
                p for separator in (".", "\n", "۔") if (p := text.find(separator, match.end())) >= 0
            ]
            right = min(stops) + 1 if stops else len(text)
            while left < right and text[left].isspace():
                left += 1
            span = {
                "field": field,
                "start": left,
                "end": right,
                "text": text[left:right],
                "uncertain": uncertain,
            }
            if span not in supports:
                supports.append(span)
    return supports[:3], negated_mentions


def assess_submission(case: dict, submission: dict, student_messages: list | None = None) -> dict:
    items = []
    approved = {p["id"]: p for p in case.get("evidence", []) if p.get("approved") is True}
    fact_lookup = {f["id"]: f for f in case.get("facts", [])}
    visual = case.get("asset", {}).get("annotations", [])
    for criterion in case.get("rubric", []):
        dimension = criterion["dimension"]
        field = criterion.get("field") or {
            "occupational_profile": "profile",
            "functional_goals": "goals",
            "environmental_reasoning": "observations",
            "evidence_rationale": "rationale",
        }.get(dimension, "rationale")
        text = str(submission.get(field, ""))
        terms = _terms(criterion.get("keywords")) or LEXICON.get(
            {
                "profile": "activity",
                "observations": "environment",
                "goals": "goal",
                "rationale": "support",
            }.get(field, "activity"),
            [],
        )
        if dimension == "interviewing":
            spans, has_negated = [], False
            for message in student_messages or []:
                if message.get("role") not in {"student", "user"}:
                    continue
                message_text = message.get("text", message.get("content", ""))
                message_spans, negated = _span_for(message_text, terms, "messages")
                has_negated = has_negated or negated
                spans.extend(
                    {**span, "message_id": message.get("id")}
                    for span in message_spans
                    if message.get("id")
                )
            spans = spans[:3]
        else:
            spans, has_negated = _span_for(text, terms, field)
        maximum = criterion.get("max_score", 3)
        # Deliberately conservative coverage: at most 2/3 before educator review.
        score = min(2 if len(spans) > 1 else 1, maximum) if spans else 0
        uncertainties = [
            "Lexical mention coverage does not establish reasoning quality; educator review is required."
        ]
        if dimension == "interviewing":
            uncertainties.append(
                "Interview coverage uses only learner-authored transcript messages, never patient or generated text."
            )
        if has_negated:
            uncertainties.append("A negated mention was excluded from positive coverage.")
        if any(s["uncertain"] for s in spans):
            uncertainties.append(
                "Learner expressed uncertainty; verify before interpreting the statement."
            )
        ref_ids = criterion.get("reference_ids", [])
        selected = set(submission.get("evidence_ids") or [])
        passage = next((approved[r] for r in ref_ids if r in approved and r in selected), None)
        if passage is None:
            uncertainties.append("No selected educator-approved reference supports this item.")
        fact = next(
            (fact_lookup[f] for f in criterion.get("fact_ids", []) if f in fact_lookup), None
        )
        # Only disclose facts already elicited in this attempt. Backend supplies IDs.
        disclosed = set(submission.get("disclosed_fact_ids", []))
        fact = fact if fact and fact["id"] in disclosed else None
        observation = (
            next(
                (v for v in visual if v.get("review_status") in {"educator_confirmed", "approved"}),
                None,
            )
            if field == "observations"
            else None
        )
        if field == "observations" and observation is None:
            uncertainties.append(
                "Asset annotations are pending educator review; no confirmed visual observation was used."
            )
        if spans:
            explanation = "Your quoted text contains a relevant mention for this criterion. The coverage score is provisional; it does not judge whether the goal is appropriate, feasible, or justified. Compare it with the rubric anchor and discuss it with an educator."
        else:
            explanation = "The baseline did not find an affirmative relevant mention in this field. Review the criterion and make your reasoning explicit. This may be a language/lexicon miss and requires educator review."
        items.append(
            {
                "dimension": dimension,
                "label": criterion.get("label", dimension),
                "score": score,
                "max_score": maximum,
                "student_evidence": spans,
                "rubric_anchor": criterion.get("anchor", ""),
                "case_fact": {"id": fact["id"], "text": _localized(fact.get("text"), "en")}
                if fact
                else None,
                "visual_observation": observation,
                "reference_passage": {
                    key: passage.get(key) for key in ("id", "text", "title", "url")
                }
                if passage
                else None,
                "explanation": explanation,
                "uncertainty": " ".join(uncertainties),
                "review_status": "provisional",
            }
        )
    weak = (
        min(items, key=lambda x: (x["score"] / max(x["max_score"], 1), x["dimension"]))
        if items
        else None
    )
    return {
        "mode": "lexical_formative_baseline",
        "version": AI_VERSION,
        "review_status": "provisional",
        "items": items,
        "total": sum(x["score"] for x in items),
        "max_total": sum(x["max_score"] for x in items),
        "trace": [],
        "recommendation": {
            "mode": "transparent_rule",
            "dimension": weak["dimension"] if weak else "interviewing",
            "reason": "Practice the lowest provisional coverage criterion; ties use dimension order. This is not a validated learner model.",
        },
        "limitations": "Original unvalidated formative rubric coverage; synthetic examples do not validate learner grading.",
    }
