from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple


Point2D = Tuple[float, float]


@dataclass
class OutlineData:
    outer: List[Point2D] = field(default_factory=list)
    holes: List[List[Point2D]] = field(default_factory=list)


@dataclass
class ProjectParams:
    voxel_mm: float = 10.0
    threshold_mm: float = 5.0
    z_band_mm: float = 3.0
    alpha: float = 15.0
    simplify_tol_mm: float = 2.0
    offset_outer_mm: float = 2.0
    offset_holes_mm: float = 0.0
    margin_mm: float = 20.0


@dataclass
class ProjectState:
    input_path: Optional[str] = None
    scale_factor: float = 1.0
    scale_calibrated: bool = False
    chosen_plane_index: Optional[int] = None
    plane_models: List[List[float]] = field(default_factory=list)
    params: ProjectParams = field(default_factory=ProjectParams)
    outline: OutlineData = field(default_factory=OutlineData)
    floor_points_2d: List[Point2D] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "input_path": self.input_path,
            "scale_factor": self.scale_factor,
            "scale_calibrated": self.scale_calibrated,
            "chosen_plane_index": self.chosen_plane_index,
            "plane_models": self.plane_models,
            "params": {
                "voxel_mm": self.params.voxel_mm,
                "threshold_mm": self.params.threshold_mm,
                "z_band_mm": self.params.z_band_mm,
                "alpha": self.params.alpha,
                "simplify_tol_mm": self.params.simplify_tol_mm,
                "offset_outer_mm": self.params.offset_outer_mm,
                "offset_holes_mm": self.params.offset_holes_mm,
                "margin_mm": self.params.margin_mm,
            },
            "outline": {
                "outer": self.outline.outer,
                "holes": self.outline.holes,
            },
            "floor_points_2d": self.floor_points_2d,
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "ProjectState":
        params_payload = payload.get("params", {})
        params = ProjectParams(
            voxel_mm=params_payload.get("voxel_mm", 10.0),
            threshold_mm=params_payload.get("threshold_mm", 5.0),
            z_band_mm=params_payload.get("z_band_mm", 3.0),
            alpha=params_payload.get("alpha", 15.0),
            simplify_tol_mm=params_payload.get("simplify_tol_mm", 2.0),
            offset_outer_mm=params_payload.get("offset_outer_mm", 2.0),
            offset_holes_mm=params_payload.get("offset_holes_mm", 0.0),
            margin_mm=params_payload.get("margin_mm", 20.0),
        )
        outline_payload = payload.get("outline", {})
        outline = OutlineData(
            outer=[tuple(pt) for pt in outline_payload.get("outer", [])],
            holes=[[tuple(pt) for pt in ring] for ring in outline_payload.get("holes", [])],
        )
        return cls(
            input_path=payload.get("input_path"),
            scale_factor=payload.get("scale_factor", 1.0),
            scale_calibrated=payload.get("scale_calibrated", False),
            chosen_plane_index=payload.get("chosen_plane_index"),
            plane_models=payload.get("plane_models", []),
            params=params,
            outline=outline,
            floor_points_2d=[tuple(pt) for pt in payload.get("floor_points_2d", [])],
        )
