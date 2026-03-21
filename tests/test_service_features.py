"""Tests for repository update, workflow, autodetection and variable selection logic."""

from __future__ import annotations

import tempfile
import unittest
import os

try:
    import pandas  # noqa: F401

    HAS_PANDAS = True
except ModuleNotFoundError:
    HAS_PANDAS = False
from pathlib import Path
from unittest.mock import patch

from app.adapters.geostatspy_adapter import GeostatSpyAdapter
from app.services.geostat_service import GeostatService


@unittest.skipUnless(HAS_PANDAS, "pandas no disponible en este entorno")
class ServiceFeatureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = GeostatService(adapter=GeostatSpyAdapter())

    def _load_sample_dataset(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "sample.csv"
            csv_path.write_text("Easting,Northing,RL,Au,HoleID,Lithology\n1,2,3,10,DH01,A\n3,4,5,20,DH02,B\n", encoding="utf-8")
            result = self.service.load_csv(str(csv_path))
            self.assertTrue(result.success)

    def test_eda_summary_contains_expected_sections(self) -> None:
        self._load_sample_dataset()
        summary = self.service.build_eda_summary()
        self.assertIn("MÓDULO EDA", summary)
        self.assertIn("Resumen | Univariado", summary)

    def test_autodetect_columns(self) -> None:
        self._load_sample_dataset()
        detected = self.service.get_autodetected_columns()
        self.assertEqual(detected["x"], "Easting")
        self.assertEqual(detected["y"], "Northing")
        self.assertEqual(detected["z"], "RL")
        self.assertEqual(detected["hole_id"], "HoleID")
        self.assertEqual(detected["domain"], "Lithology")

    def test_set_variable_config_success(self) -> None:
        self._load_sample_dataset()
        result = self.service.set_variable_config("Easting", "Northing", "RL", "Au", "HoleID", "Lithology")

        self.assertTrue(result.success)
        self.assertIn("Configuración de variables guardada", result.message)
        self.assertIsNotNone(self.service.variable_config)
        self.assertEqual(self.service.workflow_state.active_support, "Muestra original")

    @patch("app.services.geostat_service.subprocess.run")
    def test_update_repository_success_when_enabled(self, mock_run) -> None:
        mock_run.side_effect = [
            type("Result", (), {"returncode": 0, "stdout": "Already up to date.", "stderr": ""})(),
            type("Result", (), {"returncode": 0, "stdout": "", "stderr": ""})(),
        ]
        with patch.dict(os.environ, {"GEOSTAT_ENABLE_RUNTIME_GIT_UPDATE": "1"}):
            result = self.service.update_repository()

        self.assertTrue(result.success)
        self.assertIn("actualizado", result.message.lower())
        self.assertFalse(result.restart_recommended)

    @patch("app.services.geostat_service.subprocess.run")
    def test_update_repository_fails_when_submodule_update_fails(self, mock_run) -> None:
        mock_run.side_effect = [
            type("Result", (), {"returncode": 0, "stdout": "Already up to date.", "stderr": ""})(),
            type("Result", (), {"returncode": 1, "stdout": "", "stderr": "submodule boom"})(),
        ]
        with patch.dict(os.environ, {"GEOSTAT_ENABLE_RUNTIME_GIT_UPDATE": "1"}):
            result = self.service.update_repository()

        self.assertFalse(result.success)
        self.assertIn("submódulos", result.message.lower())
        self.assertIn("submodule boom", result.details)

    def test_update_repository_blocked_by_default(self) -> None:
        result = self.service.update_repository()
        self.assertFalse(result.success)
        self.assertIn("deshabilitada", result.message.lower())

    def test_build_eda_summary_uses_effective_target_statistics_when_requested(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "capping_case.csv"
            csv_path.write_text("x,y,z,target\n0,0,0,10\n1,1,1,100\n", encoding="utf-8")
            result = self.service.load_csv(str(csv_path))
            self.assertTrue(result.success)
            cfg = self.service.set_variable_config("x", "y", "z", "target")
            self.assertTrue(cfg.success)

            capping = self.service.apply_dynamic_cutoff(
                enabled=True,
                target_column="target",
                mode="percentile",
                slider_percent=50.0,
                output_column="target_capped",
                keep_category_column=False,
            )
            self.assertTrue(capping.success)

            summary = self.service.build_eda_summary(use_effective_target=True)
            self.assertIn("Target target_capped", summary)

            expected_mean = float(self.service.current_dataset.dataframe["target_capped"].dropna().astype(float).mean())
            self.assertIn(f"mean={expected_mean:.4g}", summary)

    def test_prepare_univariate_returns_expected_contract(self) -> None:
        self._load_sample_dataset()
        self.service.set_variable_config("Easting", "Northing", "RL", "Au", "HoleID", "Lithology")
        payload = self.service.prepare_univariate_data()
        self.assertIsInstance(payload, dict)
        self.assertIn("target_values", payload)
        self.assertIn("availability", payload)
        self.assertIn("diagnostics", payload)
        self.assertTrue(payload["availability"]["histogram"]["available"])

    def test_statistics_table_safe_when_target_numeric_without_valid_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "nan_target.csv"
            csv_path.write_text("x,y,z,target\n1,2,3,\n4,5,6,\n", encoding="utf-8")
            result = self.service.load_csv(str(csv_path))
            self.assertTrue(result.success)
            cfg = self.service.set_variable_config("x", "y", "z", "target")
            self.assertTrue(cfg.success)

            table = dict(self.service.get_target_statistics_table())
            self.assertEqual(table["valid_count"], "0")
            self.assertEqual(table["null_pct"], "100")
            self.assertEqual(table["mean"], "nan")


if __name__ == "__main__":
    unittest.main()
