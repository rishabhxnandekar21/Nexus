"""Audit log routes: read the chain, and verify it.

Admin only, per PRD Section 5 - the audit log is a supervisor's view, not an
investigator's. Both routes are themselves audited, so reading the log appends
to the log. That is deliberate: an access to the audit trail is an access.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import audited, verify_chain
from app.database import get_db
from app.models import AuditLog, User
from app.schemas import AuditEntryOut, VerifyResponse

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("", response_model=list[AuditEntryOut])
def recent_entries(
    limit: int = Query(default=100, ge=1, le=500),
    user: User = Depends(audited("read_audit_log", "audit_log", admin=True)),
    db: Session = Depends(get_db),
) -> list[AuditEntryOut]:
    """Newest rows first, so the page opens on what just happened.

    The username is joined in rather than resolved per row in the page - an
    outer join because user_id is nullable for a system-written row.
    """
    rows = db.execute(
        select(AuditLog, User.username)
        .join(User, User.id == AuditLog.user_id, isouter=True)
        .order_by(AuditLog.seq.desc())
        .limit(limit)
    ).all()

    return [
        AuditEntryOut(
            id=row.id,
            seq=row.seq,
            user_id=row.user_id,
            username=username,
            action=row.action,
            resource_type=row.resource_type,
            resource_id=row.resource_id,
            details=row.details,
            timestamp=row.timestamp,
            prev_hash=row.prev_hash,
            hash=row.hash,
        )
        for row, username in rows
    ]


@router.get("/verify", response_model=VerifyResponse)
def verify(
    user: User = Depends(audited("verify_audit_chain", "audit_log", admin=True)),
    db: Session = Depends(get_db),
) -> VerifyResponse:
    """Recompute every hash in seq order and report the first mismatch.

    The row logging this very call is committed by the dependency before the
    check runs, so it is included in `checked`. That is the honest answer - the
    chain being verified is the chain as it stands now.
    """
    return VerifyResponse(**verify_chain(db))
