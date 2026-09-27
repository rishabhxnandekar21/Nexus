"""SQLAlchemy tables. Six of them, exactly as specified in CLAUDE.md Section 5.

Shared file. Changes follow the schema-change protocol in TEAM-WORKFLOW.md
Section 6 - there are no migrations, so a change here silently breaks the other
member's database until they reseed.
"""

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

# Allowed values, kept here so seed.py and schemas.py can import them instead of
# repeating the literals.
ENTITY_TYPES = ("person", "vehicle", "location", "phone", "organization", "crime_event")
USER_ROLES = ("investigator", "admin")
RESOLUTION_STATUSES = ("pending", "confirmed", "rejected")


def _one_of(column: str, values: tuple[str, ...]) -> str:
    """CHECK clause body, built from the tuples above so the two cannot drift."""
    return f"{column} IN ({', '.join(chr(39) + v + chr(39) for v in values)})"


class Agency(Base):
    """A data source: GJ_POLICE, TELECOM, RTO."""

    __tablename__ = "agencies"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)


class User(Base):
    """An investigator or admin, attached to exactly one agency."""

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(_one_of("role", USER_ROLES), name="ck_users_role"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    agency_id: Mapped[int] = mapped_column(ForeignKey("agencies.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Entity(Base):
    """The one node table for every entity type.

    Type-specific fields live in `attributes` JSONB - age and alias for a person,
    plate and model for a vehicle, crime type and status for a crime event. There
    is deliberately no table per type.
    """

    __tablename__ = "entities"
    __table_args__ = (
        CheckConstraint(_one_of("entity_type", ENTITY_TYPES), name="ck_entities_entity_type"),
        Index("ix_entities_entity_type", "entity_type"),
        Index("ix_entities_agency_id", "agency_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    attributes: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    agency_id: Mapped[int] = mapped_column(ForeignKey("agencies.id"), nullable=False)
    source_ref: Mapped[str | None] = mapped_column(String(100))
    is_shared: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Relationship(Base):
    """An edge. Always dated, always attributed to an agency.

    The entity foreign keys deliberately do NOT cascade on delete. Confirming a
    resolution candidate rewires B's relationships onto A and then removes B, so
    by the time B is deleted it should own no edges. Without cascade, a bug in
    that rewiring raises a foreign-key error instead of quietly destroying edges.
    """

    __tablename__ = "relationships"
    __table_args__ = (
        Index("ix_relationships_src_entity_id", "src_entity_id"),
        Index("ix_relationships_dst_entity_id", "dst_entity_id"),
        Index("ix_relationships_valid_from", "valid_from"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    src_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id"), nullable=False)
    dst_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id"), nullable=False)
    rel_type: Mapped[str] = mapped_column(String(30), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[date | None] = mapped_column(Date)
    source_case: Mapped[str | None] = mapped_column(Text)
    agency_id: Mapped[int] = mapped_column(ForeignKey("agencies.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ResolutionCandidate(Base):
    """A proposed "these two records are the same thing" pair.

    Nothing ever auto-merges. A human confirms or rejects, which is a deliberate
    design point. The unique constraint on the pair is what makes "a rejected
    pair is never re-proposed" structural rather than a code convention.
    """

    __tablename__ = "resolution_candidates"
    __table_args__ = (
        CheckConstraint(_one_of("status", RESOLUTION_STATUSES), name="ck_resolution_status"),
        UniqueConstraint("entity_a_id", "entity_b_id", name="uq_resolution_pair"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_a_id: Mapped[int] = mapped_column(ForeignKey("entities.id"), nullable=False)
    entity_b_id: Mapped[int] = mapped_column(ForeignKey("entities.id"), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    features: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuditLog(Base):
    """Append-only, SHA-256 hash-chained. Never updated, never deleted.

    Singular table name, against the plural convention in CLAUDE.md Section 8,
    because Section 5 names it `audit_log`.

    `timestamp` is a NAIVE UTC datetime set by audit.py in Python, with no server
    default, and this matters. The hash payload embeds `timestamp.isoformat()`,
    so verify_chain has to recompute a byte-identical string. A server default
    would mean the value used in the hash was never the value Postgres stored,
    and a timestamptz can come back rendered in a different session timezone on
    the other machine - either one silently breaks the whole chain, on the one
    feature whose failure is invisible on screen.
    """

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    seq: Mapped[int] = mapped_column(unique=True, nullable=False)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_type: Mapped[str | None] = mapped_column(String(50))
    resource_id: Mapped[str | None] = mapped_column(String(50))
    details: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    prev_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    hash: Mapped[str] = mapped_column(String(64), nullable=False)
