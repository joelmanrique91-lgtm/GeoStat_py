"""Facade delegation checks for cutoff flows in GeostatService."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.adapters.geostatspy_adapter import GeostatSpyAdapter
from app.services.geostat_service import GeostatService


class CutoffServiceDelegationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = GeostatService(adapter=GeostatSpyAdapter())

    def _load_numeric_dataset(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "cutoff_delegate.csv"
            csv_path.write_text("x,y,z,target\n0,0,0,1\n1,1,1,2\n2,2,2,3\n", encoding="utf-8")
            self.assertTrue(self.service.load_csv(str(csv_path)).success)
            self.assertTrue(self.service.set_variable_config("x", "y", "z", "target").success)

    def test_dynamic_preview_delegates_to_cutoff_service(self) -> None:
        self._load_numeric_dataset()
        with patch.object(
            self.service.cutoff_service,
            "prepare_dynamic_cutoff_preview",
            wraps=self.service.cutoff_service.prepare_dynamic_cutoff_preview,
        ) as preview_mock:
            payload = self.service.prepare_dynamic_cutoff_preview("target", "percentile", 90.0)
        self.assertGreaterEqual(preview_mock.call_count, 1)
        self.assertIn("cutoff_value", payload)

    def test_apply_cutoffs_delegates_to_cutoff_service(self) -> None:
        self._load_numeric_dataset()
        with patch.object(
            self.service.cutoff_service,
            "apply_cutoffs",
            wraps=self.service.cutoff_service.apply_cutoffs,
        ) as apply_mock:
            result = self.service.apply_cutoffs(enabled=True, target_column="target", limits_text="1.5,2.5")
        self.assertGreaterEqual(apply_mock.call_count, 1)
        self.assertTrue(result.success)

    def test_apply_dynamic_cutoff_delegates_to_cutoff_service(self) -> None:
        self._load_numeric_dataset()
        with patch.object(
            self.service.cutoff_service,
            "apply_dynamic_cutoff",
            wraps=self.service.cutoff_service.apply_dynamic_cutoff,
        ) as apply_mock:
            result = self.service.apply_dynamic_cutoff(
                enabled=True,
                target_column="target",
                mode="percentile",
                slider_percent=95.0,
                output_column="target_capped",
                keep_category_column=False,
            )
        self.assertGreaterEqual(apply_mock.call_count, 1)
        self.assertTrue(result.success)


if __name__ == "__main__":
    unittest.main()
