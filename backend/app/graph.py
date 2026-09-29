"""The NetworkX graph, built from Postgres, scoped to the caller.

Krish owns this file. `build_graph()` is the one contract between the graph
core and everything built on top of it - PRD Section 11. Rishabh's
`analysis.py` calls it and never edits it, which is what keeps what-if and
link prediction from colliding with the graph itself.

The graph is rebuilt per request and held in memory. At the scale in PRD
Section 9 - about 1,500 entities and 3,000 relationships - that is a couple of
queries and a few milliseconds, and it removes every cache-invalidation
question that a persistent graph would introduce.
"""

from collections.abc import Sequence
from datetime import date

import networkx as nx
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import Agency, Entity, Relationship, User

# PRD Section 12: cap the returned nodes so Cytoscape stays responsive.
NODE_CAP = 500


def _is_admin(user: User) -> bool:
    return user.role == "admin"


def entity_scope(user: User):
    """SQL predicate for "this user may see this entity", or None for an admin.

    Exported so `routers/entities.py` filters on exactly the same rule the
    graph does. Two definitions of visibility is how a scoping demo quietly
    stops being true on one screen but not another.
    """
    if _is_admin(user):
        return None
    return or_(Entity.agency_id == user.agency_id, Entity.is_shared.is_(True))


def relationship_scope(user: User):
    """SQL predicate for relationship visibility, or None for an admin.

    Agency only - see the note in build_graph on why the edge is the sensitive
    part and there is no `is_shared` on relationships.
    """
    if _is_admin(user):
        return None
    return Relationship.agency_id == user.agency_id


def build_graph(
    db: Session,
    user: User,
    center_id: int | None = None,
    depth: int = 2,
    date_from: date | None = None,
    date_to: date | None = None,
    types: Sequence[str] | None = None,
) -> nx.Graph:
    """An undirected NetworkX graph of everything this user is allowed to see.

    Scoping, which is the whole of demo criterion S2:
      * an admin sees every entity and every relationship
      * an investigator sees entities where `agency_id` is theirs or
        `is_shared` is true, and relationships belonging to their own agency

    Relationships are scoped by agency alone because the `relationships` table
    has no `is_shared` column - and that is the right model rather than an
    omission. The edge is the sensitive part: that a phone exists may be
    shareable, while who called whom is a telecom record a police investigator
    has no claim on. A consequence worth knowing before the demo: a shared
    entity can appear with no edges for an investigator. That is correct, not a
    bug - they are entitled to know the node exists and not to know its links.

    Date filtering is an overlap test, not a `valid_from` window. A
    relationship that began before the range and has not ended is still true
    inside it; filtering on `valid_from` alone erases every open-ended family
    and ownership link from any later range.

    Graph-level attributes on the result: `truncated`, `center_id`, `depth`.
    """
    entities = _visible_entities(db, user, types)
    if not entities:
        graph = nx.Graph()
        graph.graph.update(truncated=False, center_id=center_id, depth=depth)
        return graph

    relationships = _visible_relationships(db, user, set(entities), date_from, date_to)

    graph = nx.Graph()
    for entity, agency_code in entities.values():
        graph.add_node(
            entity.id,
            name=entity.name,
            entity_type=entity.entity_type,
            agency_id=entity.agency_id,
            agency_code=agency_code,
            is_shared=entity.is_shared,
            source_ref=entity.source_ref,
            attributes=entity.attributes or {},
        )

    for rel, agency_code in relationships:
        # Parallel edges collapse onto one: an undirected simple graph is what
        # the centrality and community algorithms in F5 expect. `rel_ids` keeps
        # every underlying relationship so the side panel can list them all.
        if graph.has_edge(rel.src_entity_id, rel.dst_entity_id):
            graph[rel.src_entity_id][rel.dst_entity_id]["rel_ids"].append(rel.id)
            continue
        graph.add_edge(
            rel.src_entity_id,
            rel.dst_entity_id,
            id=rel.id,
            rel_ids=[rel.id],
            rel_type=rel.rel_type,
            confidence=rel.confidence,
            valid_from=rel.valid_from,
            valid_to=rel.valid_to,
            source_case=rel.source_case,
            agency_id=rel.agency_id,
            agency_code=agency_code,
        )

    if center_id is not None:
        graph = _around(graph, center_id, depth)

    truncated = graph.number_of_nodes() > NODE_CAP
    if truncated:
        graph = _cap(graph, center_id)

    graph.graph.update(truncated=truncated, center_id=center_id, depth=depth)
    return graph


def _visible_entities(
    db: Session, user: User, types: Sequence[str] | None
) -> dict[int, tuple[Entity, str]]:
    """Entity id -> (row, agency code), already scoped and type-filtered."""
    stmt = select(Entity, Agency.code).join(Agency, Agency.id == Entity.agency_id)
    scope = entity_scope(user)
    if scope is not None:
        stmt = stmt.where(scope)
    if types:
        stmt = stmt.where(Entity.entity_type.in_(list(types)))
    return {row.id: (row, code) for row, code in db.execute(stmt).all()}


def _visible_relationships(
    db: Session,
    user: User,
    visible_ids: set[int],
    date_from: date | None,
    date_to: date | None,
) -> list[tuple[Relationship, str]]:
    stmt = select(Relationship, Agency.code).join(
        Agency, Agency.id == Relationship.agency_id
    )
    scope = relationship_scope(user)
    if scope is not None:
        stmt = stmt.where(scope)

    # Overlap: the relationship was active at some point inside [from, to].
    if date_to is not None:
        stmt = stmt.where(Relationship.valid_from <= date_to)
    if date_from is not None:
        stmt = stmt.where(
            or_(Relationship.valid_to.is_(None), Relationship.valid_to >= date_from)
        )

    # An edge needs both endpoints visible, or it would draw into nothing.
    stmt = stmt.where(
        Relationship.src_entity_id.in_(visible_ids),
        Relationship.dst_entity_id.in_(visible_ids),
    )
    return list(db.execute(stmt).all())


def can_see_entity(db: Session, user: User, entity_id: int) -> bool:
    """Whether this user may know that this entity exists.

    Kept here so entity visibility has exactly one definition. Routes use it to
    return the same 404 for "does not exist" and "exists in another agency" -
    a different answer for the two would leak the existence of records the
    caller has no claim on.
    """
    stmt = select(Entity.id).where(Entity.id == entity_id)
    scope = entity_scope(user)
    if scope is not None:
        stmt = stmt.where(scope)
    return db.execute(stmt).scalar_one_or_none() is not None


def _around(graph: nx.Graph, center_id: int, depth: int) -> nx.Graph:
    """Everything within `depth` hops of the centre.

    A centre the caller cannot see, or that does not exist, yields an empty
    graph rather than an error: the route turns that into its own 404 when the
    entity is genuinely missing, and an investigator asking about an entity
    outside their agency should not be told whether it exists.
    """
    if center_id not in graph:
        return nx.Graph()
    reachable = nx.single_source_shortest_path_length(graph, center_id, cutoff=depth)
    return graph.subgraph(reachable).copy()


def _cap(graph: nx.Graph, center_id: int | None) -> nx.Graph:
    """Trim to NODE_CAP, keeping the centre and the best-connected nodes.

    Degree is the cheap proxy for "worth seeing" - dropping leaves loses less
    structure than dropping hubs. F5 will offer proper aggregation.
    """
    ranked = sorted(graph.degree, key=lambda pair: pair[1], reverse=True)
    keep = {node for node, _ in ranked[:NODE_CAP]}
    if center_id is not None and center_id in graph:
        keep.add(center_id)
    return graph.subgraph(keep).copy()


def to_cytoscape(graph: nx.Graph) -> dict:
    """NetworkX graph -> the element shape GraphResponse declares.

    Ids are strings. Cytoscape coerces them internally, and an edge whose
    `source` is 7 against a node id of "7" silently fails to render.
    """
    nodes = [
        {
            "data": {
                "id": str(node_id),
                "label": attrs["name"],
                "entity_type": attrs["entity_type"],
                "agency_code": attrs["agency_code"],
                "is_shared": attrs["is_shared"],
                "degree": graph.degree(node_id),
                "attributes": attrs["attributes"],
            }
        }
        for node_id, attrs in graph.nodes(data=True)
    ]
    edges = [
        {
            "data": {
                "id": f"e{attrs['id']}",
                "source": str(src),
                "target": str(dst),
                "label": attrs["rel_type"],
                "rel_type": attrs["rel_type"],
                "confidence": attrs["confidence"],
                "valid_from": attrs["valid_from"],
                "valid_to": attrs["valid_to"],
                "agency_code": attrs["agency_code"],
                "predicted": False,
            }
        }
        for src, dst, attrs in graph.edges(data=True)
    ]
    return {"nodes": nodes, "edges": edges}
