from __future__ import annotations

from typing import List, Tuple

import numpy as np
from shapely.geometry import MultiPolygon, Point, Polygon
from shapely.ops import unary_union


Point2D = Tuple[float, float]


def alpha_shape(points: np.ndarray, alpha: float) -> Polygon:
    if len(points) < 3:
        raise ValueError("点数が少なすぎます。")
    buffers = [Point(float(x), float(y)).buffer(alpha) for x, y in points]
    unioned = unary_union(buffers)
    if isinstance(unioned, Polygon):
        return unioned
    if isinstance(unioned, MultiPolygon):
        largest = max(unioned.geoms, key=lambda g: g.area)
        return largest
    raise ValueError("輪郭生成に失敗しました。")


def simplify_polygon(poly: Polygon, tolerance: float) -> Polygon:
    return poly.simplify(tolerance, preserve_topology=True)


def polygon_to_coords(poly: Polygon) -> Tuple[List[Point2D], List[List[Point2D]]]:
    exterior = [(float(x), float(y)) for x, y in poly.exterior.coords[:-1]]
    holes = []
    for interior in poly.interiors:
        holes.append([(float(x), float(y)) for x, y in interior.coords[:-1]])
    return exterior, holes


def generate_outline(points_2d: np.ndarray, alpha: float, simplify_tol: float) -> Tuple[List[Point2D], List[List[Point2D]]]:
    poly = alpha_shape(points_2d, alpha)
    if simplify_tol > 0:
        poly = simplify_polygon(poly, simplify_tol)
    if not poly.is_valid:
        poly = poly.buffer(0)
    if poly.is_empty:
        raise ValueError("輪郭が空になりました。")
    return polygon_to_coords(poly)
