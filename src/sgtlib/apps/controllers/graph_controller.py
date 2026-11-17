# SPDX-License-Identifier: GNU GPL v3
"""
Pyside6 (GUI components) controller class for graph extraction and computation.
"""

import logging

from PySide6.QtCore import QObject, Slot

from ...compute.graph_analyzer import GraphAnalyzer
from ...utils.sgt_utils import ProgressData
from ..models.checkbox_model import CheckBoxModel
from ..models.table_model import TableModel
from ..models.tree_model import TreeModel


class GraphController(QObject):
    def __init__(self, controller_obj, parent: QObject | None = None):
        super().__init__(parent)
        self._ctrl = controller_obj
        self._ovito_dialog = None
        self._ovito_pipeline = None
        self._ovito_viewport_window = None
        self._ovito_spacing_modifier = None

        # Create Models
        self.graphPropsModel = TableModel([])
        self.graphComputeModel = TableModel([])
        self.graphComparisonModel = TableModel([])
        self.gtcScalingModel = CheckBoxModel([])
        self.gteTreeModel = TreeModel([])
        self.gtcListModel = CheckBoxModel([])
        self.exportGraphModel = CheckBoxModel([])

        # Attach listener for syncing models
        self._ctrl.syncModelSignal.connect(self.synchronize_graph_models)

    def start_task(self, msg: str = "please wait..."):
        """Activate the wait flag and send a wait signal."""
        self._ctrl.wait_msg = msg
        self._ctrl.wait_flag = True

    def stop_task(self):
        """Deactivate the wait flag and send a wait signal."""
        self._ctrl.wait_msg = ""
        self._ctrl.wait_flag = False

    @Slot(str, result=str)
    def get_compass_parameter(self, parameter_id: str) -> str:
        """Return a selected COMPASS GUI parameter as text."""
        sgt_obj = self._ctrl.get_selected_sgt_obj()
        if sgt_obj is None or parameter_id not in sgt_obj.configs:
            return ""
        return str(sgt_obj.configs[parameter_id].get("value", ""))

    @Slot(str, str, result=bool)
    def set_compass_parameter(self, parameter_id: str, value: str) -> bool:
        """Validate and store a COMPASS GUI parameter."""
        sgt_obj = self._ctrl.get_selected_sgt_obj()
        if sgt_obj is None or parameter_id not in sgt_obj.configs:
            return False
        try:
            parsed = int(value) if parameter_id == "compass_boundary_axis" else float(value)
        except (TypeError, ValueError):
            self._ctrl.showAlertSignal.emit(
                "Invalid COMPASS parameter",
                f"{sgt_obj.configs[parameter_id]['text']} must be numeric.",
            )
            return False
        if parameter_id == "compass_boundary_axis" and parsed not in (0, 1, 2):
            self._ctrl.showAlertSignal.emit(
                "Invalid COMPASS parameter", "Boundary axis must be 0, 1, or 2."
            )
            return False
        sgt_obj.configs[parameter_id]["value"] = parsed
        return True

    def synchronize_graph_models(self, sgt_obj: GraphAnalyzer):
        """
            Reload graph configuration selections and controls from saved dict to QML gui_mcw.
        Args:
            sgt_obj: a GraphAnalyzer object with all saved user-selected configurations.

        Returns:

        """
        if sgt_obj is None:
            return

        try:
            # Models Auto-update with saved sgt_obj configs. No need to re-assign!
            ntwk_p = sgt_obj.ntwk_p
            graph_obj = ntwk_p.graph_obj
            option_gte = graph_obj.configs
            options_gtc = sgt_obj.configs

            graph_options = [
                v for v in option_gte.values() if v["type"] == "graph-extraction"
            ]
            file_options = [
                v for v in option_gte.values() if v["type"] == "file-options"
            ]
            compute_options = [
                v for v in options_gtc.values() if v["type"] == "gt-metric"
            ]
            scaling_options = [
                v for v in options_gtc.values() if v["type"] == "scaling-param"
            ]

            self.gteTreeModel.reset_data(graph_options)
            self.exportGraphModel.reset_data(file_options)
            self.gtcListModel.reset_data(compute_options)
            self.gtcScalingModel.reset_data(scaling_options)

            self.graphPropsModel.reset_data(graph_obj.props)
            self.graphComputeModel.reset_data(sgt_obj.props)
            comparison_data = (
                sgt_obj.comparison_results.values.tolist()
                if sgt_obj.comparison_results is not None
                else []
            )
            self.graphComparisonModel.reset_data(comparison_data)
        except Exception as err:
            logging.exception("Fatal Error: %s", err, extra={"user": "SGT Logs"})
            self._ctrl.showAlertSignal.emit(
                "Fatal Error",
                "Error re-loading image configurations! Close app and try again.",
            )

    @Slot(result=bool)
    def display_graph(self):
        if len(self._ctrl.sgt_objs) <= 0:
            return False

        sgt_obj = self._ctrl.get_selected_sgt_obj()
        if sgt_obj is None:
            return False

        if sgt_obj.ntwk_p.graph_obj.img_ntwk is None:
            return False

        return sgt_obj.ntwk_p.selected_batch_view == "graph"

    @Slot(bool)
    def reload_graph_image(self, only_giant_graph=False):
        if self._ctrl.wait_flag:
            logging.info(
                "Please Wait: Another GT task is running!", extra={"user": "SGT Logs"}
            )
            self._ctrl.showAlertSignal.emit(
                "Please Wait", "Another GT task is running!"
            )
            return

        try:
            self.start_task()
            sgt_obj = self._ctrl.get_selected_sgt_obj()
            sel_img_batch = sgt_obj.ntwk_p.selected_batch
            sgt_obj.ntwk_p.draw_graph_image(
                sel_img_batch, show_giant_only=only_giant_graph
            )
            self._ctrl.changeImageSignal.emit()
            self.stop_task()
        except Exception as err:
            self.stop_task()
            logging.exception(
                "Error reloading graph image: %s", err, extra={"user": "SGT Logs"}
            )

    @Slot()
    def load_graph_simulation(self):
        """Render and visualize OVITO graph network simulation."""
        try:
            # Import libraries
            from ovito import scene
            from ovito.gui import create_qwidget
            from ovito.io import import_file
            from ovito.modifiers import (
                AffineTransformationModifier,
                AssignColorModifier,
            )
            from ovito.vis import Viewport
            from PySide6.QtCore import Qt
            from PySide6.QtWidgets import (
                QDialog,
                QHBoxLayout,
                QLabel,
                QSlider,
                QVBoxLayout,
            )

            # Close an earlier viewer before replacing its scene pipeline.
            if self._ovito_dialog is not None:
                self._ovito_dialog.close()
                self._ovito_dialog = None

            # Clear any existing scene
            for p_line in list(scene.pipelines):
                p_line.remove_from_scene()

            # Create OVITO data pipeline
            sgt_obj = self._ctrl.get_selected_sgt_obj()
            h, w = sgt_obj.ntwk_p.graph_obj.img_ntwk.shape[:2]
            pipeline = import_file(sgt_obj.ntwk_p.graph_obj.gsd_file)
            spacing_modifier = AffineTransformationModifier(
                relative_mode=True,
                operate_on={"particles"},
                transformation=[[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0]],
            )
            pipeline.modifiers.append(spacing_modifier)
            pipeline.modifiers.append(
                AssignColorModifier(
                    operate_on="particles", color=(0.12, 0.68, 0.9)
                )
            )
            pipeline.modifiers.append(
                AssignColorModifier(operate_on="bonds", color=(1, 1, 1))
            )
            pipeline.add_to_scene()

            vp = Viewport(type=Viewport.Type.Perspective, camera_dir=(2, 1, -1))
            vp.zoom_all((w, h))  # width, height

            dialog = QDialog(parent=self._ctrl.qml_app.activeWindow())
            dialog.setWindowTitle("3D Graph Visualization")
            dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
            dialog_layout = QVBoxLayout(dialog)

            viewport_window = create_qwidget(vp, parent=dialog)
            viewport_widget = getattr(viewport_window, "widget", viewport_window)
            viewport_widget.setFixedSize(w, h)
            dialog_layout.addWidget(viewport_widget)

            spacing_controls = QHBoxLayout()
            spacing_controls.addWidget(QLabel("Layer spacing"))
            spacing_slider = QSlider(Qt.Orientation.Horizontal)
            spacing_slider.setRange(25, 1500)
            spacing_slider.setValue(100)
            spacing_slider.setToolTip("Adjust the distance between all graph layers")
            spacing_controls.addWidget(spacing_slider, 1)
            spacing_label = QLabel("1.00×")
            spacing_label.setMinimumWidth(52)
            spacing_label.setAlignment(Qt.AlignmentFlag.AlignRight)
            spacing_controls.addWidget(spacing_label)
            dialog_layout.addLayout(spacing_controls)

            def update_layer_spacing(value: int) -> None:
                multiplier = value / 100.0
                spacing_modifier.transformation = [
                    [multiplier, 0, 0, 0],
                    [0, 1, 0, 0],
                    [0, 0, 1, 0],
                ]
                spacing_label.setText(f"{multiplier:.2f}×")

            spacing_slider.valueChanged.connect(update_layer_spacing)

            self._ovito_dialog = dialog
            self._ovito_pipeline = pipeline
            self._ovito_viewport_window = viewport_window
            self._ovito_spacing_modifier = spacing_modifier

            def release_viewer(_result: int) -> None:
                if pipeline in scene.pipelines:
                    pipeline.remove_from_scene()
                if self._ovito_pipeline is pipeline:
                    self._ovito_dialog = None
                    self._ovito_pipeline = None
                    self._ovito_viewport_window = None
                    self._ovito_spacing_modifier = None

            dialog.finished.connect(release_viewer)
            dialog.resize(w, h + spacing_slider.sizeHint().height() + 24)
            dialog.show()
        except Exception as e:
            logging.exception(
                f"Graph Simulation Error: {e}", extra={"user": "SGT Logs"}
            )

    @Slot()
    def export_graph_to_file(self):
        """Export graph data and save as a file."""
        if self._ctrl.wait_flag:
            logging.info(
                "Please Wait: Another GT task is running!", extra={"user": "SGT Logs"}
            )
            self._ctrl.showAlertSignal.emit(
                "Please Wait", "Another GT task is running!"
            )
            return
        self._ctrl.handle_progress_update(
            ProgressData(percent=0, sender="GT", message="Exporting Graph Data...")
        )
        try:
            if self._ctrl.get_selected_sgt_obj().ntwk_p.selected_batch.is_graph_only:
                return

            self._ctrl.handle_progress_update(
                ProgressData(percent=20, sender="GT", message="Exporting Graph Data...")
            )
            self.start_task()
            sgt_obj = self._ctrl.get_selected_sgt_obj()
            self._ctrl.submit_job(1, "Export-Graph", (sgt_obj.ntwk_p,), True)
        except Exception as err:
            logging.exception(
                "Unable to Export Graph: " + str(err), extra={"user": "SGT Logs"}
            )
            self._ctrl.handle_finished(
                1,
                False,
                ["Unable to Export Graph", "Error exporting graph to file. Try again."],
            )

    @Slot()
    def run_extract_graph(self):
        """Retrieve settings from the model and send to Python."""

        if self._ctrl.wait_flag:
            logging.info(
                "Please Wait: Another GT task is running!", extra={"user": "SGT Logs"}
            )
            self._ctrl.showAlertSignal.emit(
                "Please Wait", "Another GT task is running!"
            )
            return

        try:
            self.start_task()
            sgt_obj = self._ctrl.get_selected_sgt_obj()
            self._ctrl.submit_job(1, "Extract-Graph", (sgt_obj.ntwk_p,), True)
        except Exception as err:
            self.stop_task()
            logging.exception(
                "Graph Extraction Error: %s", err, extra={"user": "SGT Logs"}
            )
            self._ctrl.handle_progress_update(
                ProgressData(
                    type="error",
                    sender="GT",
                    message="Fatal error occurred! Close the app and try again.",
                )
            )
            self._ctrl.handle_finished(
                1,
                False,
                [
                    "Graph Extraction Error",
                    (
                        "Fatal error while trying to extract graph. "
                        "Close the app and try again."
                    ),
                ],
            )

    @Slot(float)
    def rate_graph(self, rating: float):
        """Rate extracted graph on a scale of 1-10"""
        if self._ctrl.wait_flag:
            logging.info(
                "Please Wait: Another GT task running!", extra={"user": "SGT Logs"}
            )
            self._ctrl.showAlertSignal.emit(
                "Please Wait", "Another GT task is running!"
            )
            return

        try:
            self.start_task()
            sgt_obj = self._ctrl.get_selected_sgt_obj()
            self._ctrl.submit_job(
                1,
                "Rate-Graph",
                (
                    rating,
                    sgt_obj.ntwk_p,
                ),
                True,
            )
        except Exception as err:
            self.stop_task()
            logging.info("Rate Graph Error: " + str(err), extra={"user": "SGT Logs"})

    @Slot()
    def run_graph_analyzer(self):
        """Retrieve settings from the model and send to Python."""
        if self._ctrl.wait_flag:
            logging.info(
                "Please Wait: Another GT task is running!", extra={"user": "SGT Logs"}
            )
            self._ctrl.showAlertSignal.emit(
                "Please Wait", "Another GT task is running!"
            )
            return

        try:
            self.start_task()
            sgt_obj = self._ctrl.get_selected_sgt_obj()
            self._ctrl.submit_job(1, "Compute-GT", (sgt_obj,), True)
        except Exception as err:
            self.stop_task()
            logging.exception(
                "GT Computation Error: %s", err, extra={"user": "SGT Logs"}
            )
            self._ctrl.handle_progress_update(
                ProgressData(
                    type="error",
                    sender="GT",
                    message="Fatal error occurred! Close the app and try again.",
                )
            )
            self._ctrl.handle_finished(
                1,
                False,
                [
                    "GT Computation Error",
                    (
                        "Fatal error while trying calculate GT parameters. "
                        "Close the app and try again."
                    ),
                ],
            )

    @Slot()
    def run_multi_graph_analyzer(self):
        """"""
        if self._ctrl.wait_flag:
            logging.info(
                "Please Wait: Another GT task is running!", extra={"user": "SGT Logs"}
            )
            self._ctrl.showAlertSignal.emit(
                "Please Wait", "Another GT task is running!"
            )
            return

        try:
            self.start_task()
            # Update Configs
            self._ctrl.replicate_sgt_configs()
            # Start Background Process
            self._ctrl.submit_job(1, "Compute-Multi-GT", (self._ctrl.sgt_objs,), True)
        except Exception as err:
            self.stop_task()
            logging.exception(
                "GT Computation Error: %s", err, extra={"user": "SGT Logs"}
            )
            self._ctrl.handle_progress_update(
                ProgressData(
                    type="error",
                    sender="GT",
                    message="Fatal error occurred! Close the app and try again.",
                )
            )
            self._ctrl.handle_finished(
                1,
                False,
                [
                    "GT Computation Error",
                    (
                        "Fatal error while trying calculate GT parameters. "
                        "Close the app and try again."
                    ),
                ],
            )
