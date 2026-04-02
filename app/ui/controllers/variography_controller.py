"""Controller for Variography stage interactions."""

from __future__ import annotations

from dataclasses import asdict

from app.services.geostat_service import GeostatService


class VariographyController:
    def __init__(self, service: GeostatService) -> None:
        self.service = service

    def compute(self, ui_state: dict[str, object]) -> dict[str, object]:
        response = self.service.compute_experimental_variography(ui_state)
        requested_n_lags = self._safe_int(ui_state.get("n_lags"), default=16)
        defaults = self.service.estimate_variography_defaults(
            n_lags=requested_n_lags,
            context_snapshot=self.service.get_analysis_context_snapshot(),
        )
        payload = {
            "ok": response.ok,
            "message": response.message,
            "warnings": [asdict(item) for item in response.warnings],
            "blockers": [asdict(item) for item in response.blockers],
            "result": None,
            "metadata": {
                "dominant_blocker": response.blockers[0].code if response.blockers else "",
                "dominant_warning": response.warnings[0].code if response.warnings else "",
                "recommended_max_distance": float(defaults["max_distance"]),
                "recommended_lag_distance": float(defaults["lag_distance"]),
                "effective_rows": int(defaults["effective_rows"]),
            },
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
            payload["metadata"] = dict(response.result.metadata)
        return payload

    @staticmethod
    def _safe_int(value: object, *, default: int) -> int:
        try:
            if value is None:
                return default
            normalized = str(value).strip()
            if not normalized:
                return default
            return int(float(normalized))
        except (TypeError, ValueError):
            return default

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
        dynamic_defaults = self.service.estimate_variography_defaults(
            n_lags=int(session.n_lags),
            context_snapshot=snapshot,
        )
        use_dynamic_defaults = bool(session.last_response is None and session.last_request is None)
        lag_distance = float(dynamic_defaults["lag_distance"]) if use_dynamic_defaults else float(session.lag_distance)
        n_lags = int(dynamic_defaults["n_lags"]) if use_dynamic_defaults else int(session.n_lags)
        max_distance = float(dynamic_defaults["max_distance"]) if use_dynamic_defaults else float(session.max_distance)
        lag_tolerance = float(dynamic_defaults["lag_tolerance"]) if use_dynamic_defaults else float(session.lag_tolerance)
        return {
            "target_col": target_default,
            "x_col": self.service.variable_config.x_column if self.service.variable_config else "",
            "y_col": self.service.variable_config.y_column if self.service.variable_config else "",
            "z_col": self.service.variable_config.z_column if self.service.variable_config else "",
            "lag_distance": lag_distance,
            "n_lags": n_lags,
            "lag_tolerance": lag_tolerance,
            "max_distance": max_distance,
            "azimuth": float(session.azimuth),
            "dip": float(session.dip),
            "ang_tol_h": float(session.ang_tol_h),
            "ang_tol_v": float(session.ang_tol_v),
            "band_width": float(session.band_width),
            "band_height": float(session.band_height),
            "estimator": str(session.estimator),
            "model": {
                "usage_target": "kriging",
                "nugget": {"enabled": True, "value": 0.0, "locked": False},
                "structures": [
                    {
                        "active": True,
                        "type": "spherical",
                        "contribution": 1.0,
                        "range_major": max_distance * 0.8,
                        "range_minor": max_distance * 0.8,
                        "range_vertical": max_distance * 0.4,
                        "azimuth": 0.0,
                        "dip": 0.0,
                        "lock_contribution": False,
                        "lock_range": False,
                    }
                ],
                "fit": {"method": "manual", "min_pairs": 30, "exclude_lags": []},
            },
            "target_options": target_options,
        }
