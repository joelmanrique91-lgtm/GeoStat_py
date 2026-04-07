"""Color mapping configuration for scene layers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ColorMappingConfig:
    variable: str
    scheme: str = "viridis"
    value_min: float | None = None
    value_max: float | None = None
    null_color: str = "#808080"
