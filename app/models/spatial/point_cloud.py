"""Typed geometry contract for point-cloud rendering layers."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PointCloudGeometry:
    points_xyz: tuple[tuple[float, float, float], ...]
    color_values: tuple[float, ...]
    color_mode: str
    color_label: str
    color_tick_positions: tuple[float, ...] = ()
    color_tick_labels: tuple[str, ...] = ()
    source_point_count: int = 0
    rendered_point_count: int = 0
    metadata: dict[str, object] = field(default_factory=dict)
