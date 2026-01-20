from __future__ import annotations

from typing import List, Tuple

from shapely.geometry import Polygon


Point2D = Tuple[float, float]


def apply_offsets(
    outer: List[Point2D],
    holes: List[List[Point2D]],
    offset_outer: float,
    offset_holes: float,
) -> Tuple[List[Point2D], List[List[Point2D]]]:
    poly = Polygon(outer, holes)
    if not poly.is_valid:
        poly = poly.buffer(0)
    if poly.is_empty:
        raise ValueError("ポリゴンが無効です。")
    outer_poly = poly.buffer(offset_outer)
    if outer_poly.is_empty:
        raise ValueError("外周オフセットに失敗しました。")
    outer_poly = max(outer_poly.geoms, key=lambda g: g.area) if hasattr(outer_poly, "geoms") else outer_poly
    new_outer = [(float(x), float(y)) for x, y in outer_poly.exterior.coords[:-1]]
    new_holes = []
    for hole in holes:
        hole_poly = Polygon(hole)
        hole_poly = hole_poly.buffer(offset_holes)
        if hole_poly.is_empty:
            raise ValueError("穴オフセットに失敗しました。")
        hole_poly = max(hole_poly.geoms, key=lambda g: g.area) if hasattr(hole_poly, "geoms") else hole_poly
        new_holes.append([(float(x), float(y)) for x, y in hole_poly.exterior.coords[:-1]])
    return new_outer, new_holes
