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
from app.routers.entities import _ENTITIES, _RELATIONSHIPS

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
        for spec in _ENTITIES:
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
        print(f"entities: {created} created, {len(_ENTITIES) - created} already present")

        have = {
            (r.src_entity_id, r.dst_entity_id, r.rel_type)
            for r in db.scalars(select(Relationship)).all()
        }
        rels = 0
        for spec in _RELATIONSHIPS:
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
        print(f"relationships: {rels} created, {len(_RELATIONSHIPS) - rels} already present")
        print("done")


if __name__ == "__main__":
    main()
