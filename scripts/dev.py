"""Start both local processes and clean up only the processes created here."""

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
children = []
try:
    children.append(
        subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "services.api.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                "8000",
                "--reload",
            ],
            cwd=ROOT,
            start_new_session=True,
        )
    )
    children.append(
        subprocess.Popen(["npm", "run", "dev"], cwd=ROOT / "apps/web", start_new_session=True)
    )
    print("OTCaseLab local demo: http://localhost:" + os.getenv("PORT", "3005"), flush=True)
    while all(child.poll() is None for child in children):
        time.sleep(0.5)
except KeyboardInterrupt:
    pass
finally:
    for child in children:
        if child.poll() is None:
            os.killpg(child.pid, signal.SIGTERM)
    for child in children:
        try:
            child.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGKILL)
