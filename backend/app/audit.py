"""Append-only, SHA-256 hash-chained audit log.

Shared file. This is the one piece whose failure is invisible on screen - a
broken chain looks exactly like a working one until someone verifies it - which
is why it is also the only thing in the project with a pytest.

The payload format is copied character for character from CLAUDE.md Section 5.
Do not reformat it, do not reorder the fields, do not "tidy" the separators:
verify_chain has to rebuild a byte-identical string years of rows later, and
any change here silently invalidates every row already written.
"""

import hashlib
import json
from datetime import datetime, timezone

from fastapi import Depends, Request
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_admin
from app.database import get_db
from app.models import AuditLog, User

GENESIS_PREV_HASH = "0" * 64

# Any 64-bit constant works; it only has to be the same in every process that
# writes a row. Chosen once and never changed.
_SEQ_LOCK_KEY = 8_615_294_301_776_113


def compute_hash(
    seq: int,
    user_id: int | None,
    action: str,
    resource_type: str | None,
    resource_id: str | None,
    timestamp: datetime,
    details: dict,
    prev_hash: str,
) -> str:
    """The chain hash for one row. CLAUDE.md Section 5, verbatim."""
    payload = (
        f"{seq}|{user_id}|{action}|{resource_type}|{resource_id}|"
        f"{timestamp.isoformat()}|{json.dumps(details, sort_keys=True)}|{prev_hash}"
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def write_audit(
    db: Session,
    user: User | None,
    action: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
    details: dict | None = None,
) -> AuditLog:
    """Append one row to the chain.

    Flushes but does not commit - the caller owns the transaction, which is what
    lets the test wrap a whole chain in one rollback.
    """
    details = details or {}

    # Two concurrent requests reading max(seq) at the same time would both write
    # the same seq: one hits the unique constraint, or worse the chain forks.
    # A transaction-scoped advisory lock serialises just this read-then-write.
    # It costs nothing at demo scale and the alternative failure is invisible.
    db.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": _SEQ_LOCK_KEY})

    last = db.execute(
        select(AuditLog).order_by(AuditLog.seq.desc()).limit(1)
    ).scalar_one_or_none()
    seq = 1 if last is None else last.seq + 1
    prev_hash = GENESIS_PREV_HASH if last is None else last.hash

    # Naive UTC, set here rather than by Postgres. models.py explains why: the
    # hash embeds timestamp.isoformat(), so the value in the hash has to be
    # exactly the value stored, and a timestamptz can come back rendered in a
    # different session timezone on the other machine.
    timestamp = datetime.now(timezone.utc).replace(tzinfo=None)

    row = AuditLog(
        seq=seq,
        user_id=user.id if user else None,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        timestamp=timestamp,
        prev_hash=prev_hash,
        hash=compute_hash(
            seq, user.id if user else None, action, resource_type,
            resource_id, timestamp, details, prev_hash,
        ),
    )
    db.add(row)
    db.flush()
    return row


def verify_chain(db: Session) -> dict:
    """Recompute every hash in seq order and report the first mismatch.

    Catches three things: a row whose contents were edited, a row whose stored
    hash was edited to match tampered contents, and a row deleted from the
    middle - the next row's prev_hash then points at a hash that is no longer
    its predecessor's.
    """
    rows = db.execute(select(AuditLog).order_by(AuditLog.seq)).scalars().all()

    expected_prev = GENESIS_PREV_HASH
    checked = 0
    for row in rows:
        checked += 1
        if row.prev_hash != expected_prev:
            return {"valid": False, "broken_at_seq": row.seq, "checked": checked}
        if compute_hash(
            row.seq, row.user_id, row.action, row.resource_type,
            row.resource_id, row.timestamp, row.details, row.prev_hash,
        ) != row.hash:
            return {"valid": False, "broken_at_seq": row.seq, "checked": checked}
        expected_prev = row.hash

    return {"valid": True, "broken_at_seq": None, "checked": checked}


def chain_length(db: Session) -> int:
    """Row count, for a stats page that should not pull the whole chain."""
    return db.execute(select(func.count()).select_from(AuditLog)).scalar_one()


def audited(action: str, resource_type: str | None = None, *, admin: bool = False):
    """Route dependency that resolves the caller and logs the access.

    Used in place of Depends(get_current_user), so a route physically cannot
    read graph data without writing a row - KICKOFF W1-5 and PRD F2. It commits
    the row itself: an access that then 500s is still an access, and the log is
    of attempts, not of successes.
    """
    resolve_user = require_admin if admin else get_current_user

    def dependency(
        request: Request,
        user: User = Depends(resolve_user),
        db: Session = Depends(get_db),
    ) -> User:
        params = dict(request.query_params)
        resource_id = next(
            (str(v) for k, v in request.path_params.items() if k.endswith("id")),
            None,
        )
        write_audit(
            db, user, action, resource_type, resource_id,
            {"path": request.url.path, "query": params},
        )
        db.commit()
        return user

    return dependency
