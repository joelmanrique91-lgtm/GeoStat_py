"""Typed geometry contract for assay intervals in 3D."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class AssayIntervals3D:
    """Stores interval and segment approximations for colored assay display."""

    hole_id: str
    from_to: tuple[tuple[float, float], ...]
    values: tuple[float, ...]
    segments_xyz: tuple[tuple[tuple[float, float, float], tuple[float, float, float]], ...]
    variable_name: str = ""
    metadata: dict[str, object] = field(default_factory=dict)
