"""Tests for the CSV loading use case in service layer."""

from __future__ import annotations

import tempfile
import unittest

try:
    import pandas  # noqa: F401
    HAS_PANDAS = True
except ModuleNotFoundError:
    HAS_PANDAS = False
from pathlib import Path

from app.adapters.geostatspy_adapter import GeostatSpyAdapter
from app.services.geostat_service import GeostatService


@unittest.skipUnless(HAS_PANDAS, "pandas no disponible en este entorno")
class CsvLoadingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = GeostatService(adapter=GeostatSpyAdapter())

    def test_load_csv_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "sample.csv"
            csv_path.write_text("x,y,value\n1,2,10\n3,4,20\n", encoding="utf-8")

            result = self.service.load_csv(str(csv_path))

            self.assertTrue(result.success)
            self.assertIsNotNone(result.dataset)
            self.assertEqual(result.dataset.file_name, "sample.csv")
            self.assertEqual(result.dataset.row_count, 2)
            self.assertEqual(result.dataset.column_count, 3)
            self.assertEqual(result.dataset.columns, ["x", "y", "value"])
            self.assertIn("Preview", result.details)
            self.assertIsNotNone(self.service.current_dataset)

    def test_load_csv_missing_file(self) -> None:
        result = self.service.load_csv("nonexistent_folder/nonexistent.csv")

        self.assertFalse(result.success)
        self.assertIn("no existe", result.details)
        self.assertIsNone(self.service.current_dataset)

    def test_load_csv_empty_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "empty.csv"
            csv_path.write_text("", encoding="utf-8")

            result = self.service.load_csv(str(csv_path))

            self.assertFalse(result.success)
            self.assertIn("vacío", result.message)
            self.assertIsNone(self.service.current_dataset)


if __name__ == "__main__":
    unittest.main()
