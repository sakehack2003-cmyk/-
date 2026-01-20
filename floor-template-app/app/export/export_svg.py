from __future__ import annotations

from datetime import datetime
from typing import List, Tuple

import svgwrite

from app.models.project import ProjectState


Point2D = Tuple[float, float]


def _bbox(points: List[Point2D]) -> Tuple[float, float, float, float]:
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return min(xs), min(ys), max(xs), max(ys)


def export_svg(path: str, project: ProjectState, filename_label: str) -> None:
    outer = project.outline.outer
    if not outer:
        raise ValueError("外周がありません。")
    minx, miny, maxx, maxy = _bbox(outer)
    margin = project.params.margin_mm
    width_mm = (maxx - minx) + margin * 2
    height_mm = (maxy - miny) + margin * 2

    dwg = svgwrite.Drawing(path, size=(f"{width_mm}mm", f"{height_mm}mm"), profile="tiny")
    dwg.viewbox(0, 0, width_mm, height_mm)

    offset_x = margin - minx
    offset_y = margin - miny

    cut_outer = dwg.g(id="CUT_OUTER", fill="none", stroke="black", stroke_width=0.2)
    cut_outer.add(dwg.polygon([(x + offset_x, y + offset_y) for x, y in outer]))
    dwg.add(cut_outer)

    cut_holes = dwg.g(id="CUT_HOLES", fill="none", stroke="black", stroke_width=0.2)
    for hole in project.outline.holes:
        cut_holes.add(dwg.polygon([(x + offset_x, y + offset_y) for x, y in hole]))
    dwg.add(cut_holes)

    guide = dwg.g(id="GUIDE", fill="none", stroke="black", stroke_width=0.1)
    guide.add(dwg.line(start=(offset_x, offset_y), end=(offset_x + 100, offset_y)))
    guide.add(dwg.text("100mm", insert=(offset_x, offset_y - 2), font_size=3))
    guide.add(dwg.line(start=(offset_x, offset_y), end=(offset_x, offset_y + 20)))
    guide.add(dwg.line(start=(offset_x - 2, offset_y + 10), end=(offset_x + 2, offset_y + 10)))
    dwg.add(guide)

    text = dwg.g(id="TEXT", fill="black")
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
        text.add(dwg.text(line, insert=(offset_x, text_y), font_size=3))
        text_y -= 4
    dwg.add(text)

    dwg.save()
