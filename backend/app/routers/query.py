"""Natural-language query and case brief. F10.

The LLM turns a question into filters. **This module runs the query**, against
the caller's own agency scope, and the LLM never sees a connection string. An
investigator asking a question therefore cannot be handed data their role does
not entitle them to, however the question is phrased.
"""

from collections import Counter
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app import llm
from app.audit import audited
from app.database import get_db
from app.graph import build_graph, can_see_entity, entity_scope, relationship_scope
from app.models import Agency, Entity, Relationship, User
from app.schemas import (
    BriefRequest,
    BriefResponse,
    NLQueryFilters,
    NLQueryRequest,
    NLQueryResponse,
)

router = APIRouter(prefix="/api/query", tags=["query"])

RESULT_CAP = 200


def _run_filters(db: Session, user: User, filters: dict) -> list[Entity]:
    """Execute validated filters. Agency scoping is applied first and always.

    entity_scope and relationship_scope return None for an admin, meaning "no
    restriction" - so the predicate is only attached when there is one.
    `.where(None)` matches nothing in SQLAlchemy 2.x, which silently gave an
    admin an empty result set the first time this was written.
    """
    stmt = select(Entity)
    scope = entity_scope(user)
    if scope is not None:
        stmt = stmt.where(scope)

    if filters.get("entity_types"):
        stmt = stmt.where(Entity.entity_type.in_(filters["entity_types"]))

    if filters.get("name_contains"):
        stmt = stmt.where(Entity.name.ilike(f"%{filters['name_contains']}%"))

    if filters.get("agency_codes"):
        stmt = stmt.where(Entity.agency_id.in_(
            select(Agency.id).where(Agency.code.in_(filters["agency_codes"]))))

    # A relationship or date filter is a question about edges, so it narrows to
    # entities that actually take part in a matching one. Dates use the same
    # overlap test as the graph - an open-ended link that began earlier is still
    # true inside a later window.
    rel_types = filters.get("rel_types")
    date_from = filters.get("date_from")
    date_to = filters.get("date_to")
    if rel_types or date_from or date_to:
        edges = select(Relationship)
        rel_scope = relationship_scope(user)
        if rel_scope is not None:
            edges = edges.where(rel_scope)
        if rel_types:
            edges = edges.where(Relationship.rel_type.in_(rel_types))
        if date_to:
            edges = edges.where(Relationship.valid_from <= date.fromisoformat(date_to))
        if date_from:
            edges = edges.where(or_(Relationship.valid_to.is_(None),
                                    Relationship.valid_to >= date.fromisoformat(date_from)))
        sub = edges.subquery()
        stmt = stmt.where(or_(
            Entity.id.in_(select(sub.c.src_entity_id)),
            Entity.id.in_(select(sub.c.dst_entity_id)),
        ))

    return list(db.scalars(stmt.order_by(Entity.id).limit(RESULT_CAP)))


@router.post("/nl", response_model=NLQueryResponse)
def natural_language(
    payload: NLQueryRequest,
    user: User = Depends(audited("nl_query", "query")),
    db: Session = Depends(get_db),
) -> NLQueryResponse:
    """Ask in plain English. The model only ever returns filters."""
    filters, interpretation, from_cache = llm.interpret(payload.question)
    # No filters means the question could not be narrowed down. Returning every
    # record in scope would look like an answer while being none - the honest
    # response is an empty result and a sentence saying why.
    matches = _run_filters(db, user, filters) if filters else []
    names = [e.name for e in matches]

    # A cached answer is kept for its phrasing, but the counts are always
    # recomputed here, so nothing on screen is a number from a recording.
    answer = llm.compose_answer(payload.question, filters, names, len(matches))
    if from_cache:
        phrasing = llm.cached_answer(payload.question)
        if phrasing:
            answer = f"{phrasing} {answer}"

    return NLQueryResponse(
        interpretation=interpretation,
        filters=NLQueryFilters(**filters),
        answer=answer,
        entity_ids=[e.id for e in matches],
        from_cache=from_cache,
    )


def _facts(db: Session, user: User, entity: Entity) -> str:
    """A readable summary of the entity's real network, for the model to polish.

    Assembled from the scoped graph, so a brief cannot mention a connection the
    reader is not entitled to see. Doubles as the offline brief.
    """
    graph = build_graph(db, user, center_id=entity.id, depth=2)
    if not graph.has_node(entity.id):
        return f"{entity.name} has no connections visible to you."

    direct = list(graph.neighbors(entity.id))
    kinds = Counter(graph.nodes[n].get("entity_type") for n in direct)
    rels = Counter(graph[entity.id][n].get("rel_type") for n in direct)

    starts = [graph[entity.id][n].get("valid_from") for n in direct]
    starts = sorted(d for d in starts if d)

    # Who matters structurally, measured on the two-hop neighbourhood rather
    # than the whole network, so the number reflects this entity's own context.
    import networkx as nx
    if graph.number_of_nodes() >= 3:
        central = sorted(nx.betweenness_centrality(graph).items(),
                         key=lambda kv: kv[1], reverse=True)
        notable = [graph.nodes[n].get("name") for n, score in central
                   if n != entity.id and score > 0][:3]
    else:
        notable = []

    lines = [
        f"{entity.name} is a {entity.entity_type} recorded by "
        f"{graph.nodes[entity.id].get('agency_code')}.",
        f"It has {len(direct)} direct connection{'s' if len(direct) != 1 else ''}: "
        + ", ".join(f"{n} {k}" for k, n in kinds.most_common()) + ".",
        "Those connections are "
        + ", ".join(f"{n} {r.replace('_', ' ')}" for r, n in rels.most_common()) + ".",
        f"The two-hop network around it holds {graph.number_of_nodes()} records "
        f"and {graph.number_of_edges()} links.",
    ]
    if starts:
        lines.append(f"Its connections run from {starts[0]} to {starts[-1]}.")
    if notable:
        lines.append("The most structurally significant records nearby are "
                     + ", ".join(notable) + ".")
    return " ".join(lines)


@router.post("/brief", response_model=BriefResponse)
def brief(
    payload: BriefRequest,
    user: User = Depends(audited("case_brief", "entity")),
    db: Session = Depends(get_db),
) -> BriefResponse:
    """A written summary of one entity's network."""
    if not can_see_entity(db, user, payload.entity_id):
        # Same 404 for "does not exist" and "exists in another agency", so a
        # brief request cannot be used to probe for records.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"no entity with id {payload.entity_id}",
        )
    entity = db.get(Entity, payload.entity_id)
    text, from_cache = llm.write_brief(entity.name, _facts(db, user, entity))
    return BriefResponse(entity_id=entity.id, brief=text, from_cache=from_cache)
