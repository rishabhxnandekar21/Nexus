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
from app.models import AuditLog, Entity, Relationship, ResolutionCandidate  # noqa: E402


@pytest.fixture
def db():
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    # Every test starts from an empty graph and an empty chain, so assertions
    # can be exact instead of "at least". Whatever dev_data.py happens to have
    # loaded is not the test's business, and a test that passes only because of
    # ambient rows is worse than no test. Children first, for the foreign keys.
    session.execute(delete(ResolutionCandidate))
    session.execute(delete(Relationship))
    session.execute(delete(Entity))
    session.execute(delete(AuditLog))
    session.flush()

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()
