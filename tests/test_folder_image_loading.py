from pathlib import Path

from sgtlib.apps.controllers.base_controller import BaseController


class RecordingController(BaseController):
    def __init__(self):
        super().__init__()
        self.created_paths = []

    def create_sgt_object(self, file_path: str, out_dir: str = "") -> bool:
        self.created_paths.append(Path(file_path).name)
        self._sgt_objs[Path(file_path).stem] = object()
        return True


def test_slice_folder_creates_one_native_stack_object(tmp_path):
    for name in ("slice0281.tif", "slice0282.tif", "slice0283.tif"):
        (tmp_path / name).touch()

    controller = RecordingController()

    assert controller.add_multiple_images(str(tmp_path)) is True
    assert controller.created_paths == ["slice0281.tif"]


def test_ordinary_image_folder_keeps_one_object_per_image(tmp_path):
    for name in ("first.png", "second.png"):
        (tmp_path / name).touch()

    controller = RecordingController()

    assert controller.add_multiple_images(str(tmp_path)) is True
    assert controller.created_paths == ["first.png", "second.png"]


def test_empty_folder_is_rejected(tmp_path):
    controller = RecordingController()

    assert controller.add_multiple_images(str(tmp_path)) is False
    assert controller.created_paths == []
