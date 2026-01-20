from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import numpy as np
import open3d as o3d
from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSplitter,
    QStatusBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from app.export.export_pdf import export_pdf
from app.export.export_svg import export_svg
from app.io.importer import import_geometry
from app.io.project_store import load_project, save_project
from app.models.project import ProjectState
from app.pipeline.floor_detect import colorize_planes, detect_floor_planes
from app.pipeline.offset import apply_offsets
from app.pipeline.outline import generate_outline
from app.pipeline.preprocess import downsample_point_cloud
from app.pipeline.project_to_2d import extract_floor_points, project_to_2d
from app.ui.dialogs import ask_distance_mm, show_error, show_info, show_warning
from app.ui.view2d import View2D


class Worker(QObject):
    finished = Signal(object)
    error = Signal(str)

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs

    def run(self) -> None:
        try:
            result = self.fn(*self.args, **self.kwargs)
            self.finished.emit(result)
        except Exception as exc:  # noqa: BLE001
            self.error.emit(str(exc))


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Floor Template App (MVP)")
        self.resize(1400, 900)
        self.setAcceptDrops(True)

        self.project = ProjectState()
        self.raw_geometry: Optional[o3d.geometry.Geometry] = None
        self.pcd: Optional[o3d.geometry.PointCloud] = None
        self.planes = []

        self._init_ui()

    def _init_ui(self) -> None:
        toolbar = QToolBar()
        self.addToolBar(toolbar)

        import_btn = QPushButton("Import")
        import_btn.clicked.connect(self.import_file)
        toolbar.addWidget(import_btn)

        save_btn = QPushButton("Save Project")
        save_btn.clicked.connect(self.save_project)
        toolbar.addWidget(save_btn)

        load_btn = QPushButton("Load Project")
        load_btn.clicked.connect(self.load_project)
        toolbar.addWidget(load_btn)

        export_pdf_btn = QPushButton("Export PDF")
        export_pdf_btn.clicked.connect(self.export_pdf)
        toolbar.addWidget(export_pdf_btn)

        export_svg_btn = QPushButton("Export SVG")
        export_svg_btn.clicked.connect(self.export_svg)
        toolbar.addWidget(export_svg_btn)

        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)

        splitter = QSplitter()
        left_panel = self._build_left_panel()
        right_panel = self._build_right_panel()
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(1, 2)

        main_layout.addWidget(splitter)
        main_layout.addWidget(self._build_param_panel())

        self.setCentralWidget(main_widget)
        self.setStatusBar(QStatusBar())

    def _build_left_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        self.label_stats = QLabel("No data")
        layout.addWidget(self.label_stats)

        self.detect_btn = QPushButton("Detect Floor")
        self.detect_btn.clicked.connect(self.detect_floor)
        layout.addWidget(self.detect_btn)

        self.generate_btn = QPushButton("Generate Outline")
        self.generate_btn.clicked.connect(self.generate_outline)
        layout.addWidget(self.generate_btn)

        self.open3d_btn = QPushButton("Open 3D Viewer")
        self.open3d_btn.clicked.connect(self.show_open3d)
        layout.addWidget(self.open3d_btn)

        plane_group = QGroupBox("Plane Candidates")
        plane_layout = QVBoxLayout(plane_group)
        self.plane_buttons = []
        self.plane_button_group = QButtonGroup(self)
        for i in range(3):
            btn = QRadioButton(f"Plane {i + 1}")
            btn.setEnabled(False)
            self.plane_buttons.append(btn)
            self.plane_button_group.addButton(btn, i)
            plane_layout.addWidget(btn)
        self.plane_button_group.buttonClicked.connect(self.select_plane)
        layout.addWidget(plane_group)

        layout.addStretch()
        return panel

    def _build_right_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        self.view2d = View2D()
        self.view2d.scalePointsSelected.connect(self.on_scale_points)
        self.view2d.geometryChanged.connect(self.on_geometry_changed)
        layout.addWidget(self.view2d)

        controls = QHBoxLayout()
        scale_btn = QPushButton("Scale Calibrate")
        scale_btn.clicked.connect(lambda: self.view2d.set_mode("scale"))
        controls.addWidget(scale_btn)

        circle_btn = QPushButton("Add Hole: Circle")
        circle_btn.clicked.connect(lambda: self.view2d.set_mode("add_circle"))
        controls.addWidget(circle_btn)

        rect_btn = QPushButton("Add Hole: Rect")
        rect_btn.clicked.connect(lambda: self.view2d.set_mode("add_rect"))
        controls.addWidget(rect_btn)

        poly_btn = QPushButton("Add Hole: Polygon")
        poly_btn.clicked.connect(lambda: self.view2d.set_mode("add_poly"))
        controls.addWidget(poly_btn)

        select_btn = QPushButton("Select/Move")
        select_btn.clicked.connect(lambda: self.view2d.set_mode("select"))
        controls.addWidget(select_btn)

        layout.addLayout(controls)
        return panel

    def _build_param_panel(self) -> QWidget:
        panel = QWidget()
        layout = QFormLayout(panel)

        self.voxel_spin = QDoubleSpinBox()
        self.voxel_spin.setRange(1.0, 100.0)
        self.voxel_spin.setValue(self.project.params.voxel_mm)
        layout.addRow("Voxel (mm)", self.voxel_spin)

        self.threshold_spin = QDoubleSpinBox()
        self.threshold_spin.setRange(0.1, 50.0)
        self.threshold_spin.setValue(self.project.params.threshold_mm)
        layout.addRow("Threshold (mm)", self.threshold_spin)

        self.z_band_spin = QDoubleSpinBox()
        self.z_band_spin.setRange(0.1, 50.0)
        self.z_band_spin.setValue(self.project.params.z_band_mm)
        layout.addRow("Z Band (mm)", self.z_band_spin)

        self.alpha_spin = QDoubleSpinBox()
        self.alpha_spin.setRange(1.0, 100.0)
        self.alpha_spin.setValue(self.project.params.alpha)
        layout.addRow("Alpha (mm)", self.alpha_spin)

        self.simplify_spin = QDoubleSpinBox()
        self.simplify_spin.setRange(0.1, 50.0)
        self.simplify_spin.setValue(self.project.params.simplify_tol_mm)
        layout.addRow("Simplify Tol (mm)", self.simplify_spin)

        self.offset_outer_spin = QDoubleSpinBox()
        self.offset_outer_spin.setRange(-50.0, 50.0)
        self.offset_outer_spin.setValue(self.project.params.offset_outer_mm)
        layout.addRow("Outer Offset (mm)", self.offset_outer_spin)

        self.offset_holes_spin = QDoubleSpinBox()
        self.offset_holes_spin.setRange(-50.0, 50.0)
        self.offset_holes_spin.setValue(self.project.params.offset_holes_mm)
        layout.addRow("Holes Offset (mm)", self.offset_holes_spin)

        self.margin_spin = QDoubleSpinBox()
        self.margin_spin.setRange(0.0, 200.0)
        self.margin_spin.setValue(self.project.params.margin_mm)
        layout.addRow("Margin (mm)", self.margin_spin)

        self.grid_check = QCheckBox("Grid On/Off")
        self.grid_check.setChecked(True)
        self.grid_check.toggled.connect(self.view2d.set_grid_enabled)
        layout.addRow(self.grid_check)

        return panel

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        urls = event.mimeData().urls()
        if urls:
            self.load_file(urls[0].toLocalFile())

    def import_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Import", "", "Point Cloud (*.ply *.obj *.stl *.glb)")
        if not path:
            return
        self.load_file(path)

    def load_file(self, path: str) -> None:
        try:
            result = import_geometry(path)
        except ValueError as exc:
            show_error(self, "Import Error", str(exc))
            return
        self.project.input_path = path
        self.raw_geometry = result.geometry
        if isinstance(result.geometry, o3d.geometry.PointCloud):
            self.pcd = result.geometry
        else:
            self.pcd = None
        bbox_min = result.bbox_min
        bbox_max = result.bbox_max
        self.label_stats.setText(
            f"Points: {result.point_count}\nBBox: {bbox_min} - {bbox_max}"
        )
        if result.warning:
            show_warning(self, "Import Warning", result.warning)

    def _update_params_from_ui(self) -> None:
        self.project.params.voxel_mm = float(self.voxel_spin.value())
        self.project.params.threshold_mm = float(self.threshold_spin.value())
        self.project.params.z_band_mm = float(self.z_band_spin.value())
        self.project.params.alpha = float(self.alpha_spin.value())
        self.project.params.simplify_tol_mm = float(self.simplify_spin.value())
        self.project.params.offset_outer_mm = float(self.offset_outer_spin.value())
        self.project.params.offset_holes_mm = float(self.offset_holes_spin.value())
        self.project.params.margin_mm = float(self.margin_spin.value())

    def detect_floor(self) -> None:
        if not self.pcd:
            show_error(self, "Detect Floor", "点群を読み込んでください。")
            return
        self._update_params_from_ui()
        self.statusBar().showMessage("Detecting floor planes...")

        def task():
            down = downsample_point_cloud(self.pcd, self.project.params.voxel_mm)
            planes = detect_floor_planes(down)
            return down, planes

        self.run_in_thread(task, self.on_detect_done)

    def on_detect_done(self, result) -> None:
        down, planes = result
        self.pcd = down
        self.planes = planes
        self.project.plane_models = [p.model.tolist() for p in planes]
        for idx, btn in enumerate(self.plane_buttons):
            btn.setEnabled(idx < len(planes))
            if idx == 0 and len(planes) > 0:
                btn.setChecked(True)
                self.project.chosen_plane_index = 0
        colored = colorize_planes(self.pcd, planes)
        o3d.visualization.draw_geometries([colored])
        self.statusBar().showMessage("Floor detection complete", 5000)

    def show_open3d(self) -> None:
        if not self.pcd:
            show_error(self, "Open3D", "点群を読み込んでください。")
            return
        o3d.visualization.draw_geometries([self.pcd])

    def select_plane(self) -> None:
        self.project.chosen_plane_index = self.plane_button_group.checkedId()

    def generate_outline(self) -> None:
        if not self.pcd or self.project.chosen_plane_index is None:
            show_error(self, "Generate Outline", "点群と平面を選択してください。")
            return
        self._update_params_from_ui()
        plane = np.array(self.project.plane_models[self.project.chosen_plane_index])
        self.statusBar().showMessage("Generating outline...")

        def task():
            floor_points = extract_floor_points(
                self.pcd,
                plane,
                self.project.params.threshold_mm,
                self.project.params.z_band_mm,
                self.project.scale_factor,
            )
            proj = project_to_2d(floor_points, plane, self.project.scale_factor)
            outer, holes = generate_outline(
                proj.points_2d_mm,
                self.project.params.alpha,
                self.project.params.simplify_tol_mm,
            )
            return proj.points_2d_mm, outer, holes

        self.run_in_thread(task, self.on_outline_done)

    def on_outline_done(self, result) -> None:
        points_2d, outer, holes = result
        self.project.floor_points_2d = [(float(x), float(y)) for x, y in points_2d]
        self.project.outline.outer = outer
        self.project.outline.holes = holes
        self.view2d.set_points(self.project.floor_points_2d)
        self.view2d.load_geometry(outer, holes)
        self.statusBar().showMessage("Outline generated", 5000)

    def on_scale_points(self, pt1, pt2) -> None:
        distance_measured = ((pt2[0] - pt1[0]) ** 2 + (pt2[1] - pt1[1]) ** 2) ** 0.5
        if distance_measured <= 0:
            show_error(self, "Scale", "距離が0です。")
            return
        actual = ask_distance_mm(self, "Scale Calibrate", "実測距離(mm)を入力")
        if actual is None:
            return
        factor = actual / distance_measured
        self.apply_scale_factor(factor)
        self.project.scale_calibrated = True
        show_info(self, "Scale Calibrate", f"Scale factor updated: {self.project.scale_factor:.4f}")

    def apply_scale_factor(self, factor: float) -> None:
        self.project.scale_factor *= factor
        if self.project.outline.outer:
            self.project.outline.outer = [(x * factor, y * factor) for x, y in self.project.outline.outer]
            self.project.outline.holes = [
                [(x * factor, y * factor) for x, y in ring] for ring in self.project.outline.holes
            ]
        if self.project.floor_points_2d:
            self.project.floor_points_2d = [(x * factor, y * factor) for x, y in self.project.floor_points_2d]
        self.view2d.set_points(self.project.floor_points_2d)
        self.view2d.load_geometry(self.project.outline.outer, self.project.outline.holes)

    def on_geometry_changed(self, outer, holes) -> None:
        self.project.outline.outer = [(float(x), float(y)) for x, y in outer]
        self.project.outline.holes = [[(float(x), float(y)) for x, y in ring] for ring in holes]

    def export_pdf(self) -> None:
        if not self.project.outline.outer:
            show_error(self, "Export", "外周がありません。")
            return
        if not self.project.scale_calibrated:
            if QMessageBox.warning(
                self,
                "Scale Warning",
                "スケール校正が未実施です。続行しますか?",
                QMessageBox.Yes | QMessageBox.No,
            ) == QMessageBox.No:
                return
        path, _ = QFileDialog.getSaveFileName(self, "Export PDF", "", "PDF (*.pdf)")
        if not path:
            return
        self._update_params_from_ui()
        try:
            outer, holes = apply_offsets(
                self.project.outline.outer,
                self.project.outline.holes,
                self.project.params.offset_outer_mm,
                self.project.params.offset_holes_mm,
            )
            original_outer = self.project.outline.outer
            original_holes = self.project.outline.holes
            self.project.outline.outer = outer
            self.project.outline.holes = holes
            export_pdf(path, self.project, Path(self.project.input_path or path).name)
            self.project.outline.outer = original_outer
            self.project.outline.holes = original_holes
        except ValueError as exc:
            show_error(self, "Export Error", str(exc))
            return
        show_info(self, "Export", f"PDF exported: {path}")

    def export_svg(self) -> None:
        if not self.project.outline.outer:
            show_error(self, "Export", "外周がありません。")
            return
        if not self.project.scale_calibrated:
            if QMessageBox.warning(
                self,
                "Scale Warning",
                "スケール校正が未実施です。続行しますか?",
                QMessageBox.Yes | QMessageBox.No,
            ) == QMessageBox.No:
                return
        path, _ = QFileDialog.getSaveFileName(self, "Export SVG", "", "SVG (*.svg)")
        if not path:
            return
        self._update_params_from_ui()
        try:
            outer, holes = apply_offsets(
                self.project.outline.outer,
                self.project.outline.holes,
                self.project.params.offset_outer_mm,
                self.project.params.offset_holes_mm,
            )
            original_outer = self.project.outline.outer
            original_holes = self.project.outline.holes
            self.project.outline.outer = outer
            self.project.outline.holes = holes
            export_svg(path, self.project, Path(self.project.input_path or path).name)
            self.project.outline.outer = original_outer
            self.project.outline.holes = original_holes
        except ValueError as exc:
            show_error(self, "Export Error", str(exc))
            return
        show_info(self, "Export", f"SVG exported: {path}")

    def save_project(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Save Project", "", "Project (*.json)")
        if not path:
            return
        self._update_params_from_ui()
        save_project(path, self.project)
        show_info(self, "Save", f"Project saved: {path}")

    def load_project(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Load Project", "", "Project (*.json)")
        if not path:
            return
        self.project = load_project(path)
        self._sync_ui_from_project()
        self.view2d.set_points(self.project.floor_points_2d)
        self.view2d.load_geometry(self.project.outline.outer, self.project.outline.holes)
        if self.project.input_path and os.path.exists(self.project.input_path):
            self.load_file(self.project.input_path)
        show_info(self, "Load", f"Project loaded: {path}")

    def _sync_ui_from_project(self) -> None:
        self.voxel_spin.setValue(self.project.params.voxel_mm)
        self.threshold_spin.setValue(self.project.params.threshold_mm)
        self.z_band_spin.setValue(self.project.params.z_band_mm)
        self.alpha_spin.setValue(self.project.params.alpha)
        self.simplify_spin.setValue(self.project.params.simplify_tol_mm)
        self.offset_outer_spin.setValue(self.project.params.offset_outer_mm)
        self.offset_holes_spin.setValue(self.project.params.offset_holes_mm)
        self.margin_spin.setValue(self.project.params.margin_mm)
        for idx, btn in enumerate(self.plane_buttons):
            btn.setEnabled(idx < len(self.project.plane_models))
            btn.setChecked(idx == self.project.chosen_plane_index)

    def run_in_thread(self, fn, callback) -> None:
        thread = QThread(self)
        worker = Worker(fn)
        worker.moveToThread(thread)
        worker.finished.connect(callback)
        worker.error.connect(lambda msg: show_error(self, "Error", msg))
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.started.connect(worker.run)
        thread.start()
