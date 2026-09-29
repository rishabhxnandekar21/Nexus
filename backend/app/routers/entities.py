"""Entity search, detail and creation - F4.

Real as of W3. Every query is scoped through the predicates in graph.py, so a
search result and a graph node agree about what this user is allowed to see.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.audit import audited
from app.database import get_db
from app.graph import can_see_entity, entity_scope, relationship_scope
from app.models import Agency, Entity, Relationship, User
from app.schemas import (
    EntityCreate,
    EntityDetailOut,
    EntityOut,
    EntitySearchResult,
    RelationshipOut,
)

router = APIRouter(prefix="/api/entities", tags=["entities"])


def _search_result(entity: Entity, agency_code: str) -> EntitySearchResult:
    return EntitySearchResult(
        id=entity.id,
        entity_type=entity.entity_type,
        name=entity.name,
        agency_code=agency_code,
        is_shared=entity.is_shared,
    )


def _entity_out(entity: Entity, agency_code: str) -> EntityOut:
    return EntityOut(
        id=entity.id,
        entity_type=entity.entity_type,
        name=entity.name,
        attributes=entity.attributes or {},
        agency_id=entity.agency_id,
        agency_code=agency_code,
        source_ref=entity.source_ref,
        is_shared=entity.is_shared,
        created_at=entity.created_at,
    )


@router.get("", response_model=list[EntitySearchResult])
def search_entities(
    type: str | None = Query(default=None, description="filter by entity_type"),
    q: str | None = Query(default=None, description="case-insensitive partial name match"),
    limit: int = Query(default=50, ge=1, le=500),
    user: User = Depends(audited("search", "entity")),
    db: Session = Depends(get_db),
) -> list[EntitySearchResult]:
    """Agency-scoped search. F4: case-insensitive partial match on name."""
    stmt = select(Entity, Agency.code).join(Agency, Agency.id == Entity.agency_id)
    scope = entity_scope(user)
    if scope is not None:
        stmt = stmt.where(scope)
    if type:
        stmt = stmt.where(Entity.entity_type == type)
    if q:
        # ilike with escaped wildcards - a search for "100%" should look for
        # that text, not match everything.
        needle = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        stmt = stmt.where(Entity.name.ilike(f"%{needle}%", escape="\\"))
    stmt = stmt.order_by(Entity.name).limit(limit)
    return [_search_result(e, code) for e, code in db.execute(stmt).all()]


@router.get("/{entity_id}", response_model=EntityDetailOut)
def get_entity(
    entity_id: int,
    user: User = Depends(audited("read", "entity")),
    db: Session = Depends(get_db),
) -> EntityDetailOut:
    """The record, its visible relationships, and the neighbours they reach.

    404 rather than 403 for an entity in another agency, so the response does
    not confirm that a record the caller has no claim on exists.
    """
    if not can_see_entity(db, user, entity_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"no entity with id {entity_id}",
        )

    entity, agency_code = db.execute(
        select(Entity, Agency.code)
        .join(Agency, Agency.id == Entity.agency_id)
        .where(Entity.id == entity_id)
    ).one()

    rel_stmt = select(Relationship).where(
        or_(
            Relationship.src_entity_id == entity_id,
            Relationship.dst_entity_id == entity_id,
        )
    )
    rel_scope = relationship_scope(user)
    if rel_scope is not None:
        rel_stmt = rel_stmt.where(rel_scope)
    relationships = db.scalars(rel_stmt).all()

    # Only edges whose far end is also visible - otherwise the panel would name
    # an entity the caller is not allowed to know about.
    other_ids = {
        r.dst_entity_id if r.src_entity_id == entity_id else r.src_entity_id
        for r in relationships
    }
    neighbour_stmt = select(Entity, Agency.code).join(
        Agency, Agency.id == Entity.agency_id
    ).where(Entity.id.in_(other_ids or {0}))
    ent_scope = entity_scope(user)
    if ent_scope is not None:
        neighbour_stmt = neighbour_stmt.where(ent_scope)
    neighbours = {e.id: (e, code) for e, code in db.execute(neighbour_stmt).all()}

    names = {entity_id: entity.name} | {i: e.name for i, (e, _) in neighbours.items()}
    agency_codes = dict(db.execute(select(Agency.id, Agency.code)).all())

    visible_rels = [
        r
        for r in relationships
        if (r.dst_entity_id if r.src_entity_id == entity_id else r.src_entity_id)
        in neighbours
    ]

    return EntityDetailOut(
        entity=_entity_out(entity, agency_code),
        relationships=[
            RelationshipOut(
                id=r.id,
                src_entity_id=r.src_entity_id,
                src_name=names[r.src_entity_id],
                dst_entity_id=r.dst_entity_id,
                dst_name=names[r.dst_entity_id],
                rel_type=r.rel_type,
                confidence=r.confidence,
                valid_from=r.valid_from,
                valid_to=r.valid_to,
                source_case=r.source_case,
                agency_code=agency_codes[r.agency_id],
            )
            for r in visible_rels
        ],
        neighbours=[
            _search_result(e, code) for e, code in sorted(
                neighbours.values(), key=lambda pair: pair[0].name
            )
        ],
    )


@router.post("", response_model=EntityOut, status_code=status.HTTP_201_CREATED)
def create_entity(
    payload: EntityCreate,
    user: User = Depends(audited("create", "entity", admin=True)),
    db: Session = Depends(get_db),
) -> EntityOut:
    """Admin only. The agency is stamped from the caller's token, never taken
    from the body, so a caller cannot file a record against another agency."""
    agency = db.get(Agency, user.agency_id)
    if agency is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"user {user.id} references agency {user.agency_id}, which does not exist",
        )
    entity = Entity(
        entity_type=payload.entity_type.value,
        name=payload.name,
        attributes=payload.attributes,
        agency_id=user.agency_id,
        source_ref=payload.source_ref,
        is_shared=payload.is_shared,
    )
    db.add(entity)
    db.commit()
    db.refresh(entity)
    return _entity_out(entity, agency.code)
