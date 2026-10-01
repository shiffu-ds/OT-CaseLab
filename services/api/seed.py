"""Seed original fictional content; generate local credentials without a fixed password."""

import argparse
import hashlib
import json
import os
import secrets

from sqlalchemy import select

from services.api.config import ROOT, get_settings
from services.api.content import create_version, validate_case
from services.api.database import SessionLocal
from services.api.models import Asset, Case, Cohort, Membership, User
from services.api.security import hasher


def seed_content(db):
    if not db.get(Cohort, "demo"):
        db.add(Cohort(id="demo", name="Fictional learning studio"))
        db.flush()
    cases = json.loads((ROOT / "data/demo/cases.json").read_text())
    for payload in cases:
        validate_case(payload)
        asset = payload["asset"]
        if not db.get(Asset, asset["id"]):
            key = asset["id"] + ".svg"
            db.add(
                Asset(
                    id=asset["id"],
                    cohort_id="demo",
                    storage_key=key,
                    checksum=hashlib.sha256(
                        (ROOT / "data/demo/assets" / key).read_bytes()
                    ).hexdigest(),
                    license=asset["license"],
                    origin=asset["origin"],
                    annotations=asset.get("annotations", []),
                )
            )
        if not db.get(Case, payload["id"]):
            case = Case(id=payload["id"], cohort_id="demo")
            db.add(case)
            db.flush()
            create_version(db, case, payload, 1, demo=True)
    db.commit()


def seed_user(db, email, name, role="student", password=None, cohort_id="demo"):
    existing = db.scalar(select(User).where(User.email == email))
    if existing:
        return existing, None
    password = password or secrets.token_urlsafe(18)
    user = User(
        email=email, name=name, password_hash=hasher.hash(password), role=role, cohort_id=cohort_id
    )
    db.add(user)
    db.flush()
    db.add(Membership(user_id=user.id, cohort_id=cohort_id, role=role))
    db.commit()
    return user, password


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--content-only", action="store_true")
    parser.add_argument("--educator-email", default="educator@otcaselab.local")
    parser.add_argument("--educator-name", default="Demo educator")
    args = parser.parse_args()
    settings = get_settings()
    if settings.environment == "production" and not args.content_only:
        raise SystemExit(
            "Production: use scripts/create_user.py with explicit educator email and password prompt"
        )
    with SessionLocal() as db:
        seed_content(db)
        if not args.content_only:
            credentials = {}
            for email, name, role in [
                (args.educator_email, args.educator_name, "educator"),
                ("student@otcaselab.local", "Demo student", "student"),
                ("admin@otcaselab.local", "Demo administrator", "admin"),
            ]:
                _, password = seed_user(db, email, name, role)
                if password:
                    credentials[role] = {"email": email, "password": password}
            if credentials:
                path = ROOT / ".runtime" / "demo-credentials.json"
                existing = json.loads(path.read_text()) if path.exists() else {}
                existing.update(credentials)
                descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
                with os.fdopen(descriptor, "w") as handle:
                    json.dump(existing, handle, indent=2)
                print(f"Local credentials written to {path} (not tracked in Git)")
    print("Five fictional cases seeded; all remain pending educator review.")


if __name__ == "__main__":
    main()
