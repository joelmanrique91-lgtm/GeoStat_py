"""Typed geometry contract for volumetric grids."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class VolumeGrid:
    origin: tuple[float, float, float]
    spacing: tuple[float, float, float]
    dims: tuple[int, int, int]
    values: tuple[float, ...]
    metadata: dict[str, object] = field(default_factory=dict)
