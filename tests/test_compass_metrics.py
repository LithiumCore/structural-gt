import numpy as np
import igraph as ig
import pytest

from src.sgtlib.compute.compass_metrics import (
    compute_boundary_betweenness,
    compute_effective_resistance,
    compute_nematic_metrics,
    compute_random_boundary_betweenness,
    vector_to_angle,
)


def _path_graph():
    graph = ig.Graph(n=4, edges=[(0, 1), (1, 2), (2, 3)])
    graph.vs["o"] = [[0, 0], [1, 0], [2, 0], [3, 0]]
    graph.es["pts"] = [
        [[0, 0], [1, 0]],
        [[1, 0], [2, 0]],
        [[2, 0], [3, 0]],
    ]
    return graph


def test_nematic_returns_compass_outputs_and_pads_2d_orientations():
    result = compute_nematic_metrics(_path_graph(), dim=2)

    assert result["orientations"].shape == (3, 2)
    assert result["tensor"].shape == (3, 3)
    assert result["director"].shape == (3,)
    assert result["angles"].tolist() == [0.0, 0.0, 0.0]
    assert result["order"] == pytest.approx(1.0)


def test_boundary_metrics_return_edge_and_node_arrays():
    result = compute_boundary_betweenness(_path_graph(), [0], [3])

    assert result["edge_betweenness"].shape == (3,)
    assert result["node_betweenness"].shape == (4,)
    np.testing.assert_allclose(result["edge_betweenness"], [1.0, 1.0, 1.0])


def test_random_boundary_metrics_and_resistance_do_not_mutate_graph():
    graph = _path_graph()
    original_vertices = graph.vcount()
    random_result = compute_random_boundary_betweenness(graph, [0], [3])
    resistance_result = compute_effective_resistance(graph, [0], [3])

    assert random_result["linear_betweenness"].shape == (3,)
    assert random_result["nonlinear_betweenness"].shape == (3,)
    assert resistance_result["effective_resistance"] > 0
    assert resistance_result["P"].shape == (6,)
    assert resistance_result["Q"].shape == (6, 6)
    assert graph.vcount() == original_vertices


def test_boundary_sets_must_be_nonempty_and_disjoint():
    graph = _path_graph()

    with pytest.raises(ValueError, match="must contain vertices"):
        compute_boundary_betweenness(graph, [], [3])
    with pytest.raises(ValueError, match="must not overlap"):
        compute_boundary_betweenness(graph, [1], [1])


def test_vector_to_angle_matches_compass_convention():
    assert vector_to_angle([1, 0]) == 90
    assert vector_to_angle([0, 1]) == 0
    assert vector_to_angle([1, -1]) == 135
