"""Clipping and slicing state contracts for future interactive tools."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ClippingState:
    enabled: bool = False
    plane_origin: tuple[float, float, float] | None = None
    plane_normal: tuple[float, float, float] | None = None
    mode: str = "none"
    z_min: float | None = None
    z_max: float | None = None
