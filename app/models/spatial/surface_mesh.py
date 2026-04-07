"""Typed geometry contract for explicit surface meshes."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SurfaceMesh:
    name: str
    vertices: tuple[tuple[float, float, float], ...]
    faces: tuple[tuple[int, int, int], ...]
    metadata: dict[str, object] = field(default_factory=dict)
