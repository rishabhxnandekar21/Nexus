"""The one test in the project.

Every other feature is verified by looking at it. This one cannot be: a
tampered chain renders exactly like an intact one, so a silent bug here would
destroy the whole tamper-evidence claim without anyone noticing. CLAUDE.md
Section 8 and KICKOFF W1-5.
"""

import hashlib
import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select, update

from app.audit import GENESIS_PREV_HASH, compute_hash, verify_chain, write_audit
from app.models import AuditLog


def _chain_of_five(db):
    for i in range(1, 6):
        write_audit(db, None, f"action_{i}", "entity", str(i), {"i": i})
    return db.execute(select(AuditLog).order_by(AuditLog.seq)).scalars().all()


def test_five_row_chain_verifies(db):
    rows = _chain_of_five(db)

    assert [r.seq for r in rows] == [1, 2, 3, 4, 5]
    assert rows[0].prev_hash == GENESIS_PREV_HASH
    assert len(GENESIS_PREV_HASH) == 64
    # Every row points at its predecessor.
    for previous, current in zip(rows, rows[1:]):
        assert current.prev_hash == previous.hash

    assert verify_chain(db) == {"valid": True, "broken_at_seq": None, "checked": 5}


def test_tampering_with_row_three_details_is_detected(db):
    _chain_of_five(db)

    # Edit the row directly, the way someone with database access would - the
    # ORM is bypassed so no hash is recomputed on the way in.
    db.execute(
        update(AuditLog).where(AuditLog.seq == 3).values(details={"i": 999})
    )
    db.expire_all()

    result = verify_chain(db)
    assert result["valid"] is False
    assert result["broken_at_seq"] == 3
    assert result["checked"] == 3


def test_recomputing_the_hash_after_tampering_is_still_detected(db):
    """The interesting case: an attacker who knows the hash rule.

    Editing a row and fixing its own hash is not enough - row 4 still carries
    the old hash as its prev_hash, so the break just moves one row later. To
    hide it they would have to rewrite every row to the end of the chain.
    """
    rows = _chain_of_five(db)
    target = rows[2]
    forged_details = {"i": 999}
    forged_hash = compute_hash(
        target.seq, target.user_id, target.action, target.resource_type,
        target.resource_id, target.timestamp, forged_details, target.prev_hash,
    )
    db.execute(
        update(AuditLog)
        .where(AuditLog.seq == 3)
        .values(details=forged_details, hash=forged_hash)
    )
    db.expire_all()

    result = verify_chain(db)
    assert result["valid"] is False
    assert result["broken_at_seq"] == 4


def test_deleting_a_row_from_the_middle_is_detected(db):
    _chain_of_five(db)
    db.execute(delete(AuditLog).where(AuditLog.seq == 3))
    db.expire_all()

    result = verify_chain(db)
    assert result["valid"] is False
    assert result["broken_at_seq"] == 4


def test_empty_chain_is_valid(db):
    assert verify_chain(db) == {"valid": True, "broken_at_seq": None, "checked": 0}


def test_payload_format_matches_the_specification(db):
    """Pins the hash rule to CLAUDE.md Section 5, independently of audit.py.

    If someone reorders a field or changes a separator, audit.py would still be
    self-consistent and every existing row would silently stop verifying. This
    rebuilds the string from the spec and fails if the two ever diverge.
    """
    timestamp = datetime(2026, 9, 29, 12, 0, 0)
    details = {"b": 2, "a": 1}
    expected_payload = (
        f"{7}|{3}|read|entity|42|{timestamp.isoformat()}|"
        f'{json.dumps(details, sort_keys=True)}|{GENESIS_PREV_HASH}'
    )
    expected = hashlib.sha256(expected_payload.encode()).hexdigest()

    assert compute_hash(
        7, 3, "read", "entity", "42", timestamp, details, GENESIS_PREV_HASH
    ) == expected


def test_timestamps_are_naive_utc(db):
    """models.py stores a naive datetime deliberately; a tz-aware one here
    would render differently on the other machine and break the chain."""
    row = write_audit(db, None, "read", "entity", "1", {})
    assert row.timestamp.tzinfo is None
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    assert abs(row.timestamp - now) < timedelta(seconds=30)
