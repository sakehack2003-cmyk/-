from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple
import math

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsPathItem,
    QGraphicsScene,
    QGraphicsView,
)


Point2D = Tuple[float, float]


class VertexHandle(QGraphicsEllipseItem):
    def __init__(self, view: "View2D", ring_index: int, vertex_index: int, is_outer: bool):
        super().__init__(-2.5, -2.5, 5, 5)
        self.view = view
        self.ring_index = ring_index
        self.vertex_index = vertex_index
        self.is_outer = is_outer
        self.setBrush(QBrush(Qt.yellow))
        self.setPen(QPen(Qt.black))
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setZValue(10)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange:
            pos = value
            self.view.update_vertex(self.is_outer, self.ring_index, self.vertex_index, pos)
        return super().itemChange(change, value)


@dataclass
class ViewState:
    outer: List[Point2D]
    holes: List[List[Point2D]]


class View2D(QGraphicsView):
    scalePointsSelected = Signal(tuple, tuple)
    geometryChanged = Signal(list, list)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setRenderHint(QPainter.Antialiasing)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.outer: List[Point2D] = []
        self.holes: List[List[Point2D]] = []
        self.points_items: List[QGraphicsEllipseItem] = []
        self.path_outer = QGraphicsPathItem()
        self.path_holes = []
        self.scene.addItem(self.path_outer)
        self.handles: List[VertexHandle] = []
        self.mode = "select"
        self.temp_poly: List[Point2D] = []
        self.temp_path_item = QGraphicsPathItem()
        self.temp_path_item.setPen(QPen(Qt.darkGray, 0.4, Qt.DashLine))
        self.scene.addItem(self.temp_path_item)
        self.scale_points: List[Point2D] = []
        self.grid_enabled = True
        self.setBackgroundBrush(QBrush(Qt.white))

    def set_grid_enabled(self, enabled: bool) -> None:
        self.grid_enabled = enabled
        self.viewport().update()

    def drawBackground(self, painter, rect):
        super().drawBackground(painter, rect)
        if not self.grid_enabled:
            return
        painter.save()
        painter.setPen(QPen(Qt.lightGray, 0.0))
        grid = 50
        left = int(rect.left()) - (int(rect.left()) % grid)
        top = int(rect.top()) - (int(rect.top()) % grid)
        for x in range(left, int(rect.right()), grid):
            painter.drawLine(x, rect.top(), x, rect.bottom())
        for y in range(top, int(rect.bottom()), grid):
            painter.drawLine(rect.left(), y, rect.right(), y)
        painter.restore()

    def clear_view(self) -> None:
        self.outer = []
        self.holes = []
        self.scene.clear()
        self.path_outer = QGraphicsPathItem()
        self.scene.addItem(self.path_outer)
        self.temp_path_item = QGraphicsPathItem()
        self.temp_path_item.setPen(QPen(Qt.darkGray, 0.4, Qt.DashLine))
        self.scene.addItem(self.temp_path_item)
        self.handles = []
        self.points_items = []

    def set_points(self, points: List[Point2D]) -> None:
        for item in self.points_items:
            self.scene.removeItem(item)
        self.points_items = []
        pen = QPen(Qt.gray)
        for x, y in points:
            item = QGraphicsEllipseItem(-0.5, -0.5, 1.0, 1.0)
            item.setPen(pen)
            item.setBrush(QBrush(Qt.gray))
            item.setPos(QPointF(x, y))
            item.setZValue(1)
            self.scene.addItem(item)
            self.points_items.append(item)

    def load_geometry(self, outer: List[Point2D], holes: List[List[Point2D]]) -> None:
        self.outer = list(outer)
        self.holes = [list(ring) for ring in holes]
        self._rebuild_paths()

    def _rebuild_paths(self) -> None:
        self.path_outer.setPen(QPen(Qt.black, 0.6))
        self._update_paths_only()

        for handle in self.handles:
            self.scene.removeItem(handle)
        self.handles = []
        for idx, pt in enumerate(self.outer):
            handle = VertexHandle(self, 0, idx, True)
            handle.setPos(QPointF(*pt))
            self.scene.addItem(handle)
            self.handles.append(handle)
        for ring_index, hole in enumerate(self.holes):
            for idx, pt in enumerate(hole):
                handle = VertexHandle(self, ring_index, idx, False)
                handle.setPos(QPointF(*pt))
                self.scene.addItem(handle)
                self.handles.append(handle)

    def _update_paths_only(self) -> None:
        path = QPainterPath()
        if self.outer:
            path.moveTo(QPointF(*self.outer[0]))
            for pt in self.outer[1:]:
                path.lineTo(QPointF(*pt))
            path.closeSubpath()
        self.path_outer.setPath(path)

        for item in self.path_holes:
            self.scene.removeItem(item)
        self.path_holes = []
        for hole in self.holes:
            hole_path = QPainterPath()
            if hole:
                hole_path.moveTo(QPointF(*hole[0]))
                for pt in hole[1:]:
                    hole_path.lineTo(QPointF(*pt))
                hole_path.closeSubpath()
            hole_item = QGraphicsPathItem(hole_path)
            hole_item.setPen(QPen(Qt.black, 0.4))
            self.scene.addItem(hole_item)
            self.path_holes.append(hole_item)

    def update_vertex(self, is_outer: bool, ring_index: int, vertex_index: int, pos: QPointF) -> None:
        if is_outer:
            if vertex_index < len(self.outer):
                self.outer[vertex_index] = (pos.x(), pos.y())
        else:
            if ring_index < len(self.holes) and vertex_index < len(self.holes[ring_index]):
                self.holes[ring_index][vertex_index] = (pos.x(), pos.y())
        self._update_paths_only()
        self.geometryChanged.emit(self.outer, self.holes)

    def set_mode(self, mode: str) -> None:
        self.mode = mode
        self.temp_poly = []
        self.scale_points = []
        self.temp_path_item.setPath(QPainterPath())

    def mousePressEvent(self, event) -> None:
        pos = self.mapToScene(event.position().toPoint())
        if self.mode == "add_circle":
            self.temp_poly = [(pos.x(), pos.y())]
        elif self.mode == "add_rect":
            self.temp_poly = [(pos.x(), pos.y())]
        elif self.mode == "add_poly":
            self.temp_poly.append((pos.x(), pos.y()))
            self._update_temp_path()
        elif self.mode == "scale":
            self.scale_points.append((pos.x(), pos.y()))
            if len(self.scale_points) == 2:
                self.scalePointsSelected.emit(self.scale_points[0], self.scale_points[1])
                self.scale_points = []
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        pos = self.mapToScene(event.position().toPoint())
        if self.mode in {"add_circle", "add_rect"} and self.temp_poly:
            start = self.temp_poly[0]
            end = (pos.x(), pos.y())
            if self.mode == "add_circle":
                radius = ((end[0] - start[0]) ** 2 + (end[1] - start[1]) ** 2) ** 0.5
                points = []
                for i in range(32):
                    angle = i / 32.0 * math.pi * 2
                    points.append((start[0] + radius * math.cos(angle), start[1] + radius * math.sin(angle)))
                self.holes.append(points)
            else:
                rect = QRectF(QPointF(*start), QPointF(*end)).normalized()
                points = [
                    (rect.left(), rect.top()),
                    (rect.right(), rect.top()),
                    (rect.right(), rect.bottom()),
                    (rect.left(), rect.bottom()),
                ]
                self.holes.append(points)
            self.temp_poly = []
            self._rebuild_paths()
            self.geometryChanged.emit(self.outer, self.holes)
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        if self.mode == "add_poly" and len(self.temp_poly) >= 3:
            self.holes.append(list(self.temp_poly))
            self.temp_poly = []
            self._rebuild_paths()
            self.geometryChanged.emit(self.outer, self.holes)
        super().mouseDoubleClickEvent(event)

    def _update_temp_path(self) -> None:
        path = QPainterPath()
        if self.temp_poly:
            path.moveTo(QPointF(*self.temp_poly[0]))
            for pt in self.temp_poly[1:]:
                path.lineTo(QPointF(*pt))
        self.temp_path_item.setPath(path)
