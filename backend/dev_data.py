"""Load the stub records into Postgres so the graph has something to show.

TEMPORARY, and not a substitute for seed.py. Rishabh owns F7 and seed.py is
the real thing: ~300 people, three deliberate scenarios, a fixed random seed,
--reset and --verify. This is none of that. It exists only so that W2 F3a can
be verified the way PRD Section 10 asks - an investigator token and an admin
token returning measurably different node counts - instead of both returning
an empty graph because nothing has been seeded yet.

Delete this file the day seed.py lands, together with the stub data it reads.

It takes its rows from routers/entities.py rather than defining its own, so
there is exactly one copy of the fake network and the stubbed endpoints and
the real graph endpoint agree with each other.

    python dev_users.py      # agencies and logins first
    python dev_data.py

Idempotent: running it twice does not duplicate anything.
"""

from datetime import date

from sqlalchemy import select

from app.database import SessionLocal, init_db
from app.models import Agency, Entity, Relationship

# The fake network. It used to live in routers/entities.py, back when that
# router was a stub; now that the router is real, this is the only place it
# belongs - a development fixture. routers/graph.py still reads it for the
# four endpoints that are not real yet (analytics, path, what-if, predict).
# id, type, name, agency_id, agency_code, is_shared, source_ref, attributes
STUB_ENTITIES: list[dict] = [
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
STUB_RELATIONSHIPS: list[dict] = [
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


AGENCY_NAMES = {
    "GJ_POLICE": "Gujarat Police",
    "TELECOM": "Telecom Operator",
    "RTO": "Regional Transport Office",
}


def _agencies(db) -> dict[str, int]:
    """Agency code -> id, creating the two that dev_users.py does not."""
    out = {}
    for code, name in AGENCY_NAMES.items():
        agency = db.scalar(select(Agency).where(Agency.code == code))
        if agency is None:
            agency = Agency(name=name, code=code)
            db.add(agency)
            db.flush()
            print(f"created agency {code} (id={agency.id})")
        out[code] = agency.id
    return out


def main() -> None:
    init_db()
    with SessionLocal() as db:
        agencies = _agencies(db)

        # source_ref is not unique in the schema, so the stub id is what makes a
        # row identifiable on a re-run. Stored in attributes under _stub_id.
        existing = {
            e.attributes.get("_stub_id"): e
            for e in db.scalars(select(Entity)).all()
            if isinstance(e.attributes, dict) and "_stub_id" in e.attributes
        }

        by_stub_id: dict[int, Entity] = {}
        created = 0
        for spec in STUB_ENTITIES:
            entity = existing.get(spec["id"])
            if entity is None:
                entity = Entity(
                    entity_type=spec["entity_type"],
                    name=spec["name"],
                    attributes={**spec["attributes"], "_stub_id": spec["id"]},
                    agency_id=agencies[spec["agency_code"]],
                    source_ref=spec["source_ref"],
                    is_shared=spec["is_shared"],
                )
                db.add(entity)
                created += 1
            by_stub_id[spec["id"]] = entity
        db.flush()
        print(f"entities: {created} created, {len(STUB_ENTITIES) - created} already present")

        have = {
            (r.src_entity_id, r.dst_entity_id, r.rel_type)
            for r in db.scalars(select(Relationship)).all()
        }
        rels = 0
        for spec in STUB_RELATIONSHIPS:
            src = by_stub_id[spec["src"]].id
            dst = by_stub_id[spec["dst"]].id
            if (src, dst, spec["rel_type"]) in have:
                continue
            db.add(Relationship(
                src_entity_id=src,
                dst_entity_id=dst,
                rel_type=spec["rel_type"],
                confidence=spec["confidence"],
                valid_from=date.fromisoformat(spec["valid_from"]),
                valid_to=date.fromisoformat(spec["valid_to"]) if spec["valid_to"] else None,
                source_case=spec["source_case"],
                agency_id=agencies[spec["agency_code"]],
            ))
            rels += 1
        db.commit()
        print(f"relationships: {rels} created, {len(STUB_RELATIONSHIPS) - rels} already present")
        print("done")


if __name__ == "__main__":
    main()
