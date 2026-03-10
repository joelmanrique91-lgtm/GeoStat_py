"""Tests for repository update, workflow, autodetection and variable selection logic."""

from __future__ import annotations

import tempfile
import unittest

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
        self.assertIn("Resumen | Univariado | Espacial", summary)

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

    def test_set_variable_config_invalid_column(self) -> None:
        self._load_sample_dataset()
        result = self.service.set_variable_config("Easting", "Northing", "bad", "Au")

        self.assertFalse(result.success)
        self.assertIn("columnas no válidas", result.message)

    @patch("app.services.geostat_service.subprocess.run")
    def test_update_repository_success(self, mock_run) -> None:
        mock_run.side_effect = [
            type("Result", (), {"returncode": 0, "stdout": "Already up to date.", "stderr": ""})(),
            type("Result", (), {"returncode": 0, "stdout": "", "stderr": ""})(),
        ]

        result = self.service.update_repository()

        self.assertTrue(result.success)
        self.assertIn("actualizado", result.message.lower())
        self.assertFalse(result.restart_recommended)


if __name__ == "__main__":
    unittest.main()
