"""Record installed package licence metadata without treating missing terms as known."""

import importlib.metadata
import json
from pathlib import Path

packages = []
for distribution in importlib.metadata.distributions():
    metadata = distribution.metadata
    packages.append(
        {
            "name": metadata["Name"],
            "version": distribution.version,
            "license_expression": metadata.get("License-Expression"),
            "license_classifiers": [
                x for x in metadata.get_all("Classifier", []) if x.startswith("License ::")
            ],
            "status": "declared metadata; review upstream terms for release",
        }
    )
lock = json.loads(Path("apps/web/package-lock.json").read_text())
node = [
    {"path": name, "version": value.get("version"), "license": value.get("license", "unknown")}
    for name, value in lock["packages"].items()
    if name
]
report = {
    "verified_date": "2026-10-01",
    "python": sorted(packages, key=lambda p: p["name"].lower()),
    "npm_locked": node,
    "note": "Metadata inventory is not a legal clearance or model-weight licence. Lockfiles remain authoritative for dependency resolution.",
}
Path("docs/reports/dependency-licenses.json").write_text(json.dumps(report, indent=2) + "\n")
print(
    f"Recorded metadata for {len(packages)} installed Python distributions and {len(node)} locked npm packages."
)
