"""Temporary login fixture for W1-4.

Creates one agency and two users so login is testable before seed.py exists.
Idempotent - safe to run repeatedly.

DELETE THIS FILE when seed.py lands in W2. seed.py creates three agencies and
six users and is the single source of truth for demo data; this exists only so
the frontend shell in W1-8 has something to log in against.

    python dev_users.py

These passwords are committed deliberately. Every account in this project is
synthetic and local-only, and the demo needs known logins.
"""

from sqlalchemy import select

from app.auth import hash_password
from app.database import SessionLocal, init_db
from app.models import Agency, User

AGENCY = {"name": "Gujarat Police", "code": "GJ_POLICE"}
USERS = [
    {"username": "investigator", "password": "investigator123", "role": "investigator"},
    {"username": "admin", "password": "admin123", "role": "admin"},
]


def main() -> None:
    init_db()
    with SessionLocal() as db:
        agency = db.scalar(select(Agency).where(Agency.code == AGENCY["code"]))
        if agency is None:
            agency = Agency(**AGENCY)
            db.add(agency)
            db.flush()
            print(f"created agency {agency.code} (id={agency.id})")
        else:
            print(f"agency {agency.code} already exists (id={agency.id})")

        for spec in USERS:
            existing = db.scalar(select(User).where(User.username == spec["username"]))
            if existing is not None:
                print(f"user {spec['username']} already exists (id={existing.id})")
                continue
            user = User(
                username=spec["username"],
                password_hash=hash_password(spec["password"]),
                role=spec["role"],
                agency_id=agency.id,
            )
            db.add(user)
            db.flush()
            print(f"created {spec['role']} {user.username} (id={user.id})")

        db.commit()
    print("done")


if __name__ == "__main__":
    main()
