"""Paired Dickson and COMPASS calculations for unweighted graph metrics.

COMPASS-side formulas follow the current ``compass-stc/StructuralGT`` igraph
calculators (Size, Degree, Clustering, Assortativity, Closeness, and
NodeBetweenness); this module keeps those calculations isolated from the
existing Dickson implementation and does not import the COMPASS package.
"""

from __future__ import annotations

import math
import numbers
import warnings
from collections.abc import Iterable

import igraph as ig
import networkx as nx
import numpy as np
import pandas as pd

from .compass_adapter import CompassGraphAdapter

COMPARISON_COLUMNS = [
    "Metric",
    "Dickson",
    "COMPASS",
    "Absolute Difference",
    "Relative Difference (%)",
]


def _mean(values) -> float:
    return float(np.mean(values)) if len(values) else math.nan


def _assortativity(graph, *, compass: bool = False):
    """Return degree assortativity while silencing expected undefined warnings."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        return (
            graph.assortativity_degree()
            if compass
            else nx.degree_assortativity_coefficient(graph)
        )


_METRIC_LABELS = {
    "number_of_nodes": "Number of Nodes",
    "number_of_edges": "Number of Edges",
    "diameter": "Diameter",
    "density": "Graph Density",
    "average_degree": "Average Degree",
    "average_clustering": "Average Clustering Coefficient",
    "degree_assortativity": "Degree Assortativity",
    "average_closeness": "Average Closeness",
    "average_node_betweenness": "Average Node Betweenness",
}


def _selected_values(graph, keys, metric_functions):
    values = {}
    for key in keys:
        try:
            values[key] = metric_functions[key](graph)
        except (nx.NetworkXError, ig.InternalError, ArithmeticError, ValueError):
            values[key] = math.nan
    return values


def dickson_metric_value(graph: nx.Graph, key: str, cache: dict | None = None):
    """Return one raw Dickson result, before the analyzer's display rounding."""
    if key not in _DICKSON_FUNCTIONS:
        raise ValueError(f"Unsupported comparison metric: {key}")
    cache_key = (id(graph), key)
    if cache is not None and cache_key in cache:
        return cache[cache_key]
    try:
        value = _DICKSON_FUNCTIONS[key](graph)
    except (nx.NetworkXError, ig.InternalError, ArithmeticError, ValueError):
        value = math.nan
    if cache is not None:
        cache[cache_key] = value
    return value


_DICKSON_FUNCTIONS = {
    "number_of_nodes": lambda g: nx.number_of_nodes(g),
    "number_of_edges": lambda g: nx.number_of_edges(g),
    "diameter": lambda g: nx.diameter(g) if g.number_of_nodes() and nx.is_connected(g) else math.nan,
    "density": lambda g: nx.density(g),
    "average_degree": lambda g: _mean([degree for _, degree in g.degree()]),
    "average_clustering": lambda g: _mean(list(nx.clustering(g).values())),
    "degree_assortativity": lambda g: _assortativity(g),
    "average_closeness": lambda g: _mean(list(nx.closeness_centrality(g).values())),
    "average_node_betweenness": lambda g: _mean(list(nx.betweenness_centrality(g).values())),
}


def _compass_functions():
    """Return formulas matching the StructuralGT COMPASS API exactly."""
    return {
        "number_of_nodes": lambda g: g.vcount(),
        "number_of_edges": lambda g: g.ecount(),
        "diameter": lambda g: g.diameter(),
        "density": lambda g: g.density(),
        "average_degree": lambda g: _mean(g.strength(weights=None)),
        "average_clustering": lambda g: _mean(g.transitivity_local_undirected(mode="zero")),
        "degree_assortativity": lambda g: _assortativity(g, compass=True),
        "average_closeness": lambda g: _mean(g.closeness()),
        "average_node_betweenness": lambda g: _mean(g.betweenness()),
    }


def _comparison_compass_functions():
    """Return comparison-only COMPASS formulas.

    These preserve the existing comparison table's normalization and
    undefined-value policy. They are intentionally separate from the public
    API, which mirrors StructuralGT's compute classes exactly.
    """
    return {
        "number_of_nodes": lambda g: g.vcount(),
        "number_of_edges": lambda g: g.ecount(),
        "diameter": lambda g: (
            g.diameter() if g.vcount() and g.is_connected() else math.nan
        ),
        "density": lambda g: g.density(),
        "average_degree": lambda g: _mean(g.degree()),
        "average_clustering": lambda g: _mean(
            g.transitivity_local_undirected(mode="zero")
        ),
        "degree_assortativity": lambda g: _assortativity(g, compass=True),
        "average_closeness": lambda g: _mean(g.closeness()),
        "average_node_betweenness": lambda g: (
            _mean(g.betweenness()) / (g.vcount() * (g.vcount() - 1))
            if g.vcount() > 1
            else math.nan
        ),
    }


def compute_compass_metrics(
    graph: ig.Graph,
    selected_metrics: Iterable[str],
) -> dict[str, float | int]:
    """Calculate selected COMPASS metrics directly on an igraph graph.

    This is the public entry point for using the COMPASS-side calculations
    without running the Dickson comparison pipeline.  The supplied graph is
    treated as read-only and is expected to have the vertex and edge
    semantics produced by :class:`CompassGraphAdapter`.
    """
    if not isinstance(graph, ig.Graph):
        raise TypeError("graph must be an igraph.Graph")

    keys = list(dict.fromkeys(selected_metrics))
    unknown = set(keys).difference(_METRIC_LABELS)
    if unknown:
        raise ValueError(f"Unsupported COMPASS metrics: {', '.join(sorted(unknown))}")
    if not keys:
        return {}

    return _selected_values(graph, keys, _compass_functions())


def _finite_or_nan(value):
    if value is None:
        return math.nan
    if isinstance(value, numbers.Integral):
        return int(value)
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return math.nan
    return numeric if math.isfinite(numeric) else math.nan


def compute_metric_comparison(
    graph: nx.Graph,
    selected_metrics: Iterable[str],
    *,
    dickson_cache: dict | None = None,
) -> pd.DataFrame:
    """Calculate selected metric pairs on the same supplied graph."""
    keys = list(dict.fromkeys(selected_metrics))
    unknown = set(keys).difference(_METRIC_LABELS)
    if unknown:
        raise ValueError(f"Unsupported comparison metrics: {', '.join(sorted(unknown))}")
    if not keys:
        return pd.DataFrame(columns=COMPARISON_COLUMNS)

    dickson = {
        key: dickson_metric_value(graph, key, dickson_cache) for key in keys
    }
    compass_graph = CompassGraphAdapter.from_networkx(graph)
    compass = _selected_values(
        compass_graph,
        keys,
        _comparison_compass_functions(),
    )
    rows = []
    for key in keys:
        left = _finite_or_nan(dickson[key])
        right = _finite_or_nan(compass[key])
        if math.isfinite(left) and math.isfinite(right):
            difference = abs(left - right)
            relative = difference / abs(left) * 100 if left != 0 else math.nan
        else:
            difference = relative = math.nan
        rows.append(
            {
                "Metric": _METRIC_LABELS[key],
                "Dickson": left,
                "COMPASS": right,
                "Absolute Difference": difference,
                "Relative Difference (%)": relative,
            }
        )
    return pd.DataFrame(rows, columns=COMPARISON_COLUMNS)


__all__ = [
    "COMPARISON_COLUMNS",
    "compute_compass_metrics",
    "compute_metric_comparison",
    "dickson_metric_value",
]
