from __future__ import annotations

import open3d as o3d


def downsample_point_cloud(pcd: o3d.geometry.PointCloud, voxel_mm: float) -> o3d.geometry.PointCloud:
    voxel_m = voxel_mm / 1000.0
    return pcd.voxel_down_sample(voxel_m)
