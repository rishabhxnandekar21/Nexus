"""Search and detail - F4.

The route functions are called directly rather than over HTTP. They are plain
functions once FastAPI's Depends arguments are supplied by hand, and calling
them directly keeps every write inside conftest's rolled-back transaction. An
HTTP client would need its own session wiring, and a mistake there commits
test rows into a table that is meant to be append-only.
"""

from datetime import date

import pytest
from fastapi import HTTPException

from app.routers.entities import get_entity, search_entities
from app.models import Agency, Entity, Relationship, User


@pytest.fixture
def world(db):
    police = Agency(name="Police", code="E_POLICE")
    telecom = Agency(name="Telecom", code="E_TELECOM")
    db.add_all([police, telecom])
    db.flush()

    officer = User(username="e_officer", password_hash="x", role="investigator",
                   agency_id=police.id)
    boss = User(username="e_boss", password_hash="x", role="admin", agency_id=police.id)
    db.add_all([officer, boss])

    ramesh = Entity(entity_type="person", name="Ramesh Bhai", attributes={},
                    agency_id=police.id, is_shared=False)
    suresh = Entity(entity_type="person", name="Suresh Bhai", attributes={},
                    agency_id=police.id, is_shared=False)
    phone = Entity(entity_type="phone", name="+91 90000 00001", attributes={},
                   agency_id=telecom.id, is_shared=True)
    secret = Entity(entity_type="phone", name="+91 90000 00002", attributes={},
                    agency_id=telecom.id, is_shared=False)
    odd = Entity(entity_type="person", name="100% Certain", attributes={},
                 agency_id=police.id, is_shared=False)
    db.add_all([ramesh, suresh, phone, secret, odd])
    db.flush()

    db.add_all([
        Relationship(src_entity_id=ramesh.id, dst_entity_id=suresh.id,
                     rel_type="family_of", confidence=1.0,
                     valid_from=date(2019, 1, 1), agency_id=police.id),
        Relationship(src_entity_id=ramesh.id, dst_entity_id=phone.id,
                     rel_type="owns", confidence=1.0,
                     valid_from=date(2021, 1, 1), agency_id=telecom.id),
    ])
    db.flush()
    return locals()


def _names(results):
    return {r.name for r in results}


# --- search -----------------------------------------------------------------


def test_search_is_agency_scoped(db, world):
    officer = _names(search_entities(None, None, 500, world["officer"], db))
    boss = _names(search_entities(None, None, 500, world["boss"], db))
    assert "Ramesh Bhai" in officer
    assert "+91 90000 00001" in officer, "another agency but shared"
    assert "+91 90000 00002" not in officer, "another agency, not shared"
    assert "+91 90000 00002" in boss, "admin sees everything"


def test_search_matches_part_of_a_name_case_insensitively(db, world):
    assert _names(search_entities(None, "bhai", 500, world["officer"], db)) == {
        "Ramesh Bhai", "Suresh Bhai",
    }
    assert _names(search_entities(None, "RAMESH", 500, world["officer"], db)) == {
        "Ramesh Bhai",
    }


def test_search_treats_wildcards_as_text(db, world):
    """A search for "%" must look for a percent sign, not match every row."""
    hits = _names(search_entities(None, "%", 500, world["boss"], db))
    assert hits == {"100% Certain"}

    assert _names(search_entities(None, "_", 500, world["boss"], db)) == set()


def test_search_filters_by_type(db, world):
    assert _names(search_entities("phone", None, 500, world["boss"], db)) == {
        "+91 90000 00001", "+91 90000 00002",
    }


def test_search_respects_the_limit(db, world):
    assert len(search_entities(None, None, 2, world["boss"], db)) == 2


# --- detail -----------------------------------------------------------------


def test_detail_hides_another_agencys_relationship(db, world):
    """Ramesh owns a shared phone, but the link is a telecom record."""
    officer_view = get_entity(world["ramesh"].id, world["officer"], db)
    admin_view = get_entity(world["ramesh"].id, world["boss"], db)

    assert {r.rel_type for r in officer_view.relationships} == {"family_of"}
    assert {r.rel_type for r in admin_view.relationships} == {"family_of", "owns"}
    assert len(officer_view.neighbours) == 1
    assert len(admin_view.neighbours) == 2


def test_detail_names_both_ends_of_every_relationship(db, world):
    view = get_entity(world["ramesh"].id, world["boss"], db)
    for rel in view.relationships:
        assert rel.src_name and rel.dst_name
        assert "Ramesh Bhai" in (rel.src_name, rel.dst_name)


def test_detail_on_another_agencys_entity_is_404_not_403(db, world):
    """403 would confirm the record exists. 404 does not."""
    with pytest.raises(HTTPException) as caught:
        get_entity(world["secret"].id, world["officer"], db)
    assert caught.value.status_code == 404


def test_detail_on_a_missing_entity_is_404(db, world):
    with pytest.raises(HTTPException) as caught:
        get_entity(99_999_999, world["boss"], db)
    assert caught.value.status_code == 404


def test_detail_on_a_shared_entity_from_another_agency_is_allowed(db, world):
    view = get_entity(world["phone"].id, world["officer"], db)
    assert view.entity.name == "+91 90000 00001"
    # Visible node, but the telecom edge to it is not the officer's to see.
    assert view.relationships == []
    assert view.neighbours == []


def test_detail_agrees_with_search_about_what_is_visible(db, world):
    """The two screens must not disagree about the same user's access."""
    visible = {r.id for r in search_entities(None, None, 500, world["officer"], db)}
    for entity_id in visible:
        get_entity(entity_id, world["officer"], db)  # must not raise
