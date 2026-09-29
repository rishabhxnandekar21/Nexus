"""Landing-page counts. F11.

`CLAUDE.md` Section 6 does not define this endpoint - F11 is a PRD feature with
no API surface written for it, and composing these numbers client-side from the
capped search and graph routes would have produced wrong counts rather than
missing ones. So the route is added deliberately, scoped like everything else,
and Section 6 is updated to match.

Scoped on purpose: an investigator's landing page should report what they can
see. It makes S2 visible a third way - the numbers differ per login before any
graph is drawn.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit import audited, chain_length, verify_chain
from app.database import get_db
from app.graph import entity_scope, relationship_scope
from app.models import Agency, AuditLog, Entity, Relationship, ResolutionCandidate, User
from app.schemas import (
    AgencyCount,
    ChainStatus,
    StatsResponse,
    TypeCount,
    YearCount,
)

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("", response_model=StatsResponse)
def stats(
    user: User = Depends(audited("read_stats", "stats")),
    db: Session = Depends(get_db),
) -> StatsResponse:
    is_admin = user.role == "admin"
    e_scope = entity_scope(user)
    r_scope = relationship_scope(user)

    def scoped(stmt, predicate):
        # entity_scope and relationship_scope return None for an admin, meaning
        # no restriction. .where(None) matches nothing, so the predicate is only
        # attached when there is one.
        return stmt if predicate is None else stmt.where(predicate)

    by_type = [
        TypeCount(entity_type=row[0], count=row[1])
        for row in db.execute(
            scoped(select(Entity.entity_type, func.count()), e_scope)
            .group_by(Entity.entity_type)
            .order_by(func.count().desc())
        )
    ]

    by_agency = [
        AgencyCount(agency_code=row[0], count=row[1])
        for row in db.execute(
            scoped(
                select(Agency.code, func.count()).join(
                    Relationship, Relationship.agency_id == Agency.id),
                r_scope,
            )
            .group_by(Agency.code)
            .order_by(Agency.code)
        )
    ]

    by_year = [
        YearCount(year=int(row[0]), count=row[1])
        for row in db.execute(
            scoped(
                select(func.extract("year", Relationship.valid_from), func.count()),
                r_scope,
            )
            .group_by(func.extract("year", Relationship.valid_from))
            .order_by(func.extract("year", Relationship.valid_from))
        )
    ]

    entities = db.scalar(scoped(select(func.count()).select_from(Entity), e_scope))
    relationships = db.scalar(
        scoped(select(func.count()).select_from(Relationship), r_scope))

    # The resolution queue is an admin view, so its depth is only reported to one.
    pending = 0
    if is_admin:
        pending = db.scalar(
            select(func.count()).select_from(ResolutionCandidate)
            .where(ResolutionCandidate.status == "pending"))

    chain = ChainStatus(rows=chain_length(db), admin_only=not is_admin)
    if is_admin:
        result = verify_chain(db)
        chain = ChainStatus(
            rows=db.scalar(select(func.count()).select_from(AuditLog)),
            valid=result["valid"],
            broken_at_seq=result["broken_at_seq"],
            checked=result["checked"],
            admin_only=False,
        )

    return StatsResponse(
        scope="all agencies" if is_admin else db.get(Agency, user.agency_id).code,
        entities=entities,
        relationships=relationships,
        agencies=db.scalar(select(func.count()).select_from(Agency)),
        users=db.scalar(select(func.count()).select_from(User)),
        by_entity_type=by_type,
        relationships_by_agency=by_agency,
        relationships_by_year=by_year,
        resolution_pending=pending,
        chain=chain,
    )
