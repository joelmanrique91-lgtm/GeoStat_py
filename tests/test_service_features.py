"""Tests for repository update, variable selection and EDA logic."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.adapters.geostatspy_adapter import GeostatSpyAdapter
from app.services.geostat_service import GeostatService


class ServiceFeatureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = GeostatService(adapter=GeostatSpyAdapter())

    def _load_sample_dataset(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "sample.csv"
            csv_path.write_text("x,y,z,target,cat\n1,2,3,10,a\n3,4,5,20,b\n", encoding="utf-8")
            result = self.service.load_csv(str(csv_path))
            self.assertTrue(result.success)

    def test_eda_summary_contains_expected_sections(self) -> None:
        self._load_sample_dataset()
        summary = self.service.build_eda_summary()

        self.assertIn("Filas: 2", summary)
        self.assertIn("Tipos de datos", summary)
        self.assertIn("Nulos por columna", summary)
        self.assertIn("Columnas numéricas detectadas", summary)

    def test_set_variable_config_success(self) -> None:
        self._load_sample_dataset()
        result = self.service.set_variable_config("x", "y", "z", "target")

        self.assertTrue(result.success)
        self.assertIn("Configuración de variables guardada", result.message)
        self.assertIn("Estadísticos de la variable objetivo", result.eda_summary)
        self.assertIsNotNone(self.service.variable_config)

    def test_set_variable_config_invalid_column(self) -> None:
        self._load_sample_dataset()
        result = self.service.set_variable_config("x", "y", "bad", "target")

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
