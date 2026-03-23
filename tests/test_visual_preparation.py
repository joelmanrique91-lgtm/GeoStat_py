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

    def test_prepare_visual_data_uses_snapshot_context(self) -> None:
        self._load_numeric_dataset()
        with patch.object(self.service, "get_analysis_context_snapshot", wraps=self.service.get_analysis_context_snapshot) as snapshot_mock:
            result = self.service.prepare_visual_data()
        self.assertTrue(result.success)
        self.assertGreaterEqual(snapshot_mock.call_count, 1)

    def test_prepare_visual_data_respects_active_domain_filter_from_snapshot(self) -> None:
        self._load_numeric_dataset()
        applied = self.service.apply_domain_definition({"variable_base": "dom", "domains": {"A": ["a"], "B": ["b"]}})
        self.assertFalse(applied.success)
        self.assertTrue(self.service.set_active_domain("A").success)

        snapshot = self.service.get_analysis_context_snapshot()
        self.assertEqual(snapshot["active_domain_filter"], "")
        result = self.service.prepare_visual_data()
        self.assertTrue(result.success)
        self.assertEqual(len(result.spatial_data.target), 3)

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
        self.assertFalse(payload["domain_boxplot"]["enabled"])
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

    def test_prepare_visual_data_fails_when_resolved_target_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            p = Path(tmp_dir) / "data.csv"
            p.write_text("x,y,z,target\n1,2,3,10\n2,3,4,11\n", encoding="utf-8")
            self.service.load_csv(str(p))
            self.service.set_variable_config("x", "y", "z", "target")
            self.assertTrue(
                self.service.apply_dynamic_cutoff(
                    enabled=True,
                    target_column="target",
                    mode="percentile",
                    slider_percent=50.0,
                    output_column="target_capped_missing",
                    keep_category_column=False,
                ).success
            )
            self.service.current_dataset.dataframe.drop(columns=["target_capped_missing"], inplace=True)
            result = self.service.prepare_visual_data()
            self.assertFalse(result.success)
            self.assertIn("Target no válido para secciones espaciales", result.message)

    def test_prepare_visual_data_fails_when_active_domain_column_missing(self) -> None:
        self._load_numeric_dataset()
        self.service.workflow_state.active_domain_filter = "A"
        self.service.variable_config.domain_column = "missing_domain_col"
        result = self.service.prepare_visual_data()
        self.assertTrue(result.success)

    def test_prepare_visual_data_color_by_override_is_respected(self) -> None:
        self._load_numeric_dataset()
        result = self.service.prepare_visual_data(color_by="dom")
        self.assertTrue(result.success)
        self.assertIsNotNone(result.spatial_data)
        self.assertEqual(result.spatial_data.target_label, "Target (categorías)")

    def test_prepare_visual_data_fails_for_invalid_color_by(self) -> None:
        self._load_numeric_dataset()
        result = self.service.prepare_visual_data(color_by="nope")
        self.assertFalse(result.success)
        self.assertIn("La columna de color no existe", result.message)

    def test_prepare_visual_data_fails_when_spatial_columns_missing(self) -> None:
        self._load_numeric_dataset()
        self.service.current_dataset.dataframe.drop(columns=["x"], inplace=True)
        result = self.service.prepare_visual_data()
        self.assertFalse(result.success)
        self.assertIn("Columnas faltantes para secciones", result.message)

    def test_prepare_visual_data_with_effective_target_regression(self) -> None:
        self._load_numeric_dataset()
        self.assertTrue(
            self.service.apply_dynamic_cutoff(
                enabled=True,
                target_column="target",
                mode="percentile",
                slider_percent=50.0,
                output_column="target_capped",
                keep_category_column=False,
            ).success
        )
        result = self.service.prepare_visual_data()
        self.assertTrue(result.success)
        self.assertEqual(len(result.spatial_data.target), 3)

    def test_prepare_visual_3d_data_success_and_contract(self) -> None:
        self._load_numeric_dataset()
        result = self.service.prepare_visual_3d_data()
        self.assertTrue(result.success)
        self.assertIsNotNone(result.spatial_3d_data)
        payload = result.spatial_3d_data
        self.assertEqual(len(payload.x), 3)
        self.assertEqual(len(payload.y), 3)
        self.assertEqual(len(payload.z), 3)
        self.assertEqual(len(payload.color_values), 3)
        self.assertEqual(payload.point_count_original, 3)
        self.assertEqual(payload.point_count_rendered, 3)
        self.assertFalse(payload.downsampling_applied)
        self.assertEqual(payload.color_mode, "numeric")

    def test_prepare_visual_3d_data_supports_categorical_color(self) -> None:
        self._load_numeric_dataset()
        result = self.service.prepare_visual_3d_data(color_by="dom")
        self.assertTrue(result.success)
        self.assertIsNotNone(result.spatial_3d_data)
        payload = result.spatial_3d_data
        self.assertEqual(payload.color_mode, "categorical")
        self.assertIsNotNone(payload.color_tick_positions)
        self.assertIsNotNone(payload.color_tick_labels)

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
