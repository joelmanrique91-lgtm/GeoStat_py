"""Tests for persistent domain estimation definitions and integrations."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

try:
    import pandas  # noqa: F401

    HAS_PANDAS = True
except ModuleNotFoundError:
    HAS_PANDAS = False

from app.adapters.geostatspy_adapter import GeostatSpyAdapter
from app.services.geostat_service import GeostatService


@unittest.skipUnless(HAS_PANDAS, "pandas no disponible en este entorno")
class DomainEstimationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = GeostatService(adapter=GeostatSpyAdapter())

    def _load_dataset(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "domains.csv"
            csv_path.write_text(
                "x,y,z,target,Minz,Lito\n0,0,0,10,A,L1\n1,1,1,12,B,L1\n2,2,2,14,C,L2\n3,3,3,9,D,L3\n",
                encoding="utf-8",
            )
            self.assertTrue(self.service.load_csv(str(csv_path)).success)
            self.assertTrue(self.service.set_variable_config("x", "y", "z", "target", domain_column="Lito").success)

    def test_apply_domain_definition_creates_persistent_column(self) -> None:
        self._load_dataset()
        original_columns = list(self.service.current_dataset.columns)
        result = self.service.apply_domain_definition(
            {"variable_base": "Minz", "domains": {"D1": ["A", "B", "C"], "D2": ["D"]}}
        )
        self.assertTrue(result.success)
        self.assertIn("domain_estimation", self.service.current_dataset.columns)
        self.assertEqual(
            self.service.current_dataset.dataframe["domain_estimation"].tolist(),
            ["D1", "D1", "D1", "D2"],
        )
        self.assertEqual(
            [column for column in self.service.current_dataset.columns if column != "domain_estimation"],
            [column for column in original_columns if column != "domain_estimation"],
        )

    def test_unassigned_categories_become_undefined(self) -> None:
        self._load_dataset()
        self.assertTrue(
            self.service.apply_domain_definition({"variable_base": "Minz", "domains": {"D1": ["A"]}}).success
        )
        self.assertEqual(
            self.service.current_dataset.dataframe["domain_estimation"].tolist(),
            ["D1", "UNDEFINED", "UNDEFINED", "UNDEFINED"],
        )

    def test_eda_uses_domain_estimation_and_global_filter(self) -> None:
        self._load_dataset()
        self.assertTrue(
            self.service.apply_domain_definition({"variable_base": "Minz", "domains": {"D1": ["A", "B"], "D2": ["C", "D"]}}).success
        )
        self.assertTrue(self.service.set_active_domain("D1").success)
        payload = self.service.prepare_univariate_data()
        self.assertEqual(payload["diagnostics"]["total_rows"], 2)
        self.assertEqual(payload["diagnostics"]["domain"], "domain_estimation")
        self.assertTrue(payload["domain_boxplot"]["enabled"])

    def test_spatial_supports_domain_estimation_color(self) -> None:
        self._load_dataset()
        self.assertTrue(
            self.service.apply_domain_definition({"variable_base": "Minz", "domains": {"D1": ["A", "B"], "D2": ["C", "D"]}}).success
        )
        result = self.service.prepare_visual_data(color_by="domain_estimation")
        self.assertTrue(result.success)
        self.assertIsNotNone(result.spatial_data)
        self.assertEqual(result.spatial_data.target_label, "Target (categorías)")
        self.assertIsNotNone(result.spatial_data.target_tick_labels)

    def test_backwards_compat_without_domains(self) -> None:
        self._load_dataset()
        payload = self.service.prepare_univariate_data()
        self.assertIn("domain_boxplot", payload)
        spatial = self.service.prepare_visual_data()
        self.assertTrue(spatial.success)


if __name__ == "__main__":
    unittest.main()
