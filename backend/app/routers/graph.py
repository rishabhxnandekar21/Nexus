"""Graph, analytics, shortest path, what-if and link prediction.

W1-7 STUB. Everything is served from the twelve fake records in entities.py -
imported rather than copied so a graph node and a search result stay the same
thing while both are stubs. Both fake sets die in W2/W3 when graph.py builds a
real NetworkX graph from Postgres.

The centre/depth/date/type filters do real work on the fake set, so the
frontend can be built against behaviour rather than a constant. What is NOT
here is agency scoping: an investigator and an admin currently get identical
results. That is S2, the core demo moment, and it needs real rows - W2.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth import get_current_user
from app.models import User
from app.routers.entities import _BY_ID, _ENTITIES, _RELATIONSHIPS
from app.schemas import (
    AnalyticsResponse,
    BetweennessShift,
    ComponentStats,
    GraphEdge,
    GraphEdgeData,
    GraphNode,
    GraphNodeData,
    GraphResponse,
    NodeMetrics,
    PathResponse,
    PredictionOut,
    PredictionResponse,
    TopConnector,
    WhatIfRequest,
    WhatIfResponse,
)

router = APIRouter(prefix="/api/graph", tags=["graph"])

NODE_CAP = 500

# Hand-set centrality for the stub. Real values come from NetworkX in W2 - these
# are here so the UI has something to size and colour nodes by, not as a claim
# about the fake network.
_METRICS: dict[int, dict] = {
    1: {"betweenness": 0.42, "pagerank": 0.163, "community": 0},
    2: {"betweenness": 0.18, "pagerank": 0.101, "community": 0},
    3: {"betweenness": 0.31, "pagerank": 0.134, "community": 0},
    4: {"betweenness": 0.27, "pagerank": 0.089, "community": 1},
    5: {"betweenness": 0.09, "pagerank": 0.071, "community": 0},
    6: {"betweenness": 0.06, "pagerank": 0.062, "community": 0},
    7: {"betweenness": 0.11, "pagerank": 0.068, "community": 0},
    8: {"betweenness": 0.00, "pagerank": 0.041, "community": 1},
    9: {"betweenness": 0.08, "pagerank": 0.079, "community": 0},
    10: {"betweenness": 0.00, "pagerank": 0.038, "community": 0},
    11: {"betweenness": 0.14, "pagerank": 0.094, "community": 0},
    12: {"betweenness": 0.05, "pagerank": 0.060, "community": 1},
}


_DEFAULT_METRIC = {"betweenness": 0.0, "pagerank": 0.0, "community": 0}


def _metric(entity_id: int) -> dict:
    """Metrics for one node, tolerating a record with no hand-written row.

    _METRICS is maintained by hand alongside _ENTITIES; adding a record to one
    and not the other should not 500 the analytics endpoint.
    """
    return _METRICS.get(entity_id, _DEFAULT_METRIC)


def _degree(entity_id: int, edges: list[dict]) -> int:
    return sum(1 for r in edges if entity_id in (r["src"], r["dst"]))


def _neighbours(entity_id: int, edges: list[dict]) -> set[int]:
    out = set()
    for r in edges:
        if r["src"] == entity_id:
            out.add(r["dst"])
        elif r["dst"] == entity_id:
            out.add(r["src"])
    return out


def _select(
    center: int | None, depth: int, date_from: date | None,
    date_to: date | None, types: str | None,
) -> tuple[list[dict], list[dict]]:
    """Apply the same filters the real endpoint will, to the fake set."""
    edges = _RELATIONSHIPS
    # Overlap, not a valid_from window: an edge that began before the range and
    # never ended is still true inside it. Family and ownership links are
    # open-ended, so testing valid_from alone erases them from any later range.
    if date_to:
        edges = [r for r in edges if date.fromisoformat(r["valid_from"]) <= date_to]
    if date_from:
        edges = [
            r for r in edges
            if r["valid_to"] is None or date.fromisoformat(r["valid_to"]) >= date_from
        ]

    keep = {e["id"] for e in _ENTITIES}
    if types:
        wanted = {t.strip() for t in types.split(",") if t.strip()}
        keep = {e["id"] for e in _ENTITIES if e["entity_type"] in wanted}

    if center is not None:
        if center not in _BY_ID:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"no entity with id {center}",
            )
        reached = {center}
        frontier = {center}
        for _ in range(max(depth, 0)):
            nxt: set[int] = set()
            for node in frontier:
                nxt |= _neighbours(node, edges)
            frontier = nxt - reached
            reached |= nxt
        # The centre is added back after the intersection, not inside it - a
        # types filter must never drop the node the graph is centred on.
        keep = (keep & reached) | {center}

    nodes = [e for e in _ENTITIES if e["id"] in keep]
    edges = [r for r in edges if r["src"] in keep and r["dst"] in keep]
    return nodes, edges


@router.get("", response_model=GraphResponse)
def get_graph(
    center: int | None = Query(default=None),
    depth: int = Query(default=2, ge=1, le=3),
    date_from: date | None = Query(default=None, alias="from"),
    date_to: date | None = Query(default=None, alias="to"),
    types: str | None = Query(default=None, description="comma-separated entity types"),
    user: User = Depends(get_current_user),
) -> GraphResponse:
    """STUB. Cytoscape elements for the fake network. Ids are strings, per schemas.py."""
    nodes, edges = _select(center, depth, date_from, date_to, types)
    truncated = len(nodes) > NODE_CAP
    nodes = nodes[:NODE_CAP]
    kept = {n["id"] for n in nodes}
    edges = [r for r in edges if r["src"] in kept and r["dst"] in kept]

    return GraphResponse(
        nodes=[
            GraphNode(data=GraphNodeData(
                id=str(n["id"]), label=n["name"], entity_type=n["entity_type"],
                agency_code=n["agency_code"], is_shared=n["is_shared"],
                degree=_degree(n["id"], edges), attributes=n["attributes"],
            ))
            for n in nodes
        ],
        edges=[
            GraphEdge(data=GraphEdgeData(
                id=f"e{r['id']}", source=str(r["src"]), target=str(r["dst"]),
                label=r["rel_type"], rel_type=r["rel_type"], confidence=r["confidence"],
                valid_from=r["valid_from"], valid_to=r["valid_to"],
                agency_code=r["agency_code"],
            ))
            for r in edges
        ],
        center_id=center,
        depth=depth,
        truncated=truncated,
    )


@router.get("/analytics", response_model=AnalyticsResponse)
def get_analytics(
    center: int | None = Query(default=None),
    depth: int = Query(default=2, ge=1, le=3),
    user: User = Depends(get_current_user),
) -> AnalyticsResponse:
    """STUB. Per-node centrality and communities. Real NetworkX values in W4."""
    nodes, edges = _select(center, depth, None, None, None)
    metrics = [
        NodeMetrics(
            entity_id=n["id"], name=n["name"], degree=_degree(n["id"], edges),
            betweenness=_metric(n["id"])["betweenness"],
            pagerank=_metric(n["id"])["pagerank"],
            community=_metric(n["id"])["community"],
        )
        for n in nodes
    ]
    top = sorted(metrics, key=lambda m: m.betweenness, reverse=True)[:5]
    return AnalyticsResponse(
        metrics=metrics,
        top_connectors=[
            TopConnector(entity_id=m.entity_id, name=m.name, betweenness=m.betweenness)
            for m in top
        ],
        community_count=len({m.community for m in metrics}),
    )


@router.get("/path", response_model=PathResponse)
def get_path(
    from_id: int = Query(alias="from"),
    to_id: int = Query(alias="to"),
    user: User = Depends(get_current_user),
) -> PathResponse:
    """STUB. Breadth-first shortest path over the fake edges."""
    for node_id in (from_id, to_id):
        if node_id not in _BY_ID:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"no entity with id {node_id}",
            )

    previous: dict[int, int | None] = {from_id: None}
    queue = [from_id]
    while queue and to_id not in previous:
        current = queue.pop(0)
        for neighbour in sorted(_neighbours(current, _RELATIONSHIPS)):
            if neighbour not in previous:
                previous[neighbour] = current
                queue.append(neighbour)

    if to_id not in previous:
        return PathResponse(found=False)

    chain: list[int] = []
    cursor: int | None = to_id
    while cursor is not None:
        chain.append(cursor)
        cursor = previous[cursor]
    chain.reverse()

    hops = []
    for a, b in zip(chain, chain[1:]):
        edge = next(
            r for r in _RELATIONSHIPS
            if {r["src"], r["dst"]} == {a, b}
        )
        hops.append(edge["rel_type"])

    return PathResponse(
        found=True,
        entity_ids=chain,
        names=[_BY_ID[i]["name"] for i in chain],
        rel_types=hops,
        length=len(chain) - 1,
    )


@router.post("/whatif", response_model=WhatIfResponse)
def what_if(
    payload: WhatIfRequest,
    user: User = Depends(get_current_user),
) -> WhatIfResponse:
    """STUB. Network impact simulation - never crime prediction, per PRD N1.

    Component counts are computed for real on the fake set; the betweenness
    shift is illustrative until W5 wires NetworkX.
    """
    unknown = [i for i in payload.remove_entity_ids if i not in _BY_ID]
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"no entity with id {', '.join(str(i) for i in unknown)}",
        )
    removed = set(payload.remove_entity_ids)

    def components(node_ids: set[int], edges: list[dict]) -> list[set[int]]:
        seen: set[int] = set()
        out: list[set[int]] = []
        for start in sorted(node_ids):
            if start in seen:
                continue
            group = {start}
            stack = [start]
            while stack:
                for nb in _neighbours(stack.pop(), edges):
                    if nb in node_ids and nb not in group:
                        group.add(nb)
                        stack.append(nb)
            seen |= group
            out.append(group)
        return out

    all_ids = {e["id"] for e in _ENTITIES}
    kept_ids = all_ids - removed
    kept_edges = [
        r for r in _RELATIONSHIPS
        if r["src"] not in removed and r["dst"] not in removed
    ]

    before_groups = components(all_ids, _RELATIONSHIPS)
    after_groups = components(kept_ids, kept_edges)

    risers = sorted(
        (i for i in kept_ids),
        key=lambda i: _metric(i)["betweenness"],
        reverse=True,
    )[:5]

    return WhatIfResponse(
        removed_entity_ids=sorted(removed),
        before=ComponentStats(
            node_count=len(all_ids), edge_count=len(_RELATIONSHIPS),
            component_count=len(before_groups),
            largest_component_size=max(len(g) for g in before_groups),
        ),
        after=ComponentStats(
            node_count=len(kept_ids), edge_count=len(kept_edges),
            component_count=len(after_groups),
            largest_component_size=max((len(g) for g in after_groups), default=0),
        ),
        top_risers=[
            BetweennessShift(
                entity_id=i, name=_BY_ID[i]["name"],
                before=_metric(i)["betweenness"],
                after=round(_metric(i)["betweenness"] * 1.35, 3),
                delta=round(_metric(i)["betweenness"] * 0.35, 3),
            )
            for i in risers
        ],
    )


@router.get("/predict", response_model=PredictionResponse)
def predict_links(
    entity_id: int = Query(),
    k: int = Query(default=5, ge=1, le=20),
    user: User = Depends(get_current_user),
) -> PredictionResponse:
    """STUB. Likely-but-absent links, ranked by shared neighbours.

    Jaccard is computed for real on the fake set. Adamic-Adar is approximated
    here and comes from NetworkX in W5.
    """
    if entity_id not in _BY_ID:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"no entity with id {entity_id}",
        )

    mine = _neighbours(entity_id, _RELATIONSHIPS)
    out: list[PredictionOut] = []
    for other in _BY_ID:
        if other == entity_id or other in mine:
            continue
        theirs = _neighbours(other, _RELATIONSHIPS)
        shared = sorted(mine & theirs)
        if not shared:
            continue
        union = len(mine | theirs) or 1
        out.append(PredictionOut(
            source_entity_id=entity_id,
            target_entity_id=other,
            target_name=_BY_ID[other]["name"],
            adamic_adar=round(sum(1 / max(len(_neighbours(s, _RELATIONSHIPS)), 1) for s in shared), 3),
            jaccard=round(len(shared) / union, 3),
            shared_neighbour_ids=shared,
            shared_neighbour_names=[_BY_ID[s]["name"] for s in shared],
        ))

    out.sort(key=lambda p: (p.adamic_adar, p.jaccard), reverse=True)
    return PredictionResponse(entity_id=entity_id, predictions=out[:k])
