"""build_graph() - scoping, date filtering, centring.

These tests build their own rows inside the rolled-back transaction from
conftest, because seed.py is W2 and Rishabh's and does not exist yet. That is
deliberate rather than a stopgap: demo criterion S2 is "two logins produce two
visibly different graphs", and asserting it on data the test controls is a
stronger check than eyeballing a dashboard full of seeded records.
"""

from datetime import date

import pytest
from sqlalchemy import delete

from app.graph import (
    NODE_CAP, analyse, build_graph, can_see_entity, shortest_path, to_cytoscape,
)
from app.models import Agency, Entity, Relationship, User


@pytest.fixture
def world(db):
    """Three agencies, two users, and a small cross-agency network.

    police:   P1, P2            (P2 shared)
    telecom:  T1                (shared)
    rto:      R1                (not shared)

    edges     P1-P2  police,  2019-01-01, open ended
              P1-T1  telecom, 2021-06-01, open ended
              P2-R1  rto,     2020-01-01, ended 2020-12-31
    """
    police = Agency(name="Gujarat Police", code="T_POLICE")
    telecom = Agency(name="Telecom", code="T_TELECOM")
    rto = Agency(name="RTO", code="T_RTO")
    db.add_all([police, telecom, rto])
    db.flush()

    officer = User(
        username="t_officer", password_hash="x", role="investigator",
        agency_id=police.id,
    )
    boss = User(username="t_boss", password_hash="x", role="admin", agency_id=police.id)
    db.add_all([officer, boss])

    p1 = Entity(entity_type="person", name="P1", attributes={}, agency_id=police.id, is_shared=False)
    p2 = Entity(entity_type="person", name="P2", attributes={}, agency_id=police.id, is_shared=True)
    t1 = Entity(entity_type="phone", name="T1", attributes={}, agency_id=telecom.id, is_shared=True)
    r1 = Entity(entity_type="vehicle", name="R1", attributes={}, agency_id=rto.id, is_shared=False)
    db.add_all([p1, p2, t1, r1])
    db.flush()

    db.add_all([
        Relationship(src_entity_id=p1.id, dst_entity_id=p2.id, rel_type="family_of",
                     confidence=1.0, valid_from=date(2019, 1, 1), agency_id=police.id),
        Relationship(src_entity_id=p1.id, dst_entity_id=t1.id, rel_type="owns",
                     confidence=1.0, valid_from=date(2021, 6, 1), agency_id=telecom.id),
        Relationship(src_entity_id=p2.id, dst_entity_id=r1.id, rel_type="owns",
                     confidence=1.0, valid_from=date(2020, 1, 1),
                     valid_to=date(2020, 12, 31), agency_id=rto.id),
    ])
    db.flush()
    return {"officer": officer, "admin": boss, "p1": p1, "p2": p2, "t1": t1, "r1": r1}


# --- S2: the same query, two users, two different graphs --------------------


def test_admin_sees_every_entity_and_edge(db, world):
    graph = build_graph(db, world["admin"])
    names = {a["name"] for _, a in graph.nodes(data=True)}
    assert {"P1", "P2", "T1", "R1"} <= names
    assert graph.number_of_edges() >= 3


def test_investigator_sees_less_than_the_admin(db, world):
    officer_graph = build_graph(db, world["officer"])
    admin_graph = build_graph(db, world["admin"])
    # This inequality is demo criterion S2, asserted rather than eyeballed.
    assert officer_graph.number_of_nodes() < admin_graph.number_of_nodes()
    assert officer_graph.number_of_edges() < admin_graph.number_of_edges()


def test_investigator_sees_own_agency_and_shared_entities_only(db, world):
    graph = build_graph(db, world["officer"])
    names = {a["name"] for _, a in graph.nodes(data=True)}
    assert "P1" in names, "own agency"
    assert "P2" in names, "own agency"
    assert "T1" in names, "another agency but shared"
    assert "R1" not in names, "another agency and not shared"


def test_investigator_does_not_see_another_agencys_relationship(db, world):
    """T1 is visible to the officer, but the telecom edge reaching it is not.

    A shared node with no visible edges is the intended outcome: the node may
    be shareable while the call record that links it is not.
    """
    graph = build_graph(db, world["officer"])
    assert graph.has_edge(world["p1"].id, world["p2"].id), "own agency edge"
    assert not graph.has_edge(world["p1"].id, world["t1"].id), "telecom edge"
    assert graph.degree(world["t1"].id) == 0


# --- date filtering ---------------------------------------------------------


def test_open_ended_edge_survives_a_much_later_window(db, world):
    """The bug caught in review: valid_from alone erases still-true edges."""
    graph = build_graph(db, world["admin"], date_from=date(2024, 1, 1))
    assert graph.has_edge(world["p1"].id, world["p2"].id), (
        "family_of began in 2019 and never ended - it is still true in 2024"
    )


def test_an_ended_edge_is_excluded_from_a_later_window(db, world):
    graph = build_graph(db, world["admin"], date_from=date(2024, 1, 1))
    assert not graph.has_edge(world["p2"].id, world["r1"].id), "ended 2020-12-31"


def test_an_edge_is_excluded_before_it_began(db, world):
    graph = build_graph(db, world["admin"], date_to=date(2019, 6, 1))
    assert graph.has_edge(world["p1"].id, world["p2"].id), "began 2019-01-01"
    assert not graph.has_edge(world["p1"].id, world["t1"].id), "begins 2021"


def test_an_ended_edge_is_visible_inside_its_own_window(db, world):
    graph = build_graph(
        db, world["admin"], date_from=date(2020, 6, 1), date_to=date(2020, 7, 1)
    )
    assert graph.has_edge(world["p2"].id, world["r1"].id)


# --- centring, types, capping ----------------------------------------------


def test_depth_one_reaches_only_immediate_neighbours(db, world):
    graph = build_graph(db, world["admin"], center_id=world["r1"].id, depth=1)
    assert set(graph.nodes) == {world["r1"].id, world["p2"].id}


def test_depth_two_reaches_one_hop_further(db, world):
    graph = build_graph(db, world["admin"], center_id=world["r1"].id, depth=2)
    assert world["p1"].id in graph.nodes


def test_centring_on_an_invisible_entity_yields_an_empty_graph(db, world):
    graph = build_graph(db, world["officer"], center_id=world["r1"].id)
    assert graph.number_of_nodes() == 0


def test_types_filter(db, world):
    graph = build_graph(db, world["admin"], types=["person"])
    assert {a["entity_type"] for _, a in graph.nodes(data=True)} == {"person"}


def test_can_see_entity_matches_the_graph(db, world):
    assert can_see_entity(db, world["officer"], world["p1"].id) is True
    assert can_see_entity(db, world["officer"], world["t1"].id) is True, "shared"
    assert can_see_entity(db, world["officer"], world["r1"].id) is False
    assert can_see_entity(db, world["admin"], world["r1"].id) is True


def test_parallel_relationships_collapse_onto_one_edge(db, world):
    """Two records of the same link must not become two edges - the centrality
    and community algorithms in F5 assume a simple graph."""
    db.add(Relationship(
        src_entity_id=world["p1"].id, dst_entity_id=world["p2"].id,
        rel_type="co_accused", confidence=0.8, valid_from=date(2022, 1, 1),
        agency_id=world["officer"].agency_id,
    ))
    db.flush()
    graph = build_graph(db, world["admin"])
    assert len(graph[world["p1"].id][world["p2"].id]["rel_ids"]) == 2


def test_truncation_flags_itself(db, world, monkeypatch):
    monkeypatch.setattr("app.graph.NODE_CAP", 2)
    graph = build_graph(db, world["admin"])
    assert graph.graph["truncated"] is True
    assert graph.number_of_nodes() <= 3, "cap plus the centre allowance"


def test_empty_database_is_an_empty_graph_not_an_error(db):
    """An empty database must give an empty graph, not an exception.

    Clears the tables inside the rolled-back transaction rather than assuming
    the database happens to be empty - it was not, once dev_data.py existed,
    and a test that passes only because of ambient state is worse than no test.
    """
    agency = Agency(name="Nowhere", code="T_EMPTY")
    db.add(agency)
    db.flush()
    db.execute(delete(Relationship))
    db.execute(delete(Entity))
    db.flush()

    user = User(
        username="t_nobody", password_hash="x", role="admin", agency_id=agency.id
    )
    graph = build_graph(db, user)
    assert graph.number_of_nodes() == 0
    assert graph.number_of_edges() == 0
    assert graph.graph["truncated"] is False


# --- serialization ----------------------------------------------------------


def test_cytoscape_ids_are_strings_and_edges_line_up(db, world):
    elements = to_cytoscape(build_graph(db, world["admin"]))
    node_ids = {n["data"]["id"] for n in elements["nodes"]}
    assert all(isinstance(i, str) for i in node_ids)
    for edge in elements["edges"]:
        assert isinstance(edge["data"]["source"], str)
        # The failure this guards: an edge endpoint that no node id matches
        # renders nothing at all, with no error.
        assert edge["data"]["source"] in node_ids
        assert edge["data"]["target"] in node_ids


def test_node_cap_constant_matches_the_prd():
    assert NODE_CAP == 500


# --- analytics and shortest path - F5 ---------------------------------------
#
# The world fixture is the path T1 - P1 - P2 - R1 for an admin, which makes
# every centrality hand-checkable: the two middle nodes carry all the paths,
# the two ends carry none.


def test_analytics_returns_a_metric_for_every_node(db, world):
    result = analyse(build_graph(db, world["admin"]))
    assert {m["name"] for m in result["metrics"]} == {"P1", "P2", "T1", "R1"}
    for m in result["metrics"]:
        assert set(m) == {
            "entity_id", "name", "degree", "betweenness", "pagerank", "community",
        }


def test_degree_and_betweenness_match_the_shape_of_the_graph(db, world):
    by_name = {m["name"]: m for m in analyse(build_graph(db, world["admin"]))["metrics"]}
    # T1 - P1 - P2 - R1: the ends have one edge, the middles two.
    assert by_name["T1"]["degree"] == 1
    assert by_name["R1"]["degree"] == 1
    assert by_name["P1"]["degree"] == 2
    assert by_name["P2"]["degree"] == 2
    # Only the middle nodes lie on paths between other pairs.
    assert by_name["P1"]["betweenness"] > 0
    assert by_name["P2"]["betweenness"] > 0
    assert by_name["T1"]["betweenness"] == 0
    assert by_name["R1"]["betweenness"] == 0


def test_pagerank_sums_to_one(db, world):
    total = sum(m["pagerank"] for m in analyse(build_graph(db, world["admin"]))["metrics"])
    assert abs(total - 1.0) < 0.01


def test_top_connectors_leaves_out_nodes_no_path_runs_through(db, world):
    """Five zeros would be a worse answer than two real ones."""
    top = analyse(build_graph(db, world["admin"]))["top_connectors"]
    assert {t["name"] for t in top} == {"P1", "P2"}
    assert all(t["betweenness"] > 0 for t in top)


def test_analytics_is_scoped_like_the_graph(db, world):
    """The officer's centrality is computed over the officer's own view."""
    officer = analyse(build_graph(db, world["officer"]))
    assert "R1" not in {m["name"] for m in officer["metrics"]}


def test_analytics_on_an_empty_graph_is_empty_not_an_error(db):
    import networkx as nx

    assert analyse(nx.Graph()) == {
        "metrics": [], "top_connectors": [], "community_count": 0,
    }


def test_analytics_on_an_edgeless_graph(db, world):
    """greedy_modularity has nothing to maximise; every node stands alone."""
    graph = build_graph(db, world["admin"])
    graph.remove_edges_from(list(graph.edges))
    result = analyse(graph)
    assert result["community_count"] == 4
    assert all(m["betweenness"] == 0 for m in result["metrics"])
    assert result["top_connectors"] == []


def test_shortest_path_across_the_whole_chain(db, world):
    result = shortest_path(build_graph(db, world["admin"]), world["t1"].id, world["r1"].id)
    assert result["found"] is True
    assert result["names"] == ["T1", "P1", "P2", "R1"]
    assert result["length"] == 3
    assert result["rel_types"] == ["owns", "family_of", "owns"]


def test_shortest_path_to_self_is_zero_hops(db, world):
    result = shortest_path(build_graph(db, world["admin"]), world["p1"].id, world["p1"].id)
    assert result["found"] is True
    assert result["length"] == 0


def test_no_path_is_found_false_not_an_exception(db, world):
    graph = build_graph(db, world["admin"])
    graph.remove_edges_from(list(graph.edges))
    result = shortest_path(graph, world["t1"].id, world["r1"].id)
    assert result["found"] is False
    assert result["entity_ids"] == []


def test_a_path_the_caller_cannot_see_is_not_found(db, world):
    """R1 is invisible to the officer, so no route reaches it - even though
    one exists for an admin. Scoping has to hold here too."""
    result = shortest_path(build_graph(db, world["officer"]), world["p1"].id, world["r1"].id)
    assert result["found"] is False
