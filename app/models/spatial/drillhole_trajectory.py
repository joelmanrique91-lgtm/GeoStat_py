"""Typed geometry contract for drillhole trajectories."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class DrillholeTrajectory:
    """Represents a drillhole as an ordered 3D polyline."""

    hole_id: str
    points_xyz: tuple[tuple[float, float, float], ...]
    metadata: dict[str, object] = field(default_factory=dict)
