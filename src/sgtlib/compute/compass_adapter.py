"""Adapt Dickson's extracted NetworkX graphs for COMPASS calculations."""

from __future__ import annotations

from copy import deepcopy

import igraph as ig
import networkx as nx


class CompassGraphAdapter:
    """Convert an undirected Dickson graph to an independent igraph graph.

    Vertex insertion order is retained and the original NetworkX node key is
    stored as ``source_id``. The node geometry attributes ``o`` and ``pts``
    and edge geometry attributes ``pts``, ``length``, ``width``, and ``angle``
    are copied when present. A source edge ``weight`` is exposed only as
    ``target_weight``; it is not assumed to have COMPASS weight semantics.

    The adapter handles exactly the graph it receives. It does not choose a
    connected component or calculate missing geometry or weights.
    """

    _VERTEX_ATTRIBUTES = ("o", "pts")
    _EDGE_ATTRIBUTES = ("pts", "length", "width", "angle")

    @classmethod
    def from_networkx(cls, graph: nx.Graph) -> ig.Graph:
        """Return an independent igraph copy of a simple undirected graph.

        Args:
            graph: A simple undirected NetworkX graph. Node order is retained.

        Raises:
            TypeError: If ``graph`` is directed or contains parallel edges.
        """
        if isinstance(graph, nx.DiGraph):
            raise TypeError("graph must be undirected")
        if not isinstance(graph, nx.Graph):
            raise TypeError("graph must be a NetworkX Graph")
        if graph.is_multigraph():
            raise TypeError("graph must not contain parallel edges")

        nodes = list(graph.nodes(data=True))
        node_indices = {node_id: index for index, (node_id, _) in enumerate(nodes)}
        edges = list(graph.edges(data=True))

        adapted = ig.Graph(
            n=len(nodes),
            edges=[
                (node_indices[source], node_indices[target])
                for source, target, _ in edges
            ],
            directed=False,
        )

        adapted.vs["source_id"] = [node_id for node_id, _ in nodes]
        for attribute in cls._VERTEX_ATTRIBUTES:
            if any(attribute in data for _, data in nodes):
                adapted.vs[attribute] = [
                    deepcopy(data.get(attribute)) for _, data in nodes
                ]

        for attribute in cls._EDGE_ATTRIBUTES:
            if any(attribute in data for _, _, data in edges):
                adapted.es[attribute] = [
                    deepcopy(data.get(attribute)) for _, _, data in edges
                ]

        if any("weight" in data for _, _, data in edges):
            adapted.es["target_weight"] = [
                deepcopy(data.get("weight")) for _, _, data in edges
            ]

        return adapted
