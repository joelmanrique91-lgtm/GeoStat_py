"""Typed contracts for theoretical variogram model outputs and reliability status."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal

ReliabilityClass = Literal["BLOCKED", "EXPLORATORY_ONLY", "LOW_RELIABILITY", "ACCEPTABLE_PRELIMINARY"]


@dataclass(frozen=True)
class StructureContract:
    active: bool
    type: str
    contribution: float
    range_major: float
    range_minor: float
    range_vertical: float
    azimuth: float
    dip: float
    lock_contribution: bool = False
    lock_range: bool = False


@dataclass(frozen=True)
class FitDiagnosticsContract:
    method: str
    min_pairs: int
    exclude_lags: list[int]
    optimizer: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class ReliabilityContract:
    classification: ReliabilityClass
    level: str
    flags: list[str]
    notes: list[str]
    metrics: dict[str, float]


@dataclass(frozen=True)
class VariogramModelContract:
    nugget: dict[str, object]
    structures: list[StructureContract]
    fit: FitDiagnosticsContract
    curve_total: list[float]
    curves_by_structure: list[list[float]]
    sill: float
    nugget_relative_pct: float
    practical_range: float
    anisotropy_mode: str
    quality: dict[str, object]
    reliability: ReliabilityContract
    usage_target: str
    usage_warnings: list[str]
    assumptions: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        return asdict(self)

