from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from sgtlib.imaging.image_processor import ImageProcessor


def _write_slice(folder: Path, name: str, value: int) -> Path:
    path = folder / name
    Image.fromarray(np.full((4, 4), value, dtype=np.uint8)).save(path)
    return path


def test_slice_stack_files_preserve_lexicographical_order_without_duplicates(tmp_path):
    _write_slice(tmp_path, "slice2.tif", 2)
    _write_slice(tmp_path, "slice10.tif", 10)
    _write_slice(tmp_path, "slice1.tif", 1)

    selected = tmp_path / "slice10.tif"
    files = ImageProcessor.get_slice_stack_files(str(tmp_path), str(selected))

    assert [Path(path).name for path in files] == [
        "slice1.tif",
        "slice10.tif",
        "slice2.tif",
    ]


def test_from_image_file_builds_one_three_dimensional_batch_from_slices(tmp_path):
    _write_slice(tmp_path, "slice0281.tif", 1)
    _write_slice(tmp_path, "slice0282.tif", 2)
    _write_slice(tmp_path, "slice0283.tif", 3)

    processor, _ = ImageProcessor.from_image_file(
        str(tmp_path / "slice0281.tif"), allow_auto_scale=False
    )

    assert len(processor.image_batches) == 1
    assert processor.selected_batch.is_2d is False
    assert len(processor.selected_batch.images) == 3
    assert [int(image.img_2d[0, 0, 0]) for image in processor.selected_batch.images] == [
        1,
        2,
        3,
    ]


def test_from_image_file_rejects_slice_stack_with_mismatched_dimensions(tmp_path):
    _write_slice(tmp_path, "slice0281.tif", 1)
    Image.fromarray(np.full((5, 4), 2, dtype=np.uint8)).save(tmp_path / "slice0282.tif")

    with pytest.raises(ValueError, match="same dimensions"):
        ImageProcessor.from_image_file(
            str(tmp_path / "slice0281.tif"), allow_auto_scale=False
        )


