"""Test fixtures.

The db fixture runs every test inside one transaction that is always rolled
back, so the suite can be pointed at the ordinary development database without
leaving rows behind - including in audit_log, which is append-only in
production terms and must not accumulate test rows.
"""

import sys
from pathlib import Path

import pytest
from sqlalchemy import delete
from sqlalchemy.orm import Session

# backend/ on the path, so `import app...` works however pytest is invoked.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import engine  # noqa: E402
from app.models import AuditLog  # noqa: E402


@pytest.fixture
def db():
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    # Start from an empty chain so seq numbers and the genesis prev_hash are
    # deterministic. Rolled back with everything else, so the real log is
    # untouched.
    session.execute(delete(AuditLog))
    session.flush()

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()
