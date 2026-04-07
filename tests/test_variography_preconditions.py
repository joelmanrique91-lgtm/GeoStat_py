from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.adapters.geostatspy_adapter import GeostatSpyAdapter
from app.services.activity_log_service import ActivityLogService
from app.services.geostat_service import GeostatService


class VariographyPreconditionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = GeostatService(adapter=GeostatSpyAdapter(), activity_log=ActivityLogService())

    def test_compute_reports_insufficient_active_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "small.csv"
            csv_path.write_text("x,y,z,target,dom\n0,0,0,1,a\n1,1,1,2,a\n", encoding="utf-8")
            self.assertTrue(self.service.load_csv(str(csv_path)).success)
            self.assertTrue(self.service.set_variable_config("x", "y", "z", "target", domain_column="dom").success)
            self.assertTrue(self.service.apply_basic_compositing(composite_length=2.0, target_column="target").success)
            self.assertTrue(self.service.set_variography_domain_bypass(enabled=True, reason="audit").success)

            response = self.service.compute_experimental_variography(
                {
                    "lag_distance": 1.0,
                    "n_lags": 4,
                    "lag_tolerance": 0.5,
                    "max_distance": 8.0,
                }
            )
            self.assertFalse(response.ok)
            self.assertIn("INSUFFICIENT_ACTIVE_ROWS", [item.code for item in response.blockers])


if __name__ == "__main__":
    unittest.main()
