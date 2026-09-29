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
from sqlalchemy.orm import Session

from app.audit import audited
from app.database import get_db
from app.graph import analyse, build_graph, can_see_entity, shortest_path, to_cytoscape
from app.models import User
from app.schemas import (
    AnalyticsResponse,
    BetweennessShift,
    ComponentStats,
    GraphResponse,
    PathResponse,
    PredictionOut,
    PredictionResponse,
    WhatIfRequest,
    WhatIfResponse,
)

router = APIRouter(prefix="/api/graph", tags=["graph"])

# Twelve fake records kept ONLY for the four endpoints below that are not
# real yet - analytics (W4), path, what-if and predict (W5). They used to
# live in dev_data.py, which seed.py has now replaced; rather than keep a
# second loader alive for them, the data sits here and dies with the last
# stub. GET /api/graph does not touch it.
# id, type, name, agency_id, agency_code, is_shared, source_ref, attributes
_ENTITIES: list[dict] = [
    {"id": 1, "entity_type": "person", "name": "Ramesh Patel", "agency_id": 1,
     "agency_code": "GJ_POLICE", "is_shared": True, "source_ref": "FIR/2021/0112",
     "attributes": {"age": 41, "alias": "Rameshbhai", "district": "Ahmedabad"}},
    {"id": 2, "entity_type": "person", "name": "Suresh Patel", "agency_id": 1,
     "agency_code": "GJ_POLICE", "is_shared": False, "source_ref": "FIR/2021/0112",
     "attributes": {"age": 37, "district": "Ahmedabad"}},
    {"id": 3, "entity_type": "person", "name": "Imran Shaikh", "agency_id": 1,
     "agency_code": "GJ_POLICE", "is_shared": False, "source_ref": "FIR/2022/0431",
     "attributes": {"age": 29, "alias": "Immu", "district": "Surat"}},
    {"id": 4, "entity_type": "person", "name": "Dinesh Chauhan", "agency_id": 1,
     "agency_code": "GJ_POLICE", "is_shared": True, "source_ref": "FIR/2023/0077",
     "attributes": {"age": 52, "district": "Vadodara", "note": "bridge node in the stub set"}},
    {"id": 5, "entity_type": "phone", "name": "+91 98250 11223", "agency_id": 2,
     "agency_code": "TELECOM", "is_shared": True, "source_ref": "CDR/A/88121",
     "attributes": {"operator": "Jio", "circle": "Gujarat"}},
    {"id": 6, "entity_type": "phone", "name": "+91 99042 55871", "agency_id": 2,
     "agency_code": "TELECOM", "is_shared": False, "source_ref": "CDR/A/88997",
     "attributes": {"operator": "Airtel", "circle": "Gujarat"}},
    {"id": 7, "entity_type": "vehicle", "name": "GJ-01-AB-4417", "agency_id": 3,
     "agency_code": "RTO", "is_shared": True, "source_ref": "RTO/AHD/55120",
     "attributes": {"plate": "GJ-01-AB-4417", "model": "Mahindra Bolero", "colour": "white"}},
    {"id": 8, "entity_type": "vehicle", "name": "GJ-05-KL-9082", "agency_id": 3,
     "agency_code": "RTO", "is_shared": False, "source_ref": "RTO/SRT/21908",
     "attributes": {"plate": "GJ-05-KL-9082", "model": "Tata Ace", "colour": "blue"}},
    {"id": 9, "entity_type": "location", "name": "Kalupur Market, Ahmedabad", "agency_id": 1,
     "agency_code": "GJ_POLICE", "is_shared": True, "source_ref": None,
     "attributes": {"city": "Ahmedabad", "zone": "East"}},
    {"id": 10, "entity_type": "location", "name": "Adajan, Surat", "agency_id": 1,
     "agency_code": "GJ_POLICE", "is_shared": False, "source_ref": None,
     "attributes": {"city": "Surat", "zone": "West"}},
    {"id": 11, "entity_type": "crime_event", "name": "FIR 112/2021 - vehicle theft",
     "agency_id": 1, "agency_code": "GJ_POLICE", "is_shared": True,
     "source_ref": "FIR/2021/0112",
     "attributes": {"crime_type": "vehicle_theft", "status": "under_investigation"}},
    {"id": 12, "entity_type": "organization", "name": "Sabarmati Transport Co.",
     "agency_id": 1, "agency_code": "GJ_POLICE", "is_shared": False,
     "source_ref": "FIR/2023/0077", "attributes": {"registered": 2016, "city": "Ahmedabad"}},
]

# src, dst, rel_type, confidence, valid_from, valid_to, source_case, agency_code
_RELATIONSHIPS: list[dict] = [
    {"id": 1, "src": 1, "dst": 2, "rel_type": "family_of", "confidence": 0.95,
     "valid_from": "2019-01-01", "valid_to": None, "source_case": "FIR/2021/0112",
     "agency_code": "GJ_POLICE"},
    {"id": 2, "src": 1, "dst": 3, "rel_type": "co_accused", "confidence": 0.88,
     "valid_from": "2021-03-14", "valid_to": None, "source_case": "FIR/2021/0112",
     "agency_code": "GJ_POLICE"},
    {"id": 3, "src": 1, "dst": 5, "rel_type": "owns", "confidence": 1.0,
     "valid_from": "2020-06-02", "valid_to": None, "source_case": "CDR/A/88121",
     "agency_code": "TELECOM"},
    {"id": 4, "src": 2, "dst": 6, "rel_type": "owns", "confidence": 1.0,
     "valid_from": "2020-08-19", "valid_to": None, "source_case": "CDR/A/88997",
     "agency_code": "TELECOM"},
    {"id": 5, "src": 5, "dst": 6, "rel_type": "called", "confidence": 1.0,
     "valid_from": "2021-03-11", "valid_to": "2021-03-11", "source_case": "CDR/A/88121",
     "agency_code": "TELECOM"},
    {"id": 6, "src": 3, "dst": 7, "rel_type": "owns", "confidence": 0.9,
     "valid_from": "2021-01-20", "valid_to": None, "source_case": "RTO/AHD/55120",
     "agency_code": "RTO"},
    {"id": 7, "src": 7, "dst": 9, "rel_type": "present_at", "confidence": 0.72,
     "valid_from": "2021-03-14", "valid_to": "2021-03-14", "source_case": "FIR/2021/0112",
     "agency_code": "GJ_POLICE"},
    {"id": 8, "src": 1, "dst": 11, "rel_type": "suspect_in", "confidence": 0.81,
     "valid_from": "2021-03-14", "valid_to": None, "source_case": "FIR/2021/0112",
     "agency_code": "GJ_POLICE"},
    {"id": 9, "src": 3, "dst": 11, "rel_type": "suspect_in", "confidence": 0.77,
     "valid_from": "2021-03-14", "valid_to": None, "source_case": "FIR/2021/0112",
     "agency_code": "GJ_POLICE"},
    {"id": 10, "src": 11, "dst": 9, "rel_type": "present_at", "confidence": 1.0,
     "valid_from": "2021-03-14", "valid_to": "2021-03-14", "source_case": "FIR/2021/0112",
     "agency_code": "GJ_POLICE"},
    {"id": 11, "src": 4, "dst": 3, "rel_type": "co_accused", "confidence": 0.64,
     "valid_from": "2023-02-08", "valid_to": None, "source_case": "FIR/2023/0077",
     "agency_code": "GJ_POLICE"},
    {"id": 12, "src": 4, "dst": 12, "rel_type": "family_of", "confidence": 0.55,
     "valid_from": "2023-02-08", "valid_to": None, "source_case": "FIR/2023/0077",
     "agency_code": "GJ_POLICE"},
    {"id": 13, "src": 12, "dst": 8, "rel_type": "owns", "confidence": 1.0,
     "valid_from": "2022-11-30", "valid_to": None, "source_case": "RTO/SRT/21908",
     "agency_code": "RTO"},
    {"id": 14, "src": 2, "dst": 10, "rel_type": "present_at", "confidence": 0.6,
     "valid_from": "2022-07-04", "valid_to": "2022-07-04", "source_case": "FIR/2022/0431",
     "agency_code": "GJ_POLICE"},
]


_BY_ID = {e["id"]: e for e in _ENTITIES}

# The node cap lives in graph.py, which is the only thing that applies it. It
# was duplicated here while GET /api/graph was a stub; two copies of a limit
# are two copies that can drift apart.

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


def _neighbours(entity_id: int, edges: list[dict]) -> set[int]:
    out = set()
    for r in edges:
        if r["src"] == entity_id:
            out.add(r["dst"])
        elif r["dst"] == entity_id:
            out.add(r["src"])
    return out


@router.get("", response_model=GraphResponse)
def get_graph(
    center: int | None = Query(default=None),
    depth: int = Query(default=2, ge=1, le=3),
    date_from: date | None = Query(default=None, alias="from"),
    date_to: date | None = Query(default=None, alias="to"),
    types: str | None = Query(default=None, description="comma-separated entity types"),
    user: User = Depends(audited("read", "graph")),
    db: Session = Depends(get_db),
) -> GraphResponse:
    """REAL - W2, F3a. Agency-scoped, date-filtered Cytoscape elements.

    The first endpoint off the stubs. Returns an empty graph until seed.py
    lands; that is correct, not a failure.
    """
    if center is not None and not can_see_entity(db, user, center):
        # Same answer whether it is missing or simply not theirs.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"no entity with id {center}",
        )

    graph = build_graph(
        db,
        user,
        center_id=center,
        depth=depth,
        date_from=date_from,
        date_to=date_to,
        types=[t.strip() for t in types.split(",") if t.strip()] if types else None,
    )
    elements = to_cytoscape(graph)
    return GraphResponse(
        nodes=elements["nodes"],
        edges=elements["edges"],
        center_id=center,
        depth=depth,
        truncated=graph.graph["truncated"],
    )


@router.get("/analytics", response_model=AnalyticsResponse)
def get_analytics(
    center: int | None = Query(default=None),
    depth: int = Query(default=2, ge=1, le=3),
    user: User = Depends(audited("analytics", "graph")),
    db: Session = Depends(get_db),
) -> AnalyticsResponse:
    """REAL - W4, F5. Centrality and communities over the caller's own view.

    Computed on the scoped graph, not the whole network: an investigator's
    "most central person" should be the most central person they are allowed
    to see, which is also the only number they could act on.
    """
    if center is not None and not can_see_entity(db, user, center):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"no entity with id {center}",
        )
    result = analyse(build_graph(db, user, center_id=center, depth=depth))
    return AnalyticsResponse(**result)


@router.get("/path", response_model=PathResponse)
def get_path(
    from_id: int = Query(alias="from"),
    to_id: int = Query(alias="to"),
    user: User = Depends(audited("path", "graph")),
    db: Session = Depends(get_db),
) -> PathResponse:
    """REAL - W4, F5. Shortest path across the caller's own view.

    Both endpoints must be visible, and an invisible one gives the same 404 as
    a missing one. A path is only meaningful through edges the caller can see,
    so a route that exists for an admin may genuinely not exist here.
    """
    for entity_id in (from_id, to_id):
        if not can_see_entity(db, user, entity_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"no entity with id {entity_id}",
            )
    return PathResponse(**shortest_path(build_graph(db, user), from_id, to_id))


@router.post("/whatif", response_model=WhatIfResponse)
def what_if(
    payload: WhatIfRequest,
    user: User = Depends(audited("whatif", "graph")),
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
    user: User = Depends(audited("predict", "graph")),
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
