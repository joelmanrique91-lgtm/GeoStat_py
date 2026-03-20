"""Tests for visual data preparation and EDA statistics/plots preparation."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

try:
    import pandas  # noqa: F401

    HAS_PANDAS = True
except ModuleNotFoundError:
    HAS_PANDAS = False

from app.adapters.geostatspy_adapter import GeostatSpyAdapter
from app.services.geostat_service import GeostatService


@unittest.skipUnless(HAS_PANDAS, "pandas no disponible en este entorno")
class VisualPreparationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = GeostatService(adapter=GeostatSpyAdapter())

    def _load_numeric_dataset(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            p = Path(tmp_dir) / "data.csv"
            p.write_text("x,y,z,target,dom\n1,2,3,10,a\n2,3,4,12,a\n3,4,5,16,b\n", encoding="utf-8")
            self.service.load_csv(str(p))
            self.service.set_variable_config("x", "y", "z", "target", domain_column="dom")

    def test_prepare_visual_data_success(self) -> None:
        self._load_numeric_dataset()
        result = self.service.prepare_visual_data()
        self.assertTrue(result.success)
        self.assertIsNotNone(result.spatial_data)
        self.assertEqual(len(result.spatial_data.target), 3)
        self.assertEqual(len(result.spatial_data.x), 3)
        self.assertEqual(len(result.spatial_data.y), 3)
        self.assertEqual(len(result.spatial_data.z), 3)

    def test_statistics_table_contains_expected_metrics(self) -> None:
        self._load_numeric_dataset()
        table = dict(self.service.get_target_statistics_table())
        self.assertIn("mean", table)
        self.assertIn("p10", table)
        self.assertIn("skewness", table)
        self.assertIn("null_pct", table)
        self.assertIn("valid_count", table)

    def test_univariate_data_contains_probplot_and_domain_boxplot(self) -> None:
        self._load_numeric_dataset()
        payload = self.service.prepare_univariate_data(max_domain_categories=5)
        self.assertEqual(len(payload["probplot_x"]), 3)
        self.assertTrue(payload["domain_boxplot"]["enabled"])
        self.assertTrue(payload["availability"]["histogram"]["available"])
        self.assertTrue(payload["availability"]["boxplot"]["available"])
        self.assertTrue(payload["availability"]["probability"]["available"])


    @patch("app.services.geostat_service.statistics.NormalDist")
    def test_univariate_payload_partial_when_probability_fails(self, mock_normal) -> None:
        self._load_numeric_dataset()
        mock_normal.return_value.inv_cdf.side_effect = ValueError("boom")
        payload = self.service.prepare_univariate_data(max_domain_categories=5)
        self.assertTrue(payload["probability_failed"])
        self.assertEqual(payload["probplot_x"], [])
        self.assertEqual(payload["probplot_y"], [])

    def test_prepare_visual_data_fails_for_non_numeric_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            p = Path(tmp_dir) / "data.csv"
            p.write_text("x,y,z,target\n1,2,3,a\n2,3,4,b\n", encoding="utf-8")
            self.service.load_csv(str(p))
            self.service.set_variable_config("x", "y", "z", "target")
            result = self.service.prepare_visual_data()
            self.assertFalse(result.success)
            self.assertIn("Target no numérico", result.message)

    def test_univariate_coerces_numeric_strings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            p = Path(tmp_dir) / "data.csv"
            p.write_text("x,y,z,target,dom\n1,2,3,10,a\n2,3,4,11.5,b\n3,4,5,foo,a\n", encoding="utf-8")
            self.service.load_csv(str(p))
            self.service.set_variable_config("x", "y", "z", "target", domain_column="dom")
            payload = self.service.prepare_univariate_data()
            self.assertEqual(payload["diagnostics"]["target_valid_count"], 2)
            self.assertEqual(payload["diagnostics"]["target_nan_count"], 1)
            self.assertTrue(payload["availability"]["histogram"]["available"])

    def test_prepare_swath_data_returns_xyz_series(self) -> None:
        self._load_numeric_dataset()
        swath = self.service.prepare_swath_data(bins=5)
        self.assertEqual(set(swath.keys()), {"x", "y", "z"})
        self.assertEqual(swath["x"].axis, "x")
        self.assertEqual(swath["y"].axis, "y")
        self.assertEqual(swath["z"].axis, "z")


if __name__ == "__main__":
    unittest.main()
