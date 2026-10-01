import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from services.api.main import app  # noqa: E402

path = ROOT / "packages/contracts/openapi.json"
path.write_text(json.dumps(app.openapi(), indent=2) + "\n")
print(path)
