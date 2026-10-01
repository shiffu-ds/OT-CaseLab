"""Train a real sklearn model using strictly grouped, explicitly synthetic fixtures.

The output JSON is a portable numeric artifact; no untrusted pickle is loaded.
Replace synthetic fixtures only with consented expert-labelled longitudinal rows.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
from sklearn.dummy import DummyClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, log_loss
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

FEATURES = [
    "previous_profile",
    "previous_environment",
    "previous_goals",
    "previous_rationale",
    "previous_attempt_count",
]
TARGETS = ["profile", "environment", "goals", "rationale"]


def fixtures(seed: int = 71) -> list[dict]:
    rng = np.random.default_rng(seed)
    rows = []
    # Twelve independent case groups; each learner belongs to exactly one group.
    for case_group in range(12):
        for learner in range(12):
            learner_id = f"synthetic-learner-{case_group}-{learner}"
            for attempt in range(3):
                scores = rng.integers(0, 4, 4).astype(float)
                target = int(np.argmin(scores + rng.normal(0, 0.4, 4)))
                rows.append(
                    {
                        "id": f"{learner_id}-row-{attempt}",
                        "learner_id": learner_id,
                        "case_id": f"synthetic-case-{case_group}",
                        "split_group": str(case_group),
                        "available_before_target": True,
                        "synthetic": True,
                        "label_source": "fixture_generator_not_educator",
                        "features": dict(zip(FEATURES, [*scores, attempt + 1], strict=True)),
                        "target": TARGETS[target],
                    }
                )
    return rows


def validate(rows: list[dict]):
    ids = [r["id"] for r in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate row IDs")
    for row in rows:
        if row.get("available_before_target") is not True:
            raise ValueError("Recommendation-time feature provenance is missing")
        if row["target"] not in TARGETS or set(row["features"]) != set(FEATURES):
            raise ValueError("Invalid longitudinal schema")
        if not row.get("learner_id") or not row.get("case_id") or not row.get("split_group"):
            raise ValueError("Missing grouped split identifiers")
        if row.get("synthetic") is not True and row.get("label_source") != "independent_educator":
            raise ValueError("Non-synthetic target requires independent educator label provenance")


def train(rows: list[dict], output: Path, seed: int = 71):
    validate(rows)
    x = np.array([[r["features"][f] for f in FEATURES] for r in rows], dtype=float)
    y = np.array([r["target"] for r in rows])
    splitter = GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=seed)
    train_idx, test_idx = next(splitter.split(x, y, [r["split_group"] for r in rows]))
    for key in ("learner_id", "case_id"):
        overlap = {rows[i][key] for i in train_idx} & {rows[i][key] for i in test_idx}
        if overlap:
            raise ValueError(
                f"{key} leakage detected: split_group must join connected learner/case identities"
            )
    model = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            (
                "classifier",
                LogisticRegression(max_iter=500, class_weight="balanced", random_state=seed),
            ),
        ]
    )
    baseline = DummyClassifier(strategy="prior")
    model.fit(x[train_idx], y[train_idx])
    baseline.fit(x[train_idx], y[train_idx])
    prediction = model.predict(x[test_idx])
    dummy = baseline.predict(x[test_idx])
    rule = np.array(TARGETS)[np.argmin(x[test_idx, :4], axis=1)]
    classes = model.classes_.tolist()
    probability = model.predict_proba(x[test_idx])

    def metrics(predicted):
        return {
            "accuracy": float(accuracy_score(y[test_idx], predicted)),
            "macro_f1": float(f1_score(y[test_idx], predicted, average="macro", zero_division=0)),
        }

    serial = json.dumps(rows, sort_keys=True, separators=(",", ":"))
    data_hash = hashlib.sha256(serial.encode()).hexdigest()
    manifest = {
        "data_sha256": data_hash,
        "seed": seed,
        "train_ids": [rows[i]["id"] for i in train_idx],
        "test_ids": [rows[i]["id"] for i in test_idx],
        "learner_overlap": 0,
        "case_overlap": 0,
        "preprocessing_fit_on": "train_only",
    }
    classifier = model["classifier"]
    artifact = {
        "format": "numeric-logistic-v1",
        "features": FEATURES,
        "classes": classes,
        "imputer_medians": model["imputer"].statistics_.tolist(),
        "scaler_mean": model["scaler"].mean_.tolist(),
        "scaler_scale": model["scaler"].scale_.tolist(),
        "coefficients": classifier.coef_.tolist(),
        "intercepts": classifier.intercept_.tolist(),
        "status": "synthetic_mechanics_only"
        if any(r.get("synthetic") for r in rows)
        else "experimental_not_promoted",
        "data_sha256": data_hash,
    }
    report = {
        "executed_at": datetime.now(UTC).isoformat(),
        "status": artifact["status"],
        "real_learner_validation": False,
        "model": metrics(prediction),
        "model_log_loss": float(log_loss(y[test_idx], probability, labels=classes)),
        "majority_baseline": metrics(dummy),
        "transparent_rule_baseline": metrics(rule),
        "n_train": len(train_idx),
        "n_test": len(test_idx),
        "calibration": [
            {
                "probability_bin": [low, low + 0.2],
                "count": int(
                    ((probability.max(axis=1) >= low) & (probability.max(axis=1) < low + 0.2)).sum()
                ),
                "correct": int(
                    (
                        (probability.max(axis=1) >= low)
                        & (probability.max(axis=1) < low + 0.2)
                        & (prediction == y[test_idx])
                    ).sum()
                ),
            }
            for low in [0.2, 0.4, 0.6, 0.8]
        ],
        "limitations": "Synthetic targets encode the fixture's lowest prior score. Metrics test software mechanics only. Real expert labels, consent, educator review, and a separate holdout are required for promotion.",
    }
    output.mkdir(parents=True, exist_ok=True)
    for name, value in [
        ("model.json", artifact),
        ("split-manifest.json", manifest),
        ("evaluation.json", report),
    ]:
        (output / name).write_text(json.dumps(value, indent=2) + "\n")
    (output / "fixtures.jsonl").write_text("\n".join(json.dumps(row) for row in rows) + "\n")
    return report


def predict(artifact: dict, features: dict, allow_synthetic: bool = False) -> dict:
    if artifact.get("format") != "numeric-logistic-v1":
        raise ValueError("Unsupported numeric model artifact")
    if artifact.get("status") == "synthetic_mechanics_only" and not allow_synthetic:
        raise ValueError("Synthetic-trained models cannot provide learner recommendations")
    x = np.array([features.get(f, np.nan) for f in artifact["features"]], dtype=float)
    x = np.where(np.isnan(x), artifact["imputer_medians"], x)
    x = (x - np.array(artifact["scaler_mean"])) / np.array(artifact["scaler_scale"])
    logits = np.array(artifact["coefficients"]) @ x + np.array(artifact["intercepts"])
    logits -= logits.max()
    probs = np.exp(logits) / np.exp(logits).sum()
    return {
        "competency": artifact["classes"][int(probs.argmax())],
        "probabilities": dict(zip(artifact["classes"], probs.tolist(), strict=True)),
        "mode": artifact["status"],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--synthetic", action="store_true")
    parser.add_argument("--data", type=Path)
    parser.add_argument("--output", type=Path, default=Path("ml/reports/synthetic-recommender"))
    args = parser.parse_args()
    if args.synthetic == bool(args.data):
        parser.error("Choose either --synthetic or --data PATH")
    rows = (
        fixtures()
        if args.synthetic
        else [json.loads(line) for line in args.data.read_text().splitlines() if line.strip()]
    )
    print(json.dumps(train(rows, args.output), indent=2))


if __name__ == "__main__":
    main()
