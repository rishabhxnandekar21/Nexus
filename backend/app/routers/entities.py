"""Entity search, detail and creation.

W1-7 STUB. Every route here returns hardcoded data that conforms to the
schemas; nothing touches the database yet. The real queries land in W2/W3 with
graph.py. The shapes are final - the frontend can be built against them now.

The twelve fake records are the same ones graph.py serves, so a search result
and a graph node refer to the same thing while both are stubs.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_admin
from app.database import get_db
from app.models import Agency, User
from app.schemas import (
    EntityCreate,
    EntityDetailOut,
    EntityOut,
    EntitySearchResult,
    RelationshipOut,
)

router = APIRouter(prefix="/api/entities", tags=["entities"])

_CREATED = datetime(2026, 9, 20, 10, 30)

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


def _search_result(e: dict) -> EntitySearchResult:
    return EntitySearchResult(
        id=e["id"], entity_type=e["entity_type"], name=e["name"],
        agency_code=e["agency_code"], is_shared=e["is_shared"],
    )


def _entity_out(e: dict) -> EntityOut:
    return EntityOut(
        id=e["id"], entity_type=e["entity_type"], name=e["name"],
        attributes=e["attributes"], agency_id=e["agency_id"],
        agency_code=e["agency_code"], source_ref=e["source_ref"],
        is_shared=e["is_shared"], created_at=_CREATED,
    )


def _relationship_out(r: dict) -> RelationshipOut:
    return RelationshipOut(
        id=r["id"], src_entity_id=r["src"], src_name=_BY_ID[r["src"]]["name"],
        dst_entity_id=r["dst"], dst_name=_BY_ID[r["dst"]]["name"],
        rel_type=r["rel_type"], confidence=r["confidence"],
        valid_from=r["valid_from"], valid_to=r["valid_to"],
        source_case=r["source_case"], agency_code=r["agency_code"],
    )


@router.get("", response_model=list[EntitySearchResult])
def search_entities(
    type: str | None = Query(default=None, description="filter by entity_type"),
    q: str | None = Query(default=None, description="case-insensitive partial name match"),
    limit: int = Query(default=50, ge=1, le=500),
    user: User = Depends(get_current_user),
) -> list[EntitySearchResult]:
    """STUB. Filters the twelve fake records so the search box behaves realistically."""
    rows = _ENTITIES
    if type:
        rows = [e for e in rows if e["entity_type"] == type]
    if q:
        needle = q.lower()
        rows = [e for e in rows if needle in e["name"].lower()]
    return [_search_result(e) for e in rows[:limit]]


@router.get("/{entity_id}", response_model=EntityDetailOut)
def get_entity(
    entity_id: int,
    user: User = Depends(get_current_user),
) -> EntityDetailOut:
    """STUB. The record plus every edge touching it and the neighbours they reach."""
    entity = _BY_ID.get(entity_id)
    if entity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"no entity with id {entity_id}",
        )
    edges = [r for r in _RELATIONSHIPS if entity_id in (r["src"], r["dst"])]
    neighbour_ids = {r["src"] if r["dst"] == entity_id else r["dst"] for r in edges}
    return EntityDetailOut(
        entity=_entity_out(entity),
        relationships=[_relationship_out(r) for r in edges],
        neighbours=[_search_result(_BY_ID[i]) for i in sorted(neighbour_ids)],
    )


@router.post("", response_model=EntityOut, status_code=status.HTTP_201_CREATED)
def create_entity(
    payload: EntityCreate,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> EntityOut:
    """STUB. Admin only - the first route to use require_admin over HTTP.

    Echoes the payload back with a fake id. The caller's agency is stamped on it
    rather than accepted from the body, which is how the real route must behave.
    The code is read from that agency rather than assumed, so the two fields
    cannot contradict each other once seed.py creates all three agencies.
    """
    agency = db.get(Agency, user.agency_id)
    if agency is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"user {user.id} references agency {user.agency_id}, which does not exist",
        )
    return EntityOut(
        id=max(_BY_ID) + 1,
        entity_type=payload.entity_type.value,
        name=payload.name,
        attributes=payload.attributes,
        agency_id=user.agency_id,
        agency_code=agency.code,
        source_ref=payload.source_ref,
        is_shared=payload.is_shared,
        created_at=_CREATED,
    )
