from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
import open3d as o3d


@dataclass
class ImportResult:
    geometry: o3d.geometry.Geometry
    point_count: int
    bbox_min: np.ndarray
    bbox_max: np.ndarray
    warning: Optional[str] = None


SUPPORTED_MESH = {".obj", ".stl", ".glb"}


def import_geometry(path: str) -> ImportResult:
    file_path = Path(path)
    ext = file_path.suffix.lower()
    if ext == ".ply":
        pcd = o3d.io.read_point_cloud(str(file_path))
        if pcd.is_empty():
            raise ValueError("PLYに点が含まれていません。")
        bbox = pcd.get_axis_aligned_bounding_box()
        return ImportResult(
            geometry=pcd,
            point_count=len(pcd.points),
            bbox_min=np.asarray(bbox.min_bound),
            bbox_max=np.asarray(bbox.max_bound),
        )
    if ext in SUPPORTED_MESH:
        warning = "MVPではメッシュ読み込みは未対応です。PLYを使用してください。"
        mesh = o3d.geometry.TriangleMesh()
        return ImportResult(
            geometry=mesh,
            point_count=0,
            bbox_min=np.zeros(3),
            bbox_max=np.zeros(3),
            warning=warning,
        )
    raise ValueError("対応していない拡張子です。PLY/OBJ/STL/GLBのみ対応。")
