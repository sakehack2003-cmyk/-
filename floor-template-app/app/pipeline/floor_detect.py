from __future__ import annotations

from dataclasses import dataclass
from typing import List

import numpy as np
import open3d as o3d


@dataclass
class PlaneCandidate:
    model: np.ndarray
    inliers: np.ndarray


def detect_floor_planes(pcd: o3d.geometry.PointCloud, max_planes: int = 3) -> List[PlaneCandidate]:
    remaining = pcd
    planes: List[PlaneCandidate] = []
    for _ in range(max_planes):
        if len(remaining.points) < 50:
            break
        model, inliers = remaining.segment_plane(
            distance_threshold=0.01,
            ransac_n=3,
            num_iterations=1000,
        )
        if len(inliers) < 100:
            break
        inliers = np.asarray(inliers)
        planes.append(PlaneCandidate(model=np.array(model), inliers=inliers))
        remaining = remaining.select_by_index(inliers, invert=True)
    return planes


def colorize_planes(pcd: o3d.geometry.PointCloud, planes: List[PlaneCandidate]) -> o3d.geometry.PointCloud:
    colored = pcd.clone()
    colors = np.tile(np.array([[0.6, 0.6, 0.6]]), (len(colored.points), 1))
    palette = [
        np.array([1.0, 0.2, 0.2]),
        np.array([0.2, 1.0, 0.2]),
        np.array([0.2, 0.2, 1.0]),
    ]
    for idx, candidate in enumerate(planes):
        if idx >= len(palette):
            break
        colors[candidate.inliers] = palette[idx]
    colored.colors = o3d.utility.Vector3dVector(colors)
    return colored
