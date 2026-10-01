"""Fill only placeholder secrets in a local env file, without printing values."""

import os
import secrets
import sys
from pathlib import Path

path = Path(sys.argv[1] if len(sys.argv) == 2 else ".env.production")
text = path.read_text()
for name in ("POSTGRES_PASSWORD", "APP_DB_PASSWORD", "MCP_SERVICE_SECRET", "MCP_HTTP_BEARER_TOKEN"):
    placeholder = f"{name}=GENERATE_LOCALLY"
    if placeholder in text:
        text = text.replace(placeholder, f"{name}={secrets.token_urlsafe(48)}")
path.write_text(text)
os.chmod(path, 0o600)
print("Local secret placeholders replaced; values were not printed.")
