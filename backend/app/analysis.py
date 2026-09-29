"""Network impact simulation and link prediction. F9.

Two deliberately narrow claims, and the naming matters. This removes nodes from
a graph of records that already exist and measures how the structure changes,
and it ranks pairs that are structurally likely to be connected but are not
recorded as connected. It does not predict crime, and it does not predict that
any person will offend - see PRD Section 4, N1. The UI says "network impact
simulation" for the same reason.

Consumes the graph `graph.py` returns and never edits it, which is the one
interface between the two of us (PRD Section 11).
"""

from __future__ import annotations

import networkx as nx

TOP_RISERS = 5


def _component_stats(graph: nx.Graph) -> dict:
    components = list(nx.connected_components(graph)) if graph.number_of_nodes() else []
    return {
        "node_count": graph.number_of_nodes(),
        "edge_count": graph.number_of_edges(),
        "component_count": len(components),
        "largest_component_size": max((len(c) for c in components), default=0),
    }


def _betweenness(graph: nx.Graph) -> dict[int, float]:
    """Exact betweenness. Cheap enough at the PRD's 1,500-entity ceiling.

    Sampling with k would make the before/after comparison noisy, and a node
    appearing to rise because of sampling error would be worse than useless on a
    screen that is meant to say who the new key connector is.
    """
    if graph.number_of_nodes() < 3:
        return dict.fromkeys(graph.nodes, 0.0)
    return nx.betweenness_centrality(graph, normalized=True)


def what_if(graph: nx.Graph, remove_entity_ids: list[int]) -> dict:
    """Remove nodes and report how the network's shape changed.

    `top_risers` is the five nodes whose betweenness rose most - in plain terms,
    who has to be routed through now that the removed nodes are gone. Nodes that
    were removed are excluded, and so are nodes whose betweenness did not move,
    because a list padded with zeros reads as a result when it is not.
    """
    present = [i for i in remove_entity_ids if graph.has_node(i)]

    before_stats = _component_stats(graph)
    before_bc = _betweenness(graph)

    reduced = graph.copy()
    reduced.remove_nodes_from(present)

    after_stats = _component_stats(reduced)
    after_bc = _betweenness(reduced)

    removed = set(present)
    shifts = []
    for node in reduced.nodes:
        if node in removed:
            continue
        before = before_bc.get(node, 0.0)
        after = after_bc.get(node, 0.0)
        delta = after - before
        if delta <= 0:
            continue
        shifts.append({
            "entity_id": node,
            "name": reduced.nodes[node].get("name", str(node)),
            "before": round(before, 6),
            "after": round(after, 6),
            "delta": round(delta, 6),
        })
    shifts.sort(key=lambda s: s["delta"], reverse=True)

    return {
        "removed_entity_ids": present,
        "before": before_stats,
        "after": after_stats,
        "top_risers": shifts[:TOP_RISERS],
    }


def predict_links(graph: nx.Graph, entity_id: int, k: int = 5) -> list[dict]:
    """Likely-but-absent links for one entity, ranked by Adamic-Adar.

    Both measures come from NetworkX. Adamic-Adar weights a shared neighbour by
    the inverse log of its degree, so two people who share a quiet contact score
    higher than two who share a hub everyone touches - which is the more
    interesting signal. Jaccard is reported alongside it as the plainer
    "how much of your world overlaps" number.

    Only non-adjacent pairs with at least one neighbour in common are considered;
    everything else scores zero and would just pad the list.
    """
    if not graph.has_node(entity_id):
        return []

    mine = set(graph.neighbors(entity_id))
    candidates = [
        other for other in graph.nodes
        if other != entity_id
        and not graph.has_edge(entity_id, other)
        and mine & set(graph.neighbors(other))
    ]
    if not candidates:
        return []

    pairs = [(entity_id, other) for other in candidates]
    # A common neighbour has degree >= 2 by definition, so log(degree) is never
    # zero and NetworkX's Adamic-Adar cannot divide by zero here.
    adamic = {v: score for _, v, score in nx.adamic_adar_index(graph, pairs)}
    jaccard = {v: score for _, v, score in nx.jaccard_coefficient(graph, pairs)}

    out = []
    for other in candidates:
        shared = sorted(mine & set(graph.neighbors(other)))
        out.append({
            "source_entity_id": entity_id,
            "target_entity_id": other,
            "target_name": graph.nodes[other].get("name", str(other)),
            "adamic_adar": round(adamic.get(other, 0.0), 4),
            "jaccard": round(jaccard.get(other, 0.0), 4),
            "shared_neighbour_ids": shared,
            "shared_neighbour_names": [
                graph.nodes[s].get("name", str(s)) for s in shared
            ],
        })

    out.sort(key=lambda p: (p["adamic_adar"], p["jaccard"]), reverse=True)
    return out[:k]
