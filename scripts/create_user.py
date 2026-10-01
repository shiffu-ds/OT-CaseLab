import argparse
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services.api.database import SessionLocal
from services.api.seed import seed_user

parser = argparse.ArgumentParser()
parser.add_argument("--email", required=True)
parser.add_argument("--name", required=True)
parser.add_argument("--role", choices=["student", "educator", "admin"], required=True)
parser.add_argument("--cohort", default="demo")
args = parser.parse_args()
password = getpass.getpass("Choose a password (at least 12 characters): ")
if len(password) < 12:
    raise SystemExit("Password must contain at least 12 characters")
with SessionLocal() as db:
    _, created = seed_user(db, args.email.casefold(), args.name, args.role, password, args.cohort)
print("Account created" if created else "Account already exists; credentials unchanged")
