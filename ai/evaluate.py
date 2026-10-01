"""Authored regression fixtures; never describe these as educator gold labels."""

import argparse
import json
from pathlib import Path

from .baseline import extract_profile

EXAMPLES = [
    (
        "en",
        "I want dressing help.",
        [("want", "priority", False), ("dressing", "activity", False), ("help", "support", False)],
    ),
    (
        "en",
        "I have no pain. I want work.",
        [("pain", "symptom", True), ("want", "priority", False), ("work", "activity", False)],
    ),
    ("en", "Maybe the chair is useful.", [("chair", "environment", False)]),
    (
        "ur",
        "مجھے درد نہیں۔ لباس اہم ہے۔",
        [("درد", "symptom", True), ("لباس", "activity", False), ("اہم", "priority", False)],
    ),
    (
        "ur",
        "کرسی پر خاندان مدد کرتا ہے۔",
        [("کرسی", "environment", False), ("خاندان", "support", False), ("مدد", "support", False)],
    ),
    (
        "roman",
        "Mujhe dard nahi. Kapray zaroori hain.",
        [("dard", "symptom", True), ("Kapray", "activity", False), ("zaroori", "priority", False)],
    ),
    (
        "roman",
        "Shayad kursi par madad chahiye.",
        [("kursi", "environment", False), ("madad", "support", False)],
    ),
]


def evaluate():
    results = {}
    for language in ("en", "ur", "roman"):
        tp = fp = fn = 0
        for lang, text, gold in EXAMPLES:
            if lang != language:
                continue
            actual = {
                (e["text"], e["label"], e["negated"]) for e in extract_profile(text)["entities"]
            }
            expected = set(gold)
            tp += len(actual & expected)
            fp += len(actual - expected)
            fn += len(expected - actual)
        precision = tp / max(tp + fp, 1)
        recall = tp / max(tp + fn, 1)
        results[language] = {
            "precision": precision,
            "recall": recall,
            "f1": 2 * precision * recall / max(precision + recall, 1e-12),
            "tp": tp,
            "fp": fp,
            "fn": fn,
        }
    return {
        "status": "authored_regression_fixtures_only",
        "educator_reviewed": False,
        "examples": len(EXAMPLES),
        "languages": results,
        "limitations": "A tiny implementation-regression set is not a multilingual fairness benchmark or educational accuracy estimate.",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="ml/reports/nlp-baseline-regression.json")
    args = parser.parse_args()
    report = evaluate()
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
