"""Engine, session factory, the get_db dependency, and table creation.

No Alembic. Schema changes go through create_all() plus a reseed, per the
protocol in TEAM-WORKFLOW.md Section 6.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """Declarative base for every table in models.py."""


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a session that always closes."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create every table that does not exist yet.

    Imports models for its side effect: the class definitions are what register
    the tables on Base.metadata. Imported here rather than at module level to
    keep models.py -> database.py the only import direction.
    """
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
