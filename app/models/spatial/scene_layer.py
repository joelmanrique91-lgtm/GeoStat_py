"""Logical scene layer contract used by 3D renderers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from .assay_intervals_3d import AssayIntervals3D
from .drillhole_trajectory import DrillholeTrajectory
from .point_cloud import PointCloudGeometry
from .surface_mesh import SurfaceMesh
from .volume_grid import VolumeGrid

LayerPayload = (
    PointCloudGeometry
    | tuple[DrillholeTrajectory, ...]
    | tuple[AssayIntervals3D, ...]
    | SurfaceMesh
    | VolumeGrid
)


@dataclass(frozen=True)
class SceneLayer:
    layer_id: str
    layer_type: Literal["point_cloud", "drillholes", "assay_intervals", "surface_mesh", "volume_grid"]
    visible: bool
    opacity: float
    color_by: str | None
    display_name: str
    payload: LayerPayload
    style: dict[str, object] = field(default_factory=dict)
