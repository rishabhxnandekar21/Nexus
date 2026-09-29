"""Entity resolution routes: score, review, confirm, reject.

Admin only, per PRD Section 5 - the resolution queue is a supervisor's view.
Nothing here merges without an explicit confirm call from a person.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import resolution
from app.audit import audited
from app.database import get_db
from app.models import Agency, Entity, ResolutionCandidate, User
from app.schemas import (
    EntityOut,
    ResolutionActionResponse,
    ResolutionCandidateOut,
    ResolutionFeature,
    ResolutionRunResponse,
)

router = APIRouter(prefix="/api/resolution", tags=["resolution"])


def _entity_out(entity: Entity, codes: dict[int, str]) -> EntityOut:
    return EntityOut(
        id=entity.id,
        entity_type=entity.entity_type,
        name=entity.name,
        attributes=entity.attributes or {},
        agency_id=entity.agency_id,
        agency_code=codes.get(entity.agency_id, "?"),
        source_ref=entity.source_ref,
        is_shared=entity.is_shared,
        created_at=entity.created_at,
    )


def _candidate_out(row: ResolutionCandidate, db: Session,
                   codes: dict[int, str]) -> ResolutionCandidateOut:
    stored = row.features or {}
    return ResolutionCandidateOut(
        id=row.id,
        entity_a=_entity_out(db.get(Entity, row.entity_a_id), codes),
        entity_b=_entity_out(db.get(Entity, row.entity_b_id), codes),
        score=row.score,
        features=[ResolutionFeature(**f) for f in stored.get("signals", [])],
        reason=stored.get("reason", ""),
        status=row.status,
        reviewed_by=row.reviewed_by,
        reviewed_at=row.reviewed_at,
    )


def _load(db: Session, candidate_id: int) -> ResolutionCandidate:
    row = db.get(ResolutionCandidate, candidate_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"no resolution candidate with id {candidate_id}",
        )
    if row.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"candidate {candidate_id} was already {row.status}",
        )
    return row


@router.post("/run", response_model=ResolutionRunResponse)
def run(
    user: User = Depends(audited("resolution_run", "resolution_candidate", admin=True)),
    db: Session = Depends(get_db),
) -> ResolutionRunResponse:
    """Score plausible pairs and queue those above the threshold."""
    result = resolution.run_resolution(db)
    db.commit()
    return ResolutionRunResponse(**result)


@router.get("/candidates", response_model=list[ResolutionCandidateOut])
def candidates(
    status_filter: str = Query(default="pending", alias="status",
                               pattern="^(pending|confirmed|rejected|all)$"),
    user: User = Depends(audited("read_resolution_queue", "resolution_candidate", admin=True)),
    db: Session = Depends(get_db),
) -> list[ResolutionCandidateOut]:
    """The queue, highest score first - the most likely duplicate at the top."""
    stmt = select(ResolutionCandidate).order_by(ResolutionCandidate.score.desc())
    if status_filter != "all":
        stmt = stmt.where(ResolutionCandidate.status == status_filter)

    codes = dict(db.execute(select(Agency.id, Agency.code)).all())
    return [_candidate_out(row, db, codes) for row in db.scalars(stmt)]


@router.post("/{candidate_id}/confirm", response_model=ResolutionActionResponse)
def confirm(
    candidate_id: int,
    user: User = Depends(audited("resolution_confirm_request", "resolution_candidate", admin=True)),
    db: Session = Depends(get_db),
) -> ResolutionActionResponse:
    """Merge B into A. A human is doing this - nothing auto-merges."""
    candidate = _load(db, candidate_id)
    return ResolutionActionResponse(**resolution.confirm(db, user, candidate))


@router.post("/{candidate_id}/reject", response_model=ResolutionActionResponse)
def reject(
    candidate_id: int,
    user: User = Depends(audited("resolution_reject_request", "resolution_candidate", admin=True)),
    db: Session = Depends(get_db),
) -> ResolutionActionResponse:
    """Not the same person. The row stays so it is never proposed again."""
    candidate = _load(db, candidate_id)
    return ResolutionActionResponse(**resolution.reject(db, user, candidate))
