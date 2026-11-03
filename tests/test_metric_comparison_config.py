from src.sgtlib.utils.config_loader import load_gtc_configs


def test_compass_comparison_options_default_to_off():
    options = load_gtc_configs("")
    comparison_options = {
        key: value for key, value in options.items() if key.startswith("compare_compass_")
    }

    assert len(comparison_options) == 9
    assert all(option["type"] == "gt-metric" for option in comparison_options.values())
    assert all(option["value"] == 0 for option in comparison_options.values())
    assert "Compare with COMPASS: Average Node Betweenness" in {
        option["text"] for option in comparison_options.values()
    }
