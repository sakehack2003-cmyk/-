from __future__ import annotations

from datetime import datetime
from typing import List, Tuple

from reportlab.lib.pagesizes import portrait
from reportlab.pdfgen import canvas

from app.models.project import ProjectState
from app.utils.units import mm_to_pt


Point2D = Tuple[float, float]


def _bbox(points: List[Point2D]) -> Tuple[float, float, float, float]:
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return min(xs), min(ys), max(xs), max(ys)


def _build_path(path_obj: canvas.Path, points: List[Point2D], offset_x: float, offset_y: float) -> None:
    if not points:
        return
    path_obj.moveTo(mm_to_pt(points[0][0] + offset_x), mm_to_pt(points[0][1] + offset_y))
    for x, y in points[1:]:
        path_obj.lineTo(mm_to_pt(x + offset_x), mm_to_pt(y + offset_y))
    path_obj.close()


def export_pdf(path: str, project: ProjectState, filename_label: str) -> None:
    outer = project.outline.outer
    if not outer:
        raise ValueError("外周がありません。")
    minx, miny, maxx, maxy = _bbox(outer)
    margin = project.params.margin_mm
    width_mm = (maxx - minx) + margin * 2
    height_mm = (maxy - miny) + margin * 2
    page_size = portrait((mm_to_pt(width_mm), mm_to_pt(height_mm)))
    c = canvas.Canvas(path, pagesize=page_size)
    c.setLineWidth(0.5)

    offset_x = margin - minx
    offset_y = margin - miny

    path_outer = c.beginPath()
    _build_path(path_outer, outer, offset_x, offset_y)
    c.drawPath(path_outer, stroke=1, fill=0)

    for hole in project.outline.holes:
        path_hole = c.beginPath()
        _build_path(path_hole, hole, offset_x, offset_y)
        c.drawPath(path_hole, stroke=1, fill=0)

    # Guides
    c.setLineWidth(0.3)
    c.line(mm_to_pt(offset_x), mm_to_pt(offset_y), mm_to_pt(offset_x + 100), mm_to_pt(offset_y))
    c.drawString(mm_to_pt(offset_x), mm_to_pt(offset_y - 5), "100mm")
    c.line(mm_to_pt(offset_x), mm_to_pt(offset_y), mm_to_pt(offset_x), mm_to_pt(offset_y + 20))
    c.line(mm_to_pt(offset_x - 5), mm_to_pt(offset_y + 10), mm_to_pt(offset_x + 5), mm_to_pt(offset_y + 10))

    # Notes
    c.setFont("Helvetica", 8)
    text_lines = [
        f"File: {filename_label}",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"Scale factor: {project.scale_factor:.4f}",
        f"threshold={project.params.threshold_mm}mm, z_band={project.params.z_band_mm}mm",
        f"alpha={project.params.alpha}, simplify={project.params.simplify_tol_mm}mm",
        f"offset_outer={project.params.offset_outer_mm}mm, offset_holes={project.params.offset_holes_mm}mm",
    ]
    text_y = offset_y + (maxy - miny) + margin - 10
    for line in text_lines:
        c.drawString(mm_to_pt(offset_x), mm_to_pt(text_y), line)
        text_y -= 4

    c.showPage()
    c.save()
