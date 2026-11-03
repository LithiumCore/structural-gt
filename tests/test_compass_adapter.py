import networkx as nx
import numpy as np
import pytest

from src.sgtlib.compute.compass_adapter import CompassGraphAdapter


def test_conversion_preserves_vertex_identity_order_geometry_and_isolates():
    graph = nx.Graph()
    graph.add_node("fiber-A", o=np.array([2, 5]), pts=np.array([[2, 5]]))
    graph.add_node(17, o=np.array([8, 3]), pts=np.array([[7, 3], [8, 3]]))
    graph.add_edge(
        "fiber-A",
        17,
        pts=np.array([[2, 5], [4, 4], [8, 3]]),
        length=6.0,
        width=2.5,
        angle=35.0,
        weight=0.75,
    )
    graph.add_node(("isolated", 1), o=np.array([20, 20]))

    adapted = CompassGraphAdapter.from_networkx(graph)

    assert adapted.vcount() == 3
    assert adapted.ecount() == 1
    assert adapted.get_edgelist() == [(0, 1)]
    assert adapted.vs["source_id"] == ["fiber-A", 17, ("isolated", 1)]
    np.testing.assert_array_equal(adapted.vs[0]["o"], [2, 5])
    np.testing.assert_array_equal(adapted.vs[0]["pts"], [[2, 5]])
    np.testing.assert_array_equal(adapted.es[0]["pts"], [[2, 5], [4, 4], [8, 3]])
    assert adapted.es[0]["length"] == 6.0
    assert adapted.es[0]["width"] == 2.5
    assert adapted.es[0]["angle"] == 35.0
    assert adapted.es[0]["target_weight"] == 0.75
    assert "weight" not in adapted.es.attributes()
    assert "Conductance" not in adapted.es.attributes()


def test_conversion_allows_missing_optional_geometry_and_weights():
    graph = nx.Graph()
    graph.add_edge("left", "right")

    adapted = CompassGraphAdapter.from_networkx(graph)

    assert adapted.vcount() == 2
    assert adapted.ecount() == 1
    assert adapted.vs["source_id"] == ["left", "right"]
    assert "o" not in adapted.vs.attributes()
    assert "pts" not in adapted.es.attributes()
    assert "target_weight" not in adapted.es.attributes()


def test_conversion_rejects_directed_graphs():
    with pytest.raises(TypeError, match="undirected"):
        CompassGraphAdapter.from_networkx(nx.DiGraph([(1, 2)]))


def test_conversion_rejects_multigraphs():
    with pytest.raises(TypeError, match="parallel edges"):
        CompassGraphAdapter.from_networkx(nx.MultiGraph([(1, 2)]))


def test_conversion_preserves_identity_of_custom_node_ids():
    class NodeId:
        pass

    node_id = NodeId()
    graph = nx.Graph()
    graph.add_node(node_id)

    adapted = CompassGraphAdapter.from_networkx(graph)

    assert adapted.vs[0]["source_id"] is node_id


def test_conversion_copies_coordinate_arrays_without_mutating_source():
    graph = nx.Graph()
    node_points = np.array([[1, 2], [3, 4]])
    edge_points = np.array([[1, 2], [3, 4]])
    graph.add_node("a", pts=node_points)
    graph.add_node("b", pts=np.array([[5, 6]]))
    graph.add_edge("a", "b", pts=edge_points, weight=2.0)

    adapted = CompassGraphAdapter.from_networkx(graph)
    adapted.vs[0]["pts"][0, 0] = 99
    adapted.es[0]["pts"][0, 0] = 88

    assert graph.nodes["a"]["pts"][0, 0] == 1
    assert graph.edges["a", "b"]["pts"][0, 0] == 1
    assert graph.edges["a", "b"]["weight"] == 2.0
