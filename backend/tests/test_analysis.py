"""F9: what-if simulation and link prediction.

Proves the logic independently of the routes, which live in routers/graph.py and
still return stub data - see the REQUEST in PROGRESS.md. The important case is
the last one: removing the seeded Scenario C bridge has to split the largest
component roughly in half, which is demo criterion S5b.
"""

import networkx as nx
import pytest
from sqlalchemy import select

from app.analysis import predict_links, what_if
from app.database import SessionLocal
from app.graph import build_graph
from app.models import Entity, User


def _line_graph(n: int) -> nx.Graph:
    """A path 0-1-2-...-n, where every interior node is a cut vertex."""
    g = nx.Graph()
    for i in range(n):
        g.add_node(i, name=f"n{i}")
        if i:
            g.add_edge(i - 1, i)
    return g


# --------------------------------------------------------------- what_if


def test_removing_nothing_leaves_the_graph_unchanged():
    g = _line_graph(6)
    result = what_if(g, [])
    assert result["removed_entity_ids"] == []
    assert result["before"] == result["after"]


def test_ids_absent_from_the_graph_are_ignored_not_errors():
    g = _line_graph(4)
    result = what_if(g, [99, 1])
    assert result["removed_entity_ids"] == [1]


def test_removing_a_cut_vertex_splits_the_graph():
    g = _line_graph(6)          # 0-1-2-3-4-5, removing 2 gives {0,1} and {3,4,5}
    result = what_if(g, [2])
    assert result["before"]["component_count"] == 1
    assert result["after"]["component_count"] == 2
    assert result["before"]["largest_component_size"] == 6
    assert result["after"]["largest_component_size"] == 3
    assert result["after"]["node_count"] == 5


def test_the_source_graph_is_not_mutated():
    g = _line_graph(5)
    what_if(g, [2])
    assert g.number_of_nodes() == 5
    assert g.has_node(2)


def test_top_risers_excludes_removed_nodes_and_flat_nodes():
    g = _line_graph(7)
    result = what_if(g, [3])
    ids = [r["entity_id"] for r in result["top_risers"]]
    assert 3 not in ids
    assert all(r["delta"] > 0 for r in result["top_risers"])
    assert len(result["top_risers"]) <= 5


def test_a_riser_is_reported_when_one_exists():
    # Two triangles joined by a long detour; cutting the direct link forces
    # traffic through the detour, so the detour's nodes gain betweenness.
    g = nx.Graph()
    g.add_edges_from([(0, 1), (1, 2), (0, 2), (2, 3), (3, 4),
                      (2, 10), (10, 11), (11, 4)])
    for n in g.nodes:
        g.nodes[n]["name"] = f"n{n}"
    result = what_if(g, [3])
    assert result["top_risers"], "expected at least one node to rise"
    assert result["top_risers"][0]["after"] > result["top_risers"][0]["before"]


# ---------------------------------------------------------- predict_links


def test_prediction_on_an_unknown_entity_is_empty_not_an_error():
    assert predict_links(_line_graph(4), 999) == []


def test_only_non_adjacent_pairs_with_a_shared_neighbour_are_returned():
    g = nx.Graph()
    g.add_edges_from([(1, 2), (2, 3), (3, 4)])
    for n in g.nodes:
        g.nodes[n]["name"] = f"n{n}"
    out = predict_links(g, 1)
    targets = [p["target_entity_id"] for p in out]
    assert targets == [3]                  # 2 is adjacent, 4 shares nothing with 1
    assert out[0]["shared_neighbour_ids"] == [2]
    assert out[0]["jaccard"] > 0


def test_a_quiet_shared_neighbour_outranks_a_hub():
    # 1 and 2 share only the hub 0; 3 and 4 share only the quiet node 5.
    # Adamic-Adar weights by inverse log degree, so the quiet pair must rank
    # higher even though both pairs share exactly one neighbour.
    g = nx.Graph()
    g.add_edges_from([(0, 1), (0, 2), (0, 6), (0, 7), (0, 8), (0, 9),
                      (5, 3), (5, 4)])
    for n in g.nodes:
        g.nodes[n]["name"] = f"n{n}"
    hub_pair = predict_links(g, 1)[0]
    quiet_pair = predict_links(g, 3)[0]
    assert quiet_pair["adamic_adar"] > hub_pair["adamic_adar"]


def test_k_caps_the_result():
    g = nx.star_graph(12)       # centre 0, leaves 1..12 all share the centre
    for n in g.nodes:
        g.nodes[n]["name"] = f"n{n}"
    assert len(predict_links(g, 1, k=3)) == 3


# ------------------------------------------- S5b, against the seeded data


@pytest.fixture
def seeded():
    """A read-only session against the real seeded database.

    The shared `db` fixture empties every table so tests can assert exact
    counts, which is right for unit tests and wrong for this one - S5b is a
    claim about seed.py's output. This session only reads, so it needs no
    cleanup.
    """
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def test_removing_the_seeded_bridge_splits_the_network(seeded):
    """S5b. The seeded Scenario C bridge is an articulation point of the
    largest component, and removing it leaves two roughly equal halves."""
    admin = seeded.scalar(select(User).where(User.role == "admin"))
    bridge = seeded.scalar(
        select(Entity).where(Entity.attributes["scenario"].astext == "C_bridge"))
    if admin is None or bridge is None:
        pytest.skip("run seed.py --reset first")

    graph = build_graph(seeded, admin)
    if not graph.has_node(bridge.id):
        pytest.skip("bridge not in the admin graph")

    result = what_if(graph, [bridge.id])

    assert result["after"]["component_count"] > result["before"]["component_count"]
    assert result["after"]["largest_component_size"] < result["before"]["largest_component_size"]

    # Roughly equal: the biggest surviving piece must not swallow everything.
    biggest = result["after"]["largest_component_size"]
    lost = result["before"]["largest_component_size"] - biggest
    assert lost > 0
    assert biggest / (biggest + lost) < 0.75, (
        f"expected a roughly even split, got {biggest} vs {lost}")
