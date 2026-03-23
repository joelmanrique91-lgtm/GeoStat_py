"""Controller for Variography stage interactions."""

from __future__ import annotations

from dataclasses import asdict

from app.services.geostat_service import GeostatService


class VariographyController:
    def __init__(self, service: GeostatService) -> None:
        self.service = service

    def compute(self, ui_state: dict[str, object]) -> dict[str, object]:
        response = self.service.compute_experimental_variography(ui_state)
        payload = {
            "ok": response.ok,
            "message": response.message,
            "warnings": [asdict(item) for item in response.warnings],
            "blockers": [asdict(item) for item in response.blockers],
            "result": None,
        }
        if response.result is not None:
            payload["result"] = {
                "lag_centers": response.result.lag_centers,
                "gamma_values": response.result.gamma_values,
                "pair_counts": response.result.pair_counts,
                "source_points": response.result.source_points,
                "used_points": response.result.used_points,
                "downsampled": response.result.downsampled,
                "metadata": response.result.metadata,
            }
        return payload

    def mark_dirty(self, target_col: str) -> None:
        session = self.service.get_variography_session()
        session.selected_target = target_col
        session.mark_dirty()

    def get_initial_state(self) -> dict[str, object]:
        session = self.service.get_variography_session()
        snapshot = self.service.get_analysis_context_snapshot()
        target_options = self.service.get_numeric_columns()
        target_default = session.selected_target or str(snapshot.get("resolved_target_column") or "")
        if target_default not in target_options:
            target_default = target_options[0] if target_options else ""
        return {
            "target_col": target_default,
            "x_col": self.service.variable_config.x_column if self.service.variable_config else "",
            "y_col": self.service.variable_config.y_column if self.service.variable_config else "",
            "z_col": self.service.variable_config.z_column if self.service.variable_config else "",
            "lag_distance": float(session.lag_distance),
            "n_lags": int(session.n_lags),
            "lag_tolerance": float(session.lag_tolerance),
            "max_distance": float(session.max_distance),
            "azimuth": float(session.azimuth),
            "dip": float(session.dip),
            "ang_tol_h": float(session.ang_tol_h),
            "ang_tol_v": float(session.ang_tol_v),
            "band_width": float(session.band_width),
            "band_height": float(session.band_height),
            "estimator": str(session.estimator),
            "target_options": target_options,
        }
