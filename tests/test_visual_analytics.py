"""Tests for spatial sections, swath plots, variogram and stability logging."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

try:
    import pandas as pd

    HAS_PANDAS = True
except ModuleNotFoundError:
    HAS_PANDAS = False

from app.adapters.geostatspy_adapter import GeostatSpyAdapter
from app.services.activity_log_service import ActivityLogService
from app.services.geostat_service import GeostatService
from app.services.visualization_service import compute_experimental_variogram, compute_swath_series, prepare_spatial_sections


@unittest.skipUnless(HAS_PANDAS, "pandas no disponible")
class VisualAnalyticsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.df = pd.DataFrame(
            {
                "x": [0, 10, 20, 30, 40],
                "y": [0, 2, 4, 6, 8],
                "z": [100, 95, 90, 85, 80],
                "target": [1.0, 2.0, 3.0, 4.0, 5.0],
            }
        )

    def test_prepare_spatial_sections_xy_xz_yz(self) -> None:
        data = prepare_spatial_sections(self.df, "x", "y", "z", "target")
        self.assertEqual(len(data.x), 5)
        self.assertFalse(data.downsampled)

    def test_downsampling_for_large_spatial_data(self) -> None:
        big = pd.DataFrame({"x": range(30000), "y": range(30000), "z": range(30000), "target": range(30000)})
        data = prepare_spatial_sections(big, "x", "y", "z", "target", max_points=5000)
        self.assertTrue(data.downsampled)
        self.assertEqual(data.source_points, 30000)
        self.assertEqual(data.plotted_points, 5000)

    def test_prepare_swath_data(self) -> None:
        swath = compute_swath_series(self.df, "x", "target", bins=4)
        self.assertEqual(swath.axis, "x")
        self.assertEqual(len(swath.centers), 4)

    def test_variogram_data(self) -> None:
        vg = compute_experimental_variogram(self.df, "x", "y", "z", "target", lag=15, n_lags=4, max_distance=80)
        self.assertEqual(len(vg.lag_centers), 4)
        self.assertGreater(sum(vg.pair_counts), 0)

    def test_errors_with_missing_columns_or_non_numeric_target(self) -> None:
        with self.assertRaises(ValueError):
            prepare_spatial_sections(self.df[["x", "y", "target"]], "x", "y", "z", "target")

        bad_df = self.df.copy()
        bad_df["target"] = ["a", "b", "c", "d", "e"]
        with self.assertRaises(ValueError):
            compute_swath_series(bad_df, "x", "target", bins=5)

    def test_logging_events_for_simplified_pipeline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            log_service = ActivityLogService(logs_dir=Path(tmp_dir))
            service = GeostatService(adapter=GeostatSpyAdapter(), activity_log=log_service)
            csv = Path(tmp_dir) / "sample.csv"
            csv.write_text("x,y,z,target\n0,0,0,1\n10,1,2,2\n20,2,4,3\n30,3,6,4\n", encoding="utf-8")
            service.load_csv(str(csv))
            service.set_variable_config("x", "y", "z", "target")
            service.prepare_visual_data()

            content = log_service.session_log_path.read_text(encoding="utf-8")
            self.assertIn("columns_autodetected", content)
            self.assertIn("dashboard_render_started", content)
            self.assertIn("dashboard_render_finished", content)


if __name__ == "__main__":
    unittest.main()
