from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import open3d as o3d

from app.utils.geom import make_plane_basis, project_points


@dataclass
class ProjectionResult:
    points_2d_mm: np.ndarray
    origin_mm: np.ndarray
    basis_u: np.ndarray
    basis_v: np.ndarray
    normal: np.ndarray


def extract_floor_points(
    pcd: o3d.geometry.PointCloud,
    plane_model: np.ndarray,
    threshold_mm: float,
    z_band_mm: float,
    scale_factor: float,
) -> np.ndarray:
    points = np.asarray(pcd.points)
    a, b, c, d = plane_model
    normal = np.array([a, b, c], dtype=float)
    normal /= np.linalg.norm(normal)
    distances = (points @ normal + d)
    distances_mm = distances * scale_factor
    mask = np.abs(distances_mm) <= threshold_mm
    band_mask = np.abs(distances_mm) <= z_band_mm
    selected = mask & band_mask
    return points[selected]


def project_to_2d(points: np.ndarray, plane_model: np.ndarray, scale_factor: float) -> ProjectionResult:
    a, b, c, d = plane_model
    normal = np.array([a, b, c], dtype=float)
    normal /= np.linalg.norm(normal)
    origin = -d * normal
    u, v, n = make_plane_basis(normal)
    points_mm = points * scale_factor
    origin_mm = origin * scale_factor
    points_2d = project_points(points_mm, origin_mm, u, v)
    return ProjectionResult(
        points_2d_mm=points_2d,
        origin_mm=origin_mm,
        basis_u=u,
        basis_v=v,
        normal=n,
    )
