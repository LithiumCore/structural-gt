"""COMPASS-compatible metrics operating directly on igraph graphs."""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence

import igraph as ig
import networkx as nx
import numpy as np


def _require_graph(graph: ig.Graph) -> ig.Graph:
    if not isinstance(graph, ig.Graph):
        raise TypeError("graph must be an igraph.Graph")
    return graph


def _weights(graph: ig.Graph, attribute: str | None) -> np.ndarray:
    if attribute is None:
        return np.ones(graph.ecount(), dtype=float)
    if attribute not in graph.es.attributes():
        raise ValueError(f"edge attribute '{attribute}' is not present")
    values = np.asarray(graph.es[attribute], dtype=float)
    if values.shape != (graph.ecount(),) or not np.all(np.isfinite(values)):
        raise ValueError(f"edge attribute '{attribute}' must contain finite weights")
    return values


def _networkx_graph(graph: ig.Graph, weight: str | None) -> nx.Graph:
    result = nx.Graph()
    result.add_nodes_from(range(graph.vcount()))
    values = _weights(graph, weight)
    for edge_index, (source, target) in enumerate(graph.get_edgelist()):
        result.add_edge(source, target, weight=float(values[edge_index]))
    return result


def _validate_boundaries(
    graph: ig.Graph,
    sources: Iterable[int],
    targets: Iterable[int],
) -> tuple[list[int], list[int]]:
    source_list = list(dict.fromkeys(int(value) for value in sources))
    target_list = list(dict.fromkeys(int(value) for value in targets))
    valid = set(range(graph.vcount()))
    if not source_list or not target_list:
        raise ValueError("source and target boundaries must contain vertices")
    if not set(source_list).issubset(valid) or not set(target_list).issubset(valid):
        raise ValueError("source and target boundaries contain invalid vertices")
    if set(source_list) & set(target_list):
        raise ValueError("source and target boundaries must not overlap")
    return source_list, target_list


def compute_boundary_betweenness(
    graph: ig.Graph,
    sources: Iterable[int],
    targets: Iterable[int],
    edge_weight: str | None = None,
) -> dict[str, np.ndarray]:
    """Compute COMPASS boundary edge and node betweenness values.

    The returned values are unnormalized, matching the underlying COMPASS
    subset routines. The caller can apply the published boundary
    normalization when it wants the scalar EBC_B convention.
    """
    graph = _require_graph(graph)
    source_list, target_list = _validate_boundaries(graph, sources, targets)
    nx_graph = _networkx_graph(graph, edge_weight)
    distance = "weight" if edge_weight is not None else None

    edge_values = nx.edge_betweenness_centrality_subset(
        nx_graph,
        source_list,
        target_list,
        normalized=False,
        weight=distance,
    )
    node_values = nx.betweenness_centrality_subset(
        nx_graph,
        source_list,
        target_list,
        normalized=False,
        weight=distance,
    )

    edge_result = np.zeros(graph.ecount(), dtype=float)
    for edge_index, (source, target) in enumerate(graph.get_edgelist()):
        edge_result[edge_index] = edge_values.get(
            (source, target), edge_values.get((target, source), 0.0)
        )
    return {
        "edge_betweenness": edge_result,
        "node_betweenness": np.asarray(
            [node_values[index] for index in range(graph.vcount())], dtype=float
        ),
    }


def compute_random_boundary_betweenness(
    graph: ig.Graph,
    sources: Iterable[int],
    targets: Iterable[int],
    edge_weight: str | None = None,
) -> dict[str, np.ndarray]:
    """Compute COMPASS linear and nonlinear random-walk boundary metrics."""
    graph = _require_graph(graph)
    source_list, target_list = _validate_boundaries(graph, sources, targets)
    weights = _weights(graph, edge_weight)
    n = graph.vcount()
    ghost = n

    adjacency = np.zeros((n + 1, n + 1), dtype=float)
    for edge_index, (source, target) in enumerate(graph.get_edgelist()):
        adjacency[source, target] += weights[edge_index]
        adjacency[target, source] += weights[edge_index]
    mean_weight = float(np.mean(weights)) if len(weights) else 1.0
    for target in target_list:
        adjacency[target, ghost] += mean_weight
        adjacency[ghost, target] += mean_weight

    laplacian = np.diag(adjacency.sum(axis=1)) - adjacency
    pseudoinverse = np.linalg.pinv(laplacian, hermitian=True)

    linear = np.zeros(graph.ecount(), dtype=float)
    for edge_index, (source, target) in enumerate(graph.get_edgelist()):
        value = 0.0
        for source_boundary in source_list:
            for target_boundary in target_list:
                voltage_source = (
                    pseudoinverse[source, source_boundary]
                    - pseudoinverse[source, target_boundary]
                )
                voltage_target = (
                    pseudoinverse[target, source_boundary]
                    - pseudoinverse[target, target_boundary]
                )
                value += abs(voltage_source - voltage_target) * adjacency[
                    source, target
                ]
        linear[edge_index] = value

    incoming = np.ones(len(source_list), dtype=float)
    voltage = np.zeros(n + 1, dtype=float)
    total_incoming = float(np.sum(incoming))
    for index in range(n + 1):
        voltage[index] = sum(
            pseudoinverse[index, source] * incoming_value
            for source, incoming_value in zip(source_list, incoming)
        )
        voltage[index] -= pseudoinverse[index, ghost] * total_incoming

    nonlinear = np.asarray(
        [
            abs(voltage[source] - voltage[target]) * adjacency[source, target]
            for source, target in graph.get_edgelist()
        ],
        dtype=float,
    )
    return {
        "linear_betweenness": linear,
        "nonlinear_betweenness": nonlinear,
    }


def vector_to_angle(vector: Sequence[float]) -> float:
    """Return the COMPASS 2D edge angle in degrees in the range [0, 180]."""
    delta_x, delta_y = vector[1], vector[0]
    if delta_x == 0 and delta_y == 0:
        return 0.0
    if delta_x == 0:
        return 90.0
    if delta_y == 0:
        return 0.0
    angle = math.degrees(math.atan(delta_y / delta_x))
    return float(angle if delta_x * delta_y > 0 else angle + 180)


def compute_nematic_metrics(
    graph: ig.Graph,
    dim: int | None = None,
) -> dict[str, np.ndarray | float | None]:
    """Compute COMPASS nematic outputs from edge endpoint coordinates."""
    graph = _require_graph(graph)
    if "pts" not in graph.es.attributes():
        raise ValueError("nematic metrics require edge 'pts' attributes")
    if dim is None:
        if "o" in graph.vs.attributes() and graph.vcount():
            dim = len(graph.vs[0]["o"])
        else:
            dim = 2
    if dim not in (2, 3):
        raise ValueError("dim must be 2 or 3")

    orientations = np.asarray(
        [np.asarray(edge["pts"])[0] - np.asarray(edge["pts"])[-1] for edge in graph.es],
        dtype=float,
    )
    if orientations.size == 0:
        orientations = np.empty((0, dim), dtype=float)
    else:
        orientations = orientations.reshape((-1, dim))

    nematic_orientations = orientations
    if dim == 2:
        nematic_orientations = np.hstack(
            (orientations, np.zeros((len(orientations), 1), dtype=float))
        )
    nonzero = np.linalg.norm(nematic_orientations, axis=1) > 0
    if not np.any(nonzero):
        raise ValueError("nematic metrics require at least one nonzero edge orientation")

    unit = nematic_orientations[nonzero] / np.linalg.norm(
        nematic_orientations[nonzero], axis=1, keepdims=True
    )
    identity = np.eye(3)
    tensor = np.mean(
        [1.5 * np.outer(vector, vector) - 0.5 * identity for vector in unit],
        axis=0,
    )
    eigenvalues, eigenvectors = np.linalg.eigh(tensor)
    largest = int(np.argmax(eigenvalues))
    angles = None
    if dim == 2:
        angles = np.asarray([vector_to_angle(vector) for vector in orientations])

    return {
        "order": float(eigenvalues[largest]),
        "tensor": tensor,
        "director": eigenvectors[:, largest],
        "orientations": orientations,
        "angles": angles,
    }


def compute_effective_resistance(
    graph: ig.Graph,
    sources: Iterable[int],
    targets: Iterable[int],
    r_j: float | str = 0.0,
    conductance_attribute: str | None = None,
) -> dict[str, np.ndarray | float | int]:
    """Compute COMPASS-style resistance, potentials, and Laplacian inverse."""
    graph = _require_graph(graph)
    source_list, target_list = _validate_boundaries(graph, sources, targets)
    working = graph.copy()
    weights = _weights(working, conductance_attribute)
    if r_j == "infinity":
        weights = np.ones(working.ecount(), dtype=float)
    conductance = float(np.mean(weights)) if len(weights) else 1.0

    source = working.vcount()
    sink = source + 1
    working.add_vertices(2)
    for vertex in source_list:
        working.add_edge(source, vertex, Conductance=conductance)
    for vertex in target_list:
        working.add_edge(sink, vertex, Conductance=conductance)

    edge_conductance = np.ones(working.ecount(), dtype=float)
    if working.ecount() > len(source_list) + len(target_list):
        edge_conductance[: graph.ecount()] = weights
    laplacian = np.asarray(working.laplacian(weights=edge_conductance))
    pseudoinverse = np.linalg.pinv(laplacian, hermitian=True)
    current = np.zeros(working.vcount(), dtype=float)
    current[source] = 1.0
    current[sink] = -1.0
    potentials = pseudoinverse @ current
    resistance = (
        pseudoinverse[source, source]
        + pseudoinverse[sink, sink]
        - 2 * pseudoinverse[source, sink]
    )
    return {
        "effective_resistance": float(resistance),
        "P": potentials,
        "Q": pseudoinverse,
        "source": source,
        "sink": sink,
    }


__all__ = [
    "compute_boundary_betweenness",
    "compute_effective_resistance",
    "compute_nematic_metrics",
    "compute_random_boundary_betweenness",
    "vector_to_angle",
]
