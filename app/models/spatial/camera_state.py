"""Camera contracts for scene persistence and renderer hints."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CameraState:
    azimuth: float = -54.0
    elevation: float = 26.0
    distance: float | None = None
    focal_point: tuple[float, float, float] | None = None
