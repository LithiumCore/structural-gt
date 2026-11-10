import math

import igraph as ig
import networkx as nx
import pandas as pd
import pytest
import matplotlib.pyplot as plt

from src.sgtlib.compute.metric_comparison import (
    compute_compass_metrics,
    compute_metric_comparison,
)
from src.sgtlib.compute import compute_compass_metrics as exported_compass_metrics
from src.sgtlib.compute.graph_analyzer import GraphAnalyzer
from src.sgtlib.utils.config_loader import load_gtc_configs


def test_comparison_keeps_full_precision_and_exposes_betweenness_difference():
    graph = nx.path_graph(4)

    result = compute_metric_comparison(
        graph,
        ["average_node_betweenness", "density", "number_of_nodes"],
    ).set_index("Metric")

    assert result.loc["Number of Nodes", "Dickson"] == 4
    assert result.loc["Number of Nodes", "COMPASS"] == 4
    assert result.loc["Graph Density", "Absolute Difference"] == 0
    assert result.loc["Average Node Betweenness", "Dickson"] == pytest.approx(1 / 3)
    assert result.loc["Average Node Betweenness", "COMPASS"] == pytest.approx(1 / 12)
    assert result.loc["Average Node Betweenness", "Absolute Difference"] == pytest.approx(1 / 4)


def test_public_compass_api_computes_selected_metrics_on_igraph_graph():
    graph = ig.Graph(n=4, edges=[(0, 1), (1, 2), (2, 3)])

    result = compute_compass_metrics(
        graph,
        ["number_of_nodes", "density", "average_node_betweenness"],
    )

    assert result["number_of_nodes"] == 4
    assert result["density"] == pytest.approx(1 / 3)
    # StructuralGT.NodeBetweenness returns raw igraph betweenness values;
    # the COMPASS API's average is therefore 1 for a four-node path.
    assert result["average_node_betweenness"] == pytest.approx(1)
    assert exported_compass_metrics is compute_compass_metrics


def test_public_compass_api_uses_igraph_diameter_for_disconnected_graphs():
    result = compute_compass_metrics(ig.Graph(n=2), ["diameter"])

    assert result["diameter"] == 0


def test_disconnected_diameter_and_zero_baseline_relative_delta_are_undefined():
    graph = nx.empty_graph(2)

    result = compute_metric_comparison(graph, ["diameter", "density"]).set_index("Metric")

    assert math.isnan(result.loc["Diameter", "Dickson"])
    assert math.isnan(result.loc["Diameter", "Absolute Difference"])
    assert math.isnan(result.loc["Graph Density", "Relative Difference (%)"])


@pytest.mark.parametrize("graph", [nx.empty_graph(0), nx.empty_graph(1)])
def test_empty_and_singleton_graphs_return_rows_without_infinite_values(graph):
    result = compute_metric_comparison(
        graph,
        [
            "number_of_nodes",
            "number_of_edges",
            "diameter",
            "density",
            "average_degree",
            "average_clustering",
            "degree_assortativity",
            "average_closeness",
            "average_node_betweenness",
        ],
    )

    assert len(result) == 9
    assert not any(
        math.isinf(value)
        for value in result[["Dickson", "COMPASS", "Absolute Difference", "Relative Difference (%)"]]
        .to_numpy()
        .flat
        if not pd.isna(value)
    )


def test_only_requested_metrics_are_returned():
    result = compute_metric_comparison(nx.path_graph(3), ["number_of_edges"])

    assert result["Metric"].tolist() == ["Number of Edges"]


def test_existing_analyzer_uses_shared_dickson_formulas():
    class ImageProcessorStub:
        config_file = ""

    analyzer = GraphAnalyzer(ImageProcessorStub())
    analyzer.configs = load_gtc_configs("")
    for option in (
        "display_degree_histogram",
        "compute_network_diameter",
        "compute_graph_density",
        "compute_avg_clustering_coef",
        "compute_assortativity_coef",
        "display_betweenness_centrality_histogram",
        "display_closeness_centrality_histogram",
    ):
        analyzer.configs[option]["value"] = 1

    graph = nx.path_graph(4)
    nx.set_edge_attributes(graph, 0.0, "angle")
    result = analyzer.compute_gt_metrics(graph, save_histogram=False, silent=True)
    values = result.set_index("parameter")["value"]

    assert values["Average degree"] == 1.5
    assert values["Network diameter"] == 3
    assert values["Graph density"] == 0.5
    assert values["Average betweenness centrality"] == pytest.approx(0.33333)


def test_comparison_results_are_written_as_csv(tmp_path):
    class Network:
        def get_filenames(self):
            return "sample", str(tmp_path)

    class Analyzer:
        ntwk_p = Network()
        plot_figures = [plt.figure()]
        results_df = None
        weighted_results_df = None
        scaling_results = {}
        comparison_results = pd.DataFrame(
            [["Graph Density", 0.5, 0.4, 0.1, 20.0]],
            columns=["Metric", "Dickson", "COMPASS", "Absolute Difference", "Relative Difference (%)"],
        )

    # Avoid rendering unrelated figures while exercising the file writer.
    analyzer = Analyzer()
    assert GraphAnalyzer.write_to_pdf(analyzer)

    written = pd.read_csv(tmp_path / "sample_SGT_compass_comparison.csv")
    assert written.columns.tolist() == Analyzer.comparison_results.columns.tolist()
    assert written.loc[0, "Absolute Difference"] == pytest.approx(0.1)
