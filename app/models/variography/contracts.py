"""Typed contracts for experimental variography workflows."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

SCHEMA_VERSION = "variography.v1"


@dataclass(frozen=True)
class AnalysisContextRef:
    dataset_file: str
    resolved_target_column: str
    active_domain_column: str = ""
    active_domain_filter: str = ""
    support: str = "Muestra original"


@dataclass(frozen=True)
class LagDefinition:
    lag_distance: float
    n_lags: int
    lag_tolerance: float
    max_distance: float


@dataclass(frozen=True)
class DirectionDefinition:
    azimuth: float = 0.0
    dip: float = 0.0
    ang_tol_h: float = 90.0
    ang_tol_v: float = 90.0
    band_width: float = 0.0
    band_height: float = 0.0


@dataclass(frozen=True)
class ExperimentalVariogramRequest:
    schema_version: str
    context: AnalysisContextRef
    x_col: str
    y_col: str
    z_col: str
    target_col: str
    estimator: Literal["classical", "cressie_hawkins"] = "classical"
    lag: LagDefinition = field(default_factory=lambda: LagDefinition(10.0, 16, 5.0, 160.0))
    direction: DirectionDefinition = field(default_factory=DirectionDefinition)


@dataclass(frozen=True)
class VariographyIssue:
    code: str
    message: str
    severity: Literal["warning", "blocker"]


@dataclass(frozen=True)
class ExperimentalVariogramResult:
    schema_version: str
    lag_centers: list[float]
    gamma_values: list[float]
    pair_counts: list[int]
    source_points: int
    used_points: int
    downsampled: bool
    warnings: list[VariographyIssue] = field(default_factory=list)
    blockers: list[VariographyIssue] = field(default_factory=list)
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class VariographyComputeResponse:
    schema_version: str
    ok: bool
    message: str
    request: ExperimentalVariogramRequest
    result: ExperimentalVariogramResult | None
    warnings: list[VariographyIssue] = field(default_factory=list)
    blockers: list[VariographyIssue] = field(default_factory=list)

