"""Execute actual downloaded pretrained NLP/CV; write measured, limited results."""

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from .cv import analyze_asset
from .nlp import extract_profile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--component", choices=["nlp", "cv", "all"], default="all")
    parser.add_argument("--output", default="ml/reports/neural-smoke.json")
    args = parser.parse_args()
    result = {
        "executed_at": datetime.now(UTC).isoformat(),
        "status": "pretrained_inference_smoke_only",
        "educational_validation": False,
    }
    if args.component in {"nlp", "all"}:
        result["nlp"] = {
            language: extract_profile(text, "neural")
            for language, text in {
                "en": "I want to dress myself. My family can help me.",
                "ur": "میں خود لباس پہننا چاہتی ہوں۔ خاندان مدد کر سکتا ہے۔",
                "roman": "Main khud kapray pehnna chahti hoon. Ghar walay madad kar saktay hain.",
            }.items()
        }
    if args.component in {"cv", "all"}:
        result["cv"] = analyze_asset(
            Path(__file__).resolve().parents[1] / "data/demo/assets/room-home.svg", "neural"
        )
        result["cv"]["input_license"] = "CC0-1.0 authored original schematic"
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(
        json.dumps(
            {
                "output": str(path),
                "components": [k for k in ("nlp", "cv") if k in result],
                "status": result["status"],
            }
        )
    )


if __name__ == "__main__":
    main()
