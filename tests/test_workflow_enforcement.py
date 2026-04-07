from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from app.adapters.geostatspy_adapter import GeostatSpyAdapter
from app.services.geostat_service import GeostatService


def _params() -> dict[str, object]:
    return {
        "target_col": "target",
        "x_col": "x",
        "y_col": "y",
        "z_col": "z",
        "lag_distance": 5.0,
        "n_lags": 8,
        "lag_tolerance": 2.5,
        "max_distance": 40.0,
        "azimuth": 0.0,
        "dip": 0.0,
        "ang_tol_h": 90.0,
        "ang_tol_v": 90.0,
        "band_width": 0.0,
        "band_height": 0.0,
        "estimator": "classical",
        "model": {
            "nugget": {"enabled": True, "value": 0.0, "locked": False},
            "structures": [
                {
                    "active": True,
                    "type": "spherical",
                    "contribution": 1.0,
                    "range_major": 25.0,
                    "range_minor": 20.0,
                    "range_vertical": 15.0,
                    "azimuth": 0.0,
                    "dip": 0.0,
                    "lock_contribution": False,
                    "lock_range": False,
                }
            ],
            "fit": {"method": "manual", "min_pairs": 10, "exclude_lags": []},
        },
    }


def _build_df(with_intervals: bool = True) -> pd.DataFrame:
    rows = []
    for i in range(80):
        rows.append(
            {
                "x": float(i % 20),
                "y": float((i // 20) * 10),
                "z": float(i),
                "target": 0.2 * i,
                "dom": "A" if i < 40 else "B",
                "hole_id": f"H{(i // 20) + 1}",
                "depth_from": float(i),
                "depth_to": float(i + 1),
            }
        )
    df = pd.DataFrame(rows)
    if not with_intervals:
        return df.drop(columns=["depth_from", "depth_to"])
    return df


class WorkflowEnforcementTests(unittest.TestCase):
    def _service(self, df: pd.DataFrame) -> GeostatService:
        service = GeostatService(adapter=GeostatSpyAdapter())
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as handle:
            path = Path(handle.name)
        df.to_csv(path, index=False)
        self.addCleanup(lambda: path.exists() and path.unlink())
        self.assertTrue(service.load_csv(str(path)).success)
        self.assertTrue(service.set_variable_config("x", "y", "z", "target", "hole_id", "dom").success)
        return service

    def test_step_status_derived_from_readiness(self) -> None:
        service = GeostatService(adapter=GeostatSpyAdapter())
        statuses = dict(service.get_workflow_step_status())
        self.assertEqual("bloqueada", statuses["EDA"])
        self.assertEqual("bloqueada", statuses["Variografía"])

    def test_set_active_domain_todos_does_not_enable_bypass(self) -> None:
        service = self._service(_build_df())
        self.assertTrue(service.apply_basic_compositing(composite_length=2.0, target_column="target").success)
        self.assertTrue(service.apply_domain_definition({"variable_base": "dom", "domains": {"A": ["A"], "B": ["B"]}}).success)
        result = service.set_active_domain("Todos")
        self.assertTrue(result.success)
        self.assertFalse(service.workflow_state.allow_variography_without_domain)

    def test_variography_blocked_without_support_confirmation(self) -> None:
        service = self._service(_build_df())
        formal_params = {**_params(), "analysis_mode": "formal"}
        response = service.compute_experimental_variography(formal_params)
        self.assertFalse(response.ok)
        self.assertIn("MISSING_SUPPORT_CONFIRMATION", [item.code for item in response.blockers])

    def test_variography_exploratory_when_support_fallback_and_bypass(self) -> None:
        service = self._service(_build_df(with_intervals=False))
        self.assertTrue(service.apply_basic_compositing(composite_length=2.0, target_column="target").success)
        self.assertTrue(service.apply_domain_definition({"variable_base": "dom", "domains": {"A": ["A"], "B": ["B"]}}).success)
        self.assertTrue(service.set_variography_domain_bypass(True, reason="test").success)
        response = service.compute_experimental_variography(_params())
        self.assertTrue(response.ok)
        metadata = response.result.metadata if response.result is not None else {}
        self.assertTrue(bool(metadata.get("exploratory_mode")))
        self.assertEqual("exploratory_only", metadata.get("exportability", {}).get("status"))


if __name__ == "__main__":
    unittest.main()
