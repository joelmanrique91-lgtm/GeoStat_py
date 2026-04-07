from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from app.adapters.geostatspy_adapter import GeostatSpyAdapter
from app.services.geostat_service import GeostatService


def _build_dataset(n: int = 80, *, with_intervals: bool = True) -> pd.DataFrame:
    rows = []
    for i in range(n):
        hole = f"H{(i // 20) + 1}"
        depth_from = float(i)
        depth_to = float(i + 1)
        rows.append(
            {
                "x": float(i % 20),
                "y": float((i // 20) * 10),
                "z": -depth_from,
                "target": 0.5 + 0.02 * i,
                "dom": "A" if i < (n // 2) else "B",
                "hole_id": hole,
                "depth_from": depth_from,
                "depth_to": depth_to,
            }
        )
    df = pd.DataFrame(rows)
    if not with_intervals:
        df = df.drop(columns=["depth_from", "depth_to"])
    return df


class WorkflowHardeningTests(unittest.TestCase):
    def _load_service(self, df: pd.DataFrame) -> GeostatService:
        service = GeostatService(adapter=GeostatSpyAdapter())
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as handle:
            path = Path(handle.name)
        df.to_csv(path, index=False)
        self.addCleanup(lambda: path.exists() and path.unlink())
        self.assertTrue(service.load_csv(str(path)).success)
        self.assertTrue(service.set_variable_config("x", "y", "z", "target", "hole_id", "dom").success)
        return service

    def test_support_uses_real_interval_compositing_when_columns_exist(self) -> None:
        service = self._load_service(_build_dataset(with_intervals=True))
        result = service.apply_basic_compositing(composite_length=2.0, target_column="target", output_column="target_comp")
        self.assertTrue(result.success)
        support = service.get_support_state()
        self.assertEqual("interval_real", support["mode"])
        self.assertEqual("", support["warning"])

    def test_support_falls_back_when_interval_columns_missing(self) -> None:
        service = self._load_service(_build_dataset(with_intervals=False))
        result = service.apply_basic_compositing(composite_length=2.0, target_column="target", output_column="target_comp")
        self.assertTrue(result.success)
        support = service.get_support_state()
        self.assertEqual("fallback_approx", support["mode"])
        self.assertIn("aproximado", support["warning"])

    def test_variography_blocked_without_domain_confirmation_when_bypass_off(self) -> None:
        service = self._load_service(_build_dataset(with_intervals=True))
        self.assertTrue(service.apply_basic_compositing(composite_length=2.0, target_column="target").success)
        self.assertTrue(service.apply_domain_definition({"variable_base": "dom", "domains": {"DomA": ["A"], "DomB": ["B"]}}).success)
        service.workflow_state.allow_variography_without_domain = False
        readiness = service.get_workflow_readiness_state()
        self.assertFalse(readiness.stage("variography").ready)
        self.assertIn("missing_domain_confirmation", readiness.stage("variography").blocking_reasons)

    def test_variography_warning_when_bypass_is_explicitly_enabled(self) -> None:
        service = self._load_service(_build_dataset(with_intervals=True))
        self.assertTrue(service.apply_basic_compositing(composite_length=2.0, target_column="target").success)
        self.assertTrue(service.apply_domain_definition({"variable_base": "dom", "domains": {"DomA": ["A"], "DomB": ["B"]}}).success)
        service.workflow_state.allow_variography_without_domain = True
        params = {
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
        }
        response = service.compute_experimental_variography(params)
        warning_codes = [item.code for item in response.warnings]
        self.assertIn("DOMAIN_BYPASS_ACTIVE", warning_codes)

    def test_variography_warning_removed_when_bypass_is_disabled(self) -> None:
        service = self._load_service(_build_dataset(with_intervals=True))
        self.assertTrue(service.apply_basic_compositing(composite_length=2.0, target_column="target").success)
        self.assertTrue(service.apply_domain_definition({"variable_base": "dom", "domains": {"DomA": ["A"], "DomB": ["B"]}}).success)
        service.workflow_state.allow_variography_without_domain = True
        params = {
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
        }
        with_bypass = service.compute_experimental_variography(params)
        self.assertIn("DOMAIN_BYPASS_ACTIVE", [item.code for item in with_bypass.warnings])
        service.workflow_state.allow_variography_without_domain = False
        without_bypass = service.compute_experimental_variography(params)
        self.assertNotIn("DOMAIN_BYPASS_ACTIVE", [item.code for item in without_bypass.warnings])

    def test_dataset_reconfiguration_clears_support_and_domain_state(self) -> None:
        service = self._load_service(_build_dataset(with_intervals=True))
        self.assertTrue(service.apply_basic_compositing(composite_length=2.0, target_column="target").success)
        self.assertTrue(service.apply_domain_definition({"variable_base": "dom", "domains": {"DomA": ["A"]}}).success)
        self.assertTrue(service.confirm_domain_assignment("DomA").success)
        self.assertTrue(service.set_variable_config("x", "y", "z", "target", "hole_id", "dom").success)
        self.assertFalse(service.get_support_state()["confirmed"])
        self.assertEqual("", service.workflow_state.active_domain_filter)

    def test_effective_context_aligns_with_eda_and_spatial_targets(self) -> None:
        service = self._load_service(_build_dataset(with_intervals=True))
        self.assertTrue(service.apply_basic_compositing(composite_length=2.0, target_column="target", output_column="target_comp").success)
        ctx = service.get_effective_workflow_context()
        self.assertEqual("target_comp", ctx["target_effective"])
        payload = service.prepare_univariate_data(use_effective_target=True)
        self.assertEqual("target_comp", payload["diagnostics"]["target"])
        spatial = service.prepare_visual_data(color_by=None)
        self.assertTrue(spatial.success)

    def test_domain_change_marks_variography_session_dirty(self) -> None:
        service = self._load_service(_build_dataset(with_intervals=True))
        self.assertTrue(service.apply_basic_compositing(composite_length=2.0, target_column="target").success)
        self.assertTrue(service.apply_domain_definition({"variable_base": "dom", "domains": {"DomA": ["A"], "DomB": ["B"]}}).success)
        self.assertTrue(service.confirm_domain_assignment("DomA").success)
        session = service.get_variography_session()
        session.compute_dirty = False
        self.assertTrue(service.set_active_domain("DomB").success)
        self.assertTrue(session.compute_dirty)

    def test_activity_log_records_support_domain_and_bypass_compute(self) -> None:
        service = self._load_service(_build_dataset(with_intervals=False))
        self.assertTrue(service.apply_basic_compositing(composite_length=2.0, target_column="target").success)
        effective = service.get_effective_workflow_context()
        self.assertEqual("fallback_approx", effective["support_mode"])
        self.assertIn("target_base", effective)
        self.assertIn("target_effective", effective)
        self.assertIn("domain_effective_column", effective)
        self.assertIn("active_domain", effective)
        self.assertTrue(service.apply_domain_definition({"variable_base": "dom", "domains": {"DomA": ["A"], "DomB": ["B"]}}).success)
        self.assertTrue(service.confirm_domain_assignment("DomA").success)
        effective_domain = service.get_effective_workflow_context()
        self.assertTrue(effective_domain["domain_confirmed"])
        self.assertTrue(service.set_active_domain("Todos").success)
        service.workflow_state.allow_variography_without_domain = True
        effective_after_bypass = service.get_effective_workflow_context()
        self.assertTrue(effective_after_bypass["domain_bypass_active"])
        _ = service.compute_experimental_variography(
            {
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
            }
        )

        events = [json.loads(line) for line in service.activity_log.session_log_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        support_event = next(item for item in events if item["event"] == "support_composite_applied")
        self.assertIn("support_mode", support_event["details"])
        self.assertIn("domain_assignment_confirmed", [item["event"] for item in events])
        variography_event = next(item for item in events if item["event"] == "variography_compute")
        self.assertTrue(variography_event["details"].get("domain_bypass_active"))


if __name__ == "__main__":
    unittest.main()
