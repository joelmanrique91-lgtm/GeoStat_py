"""Authoritative in-memory session state for variography stage."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.models.variography.contracts import ExperimentalVariogramRequest, VariographyComputeResponse


@dataclass
class VariographySession:
    selected_target: str = ""
    selected_domain_filter: str = ""
    selected_support: str = "Muestra original"
    lag_distance: float = 10.0
    n_lags: int = 16
    lag_tolerance: float = 5.0
    max_distance: float = 160.0
    azimuth: float = 0.0
    dip: float = 0.0
    ang_tol_h: float = 90.0
    ang_tol_v: float = 90.0
    band_width: float = 0.0
    band_height: float = 0.0
    estimator: str = "classical"
    compute_dirty: bool = True
    render_dirty: bool = True
    last_request: ExperimentalVariogramRequest | None = None
    last_response: VariographyComputeResponse | None = None
    latest_warning_codes: list[str] = field(default_factory=list)
    latest_blocker_codes: list[str] = field(default_factory=list)

    def mark_dirty(self) -> None:
        self.compute_dirty = True
        self.render_dirty = True

    def mark_computed(self, response: VariographyComputeResponse) -> None:
        self.last_response = response
        self.last_request = response.request
        self.compute_dirty = False
        self.render_dirty = False
        self.latest_warning_codes = [item.code for item in response.warnings]
        self.latest_blocker_codes = [item.code for item in response.blockers]

