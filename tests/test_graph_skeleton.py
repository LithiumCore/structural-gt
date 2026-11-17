import numpy as np

from sgtlib.networks.graph_skeleton import GraphSkeleton


def test_three_dimensional_skeleton_skips_two_dimensional_node_merge():
    image = np.zeros((5, 5, 5), dtype=np.uint8)
    image[:, 2, 2] = 255
    configs = {
        "merge_nearby_nodes": {"value": 1},
        "remove_disconnected_segments": {"value": 0},
        "prune_dangling_edges": {"value": 1},
    }

    graph_skeleton = GraphSkeleton(image, configs=configs, is_2d=False)

    assert graph_skeleton.skeleton.shape == image.shape
    assert graph_skeleton.skeleton_3d.shape == image.shape
