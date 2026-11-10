from src.sgtlib.utils.config_loader import load_gtc_configs


def test_compass_metric_options_and_boundary_parameters_are_available():
    options = load_gtc_configs("")

    for option_id in (
        "compute_compass_nematic",
        "compute_compass_boundary_betweenness",
        "compute_compass_node_boundary_betweenness",
        "compute_compass_random_betweenness",
        "compute_compass_effective_resistance",
    ):
        assert options[option_id]["type"] == "gt-metric"
        assert options[option_id]["value"] == 0

    assert options["compass_boundary_axis"]["value"] == 0
    assert options["compass_r_j"]["value"] == 0.0
