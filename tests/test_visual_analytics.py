"""Tests for spatial prep, domain handling and logging events."""

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
from app.services.visualization_service import prepare_spatial_sections


@unittest.skipUnless(HAS_PANDAS, "pandas no disponible")
class VisualAnalyticsTests(unittest.TestCase):
    def test_downsampling_for_large_spatial_data(self) -> None:
        big = pd.DataFrame({"x": range(30000), "y": range(30000), "z": range(30000), "target": range(30000)})
        data = prepare_spatial_sections(big, "x", "y", "z", "target", max_points=5000)
        self.assertTrue(data.downsampled)
        self.assertEqual(data.source_points, 30000)
        self.assertEqual(data.plotted_points, 5000)

    def test_univariate_domain_limit(self) -> None:
        df = pd.DataFrame(
            {
                "x": range(20),
                "y": range(20),
                "z": range(20),
                "target": [float(i) for i in range(20)],
                "dom": [f"d{i}" for i in range(20)],
            }
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv = Path(tmp_dir) / "sample.csv"
            df.to_csv(csv, index=False)
            service = GeostatService(adapter=GeostatSpyAdapter())
            service.load_csv(str(csv))
            service.set_variable_config("x", "y", "z", "target", domain_column="dom")
            payload = service.prepare_univariate_data(max_domain_categories=5)
            self.assertEqual(len(payload["domain_boxplot"]["labels"]), 5)
            self.assertIn("top 5", payload["domain_boxplot"]["message"])

    def test_univariate_without_domain_selected(self) -> None:
        df = pd.DataFrame({"x": [1, 2], "y": [3, 4], "z": [5, 6], "target": [7.0, 8.0]})
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv = Path(tmp_dir) / "sample.csv"
            df.to_csv(csv, index=False)
            service = GeostatService(adapter=GeostatSpyAdapter())
            service.load_csv(str(csv))
            service.set_variable_config("x", "y", "z", "target")
            payload = service.prepare_univariate_data()
            self.assertFalse(payload["domain_boxplot"]["enabled"])

    def test_logging_events_for_new_rendering(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            log_service = ActivityLogService(logs_dir=Path(tmp_dir))
            service = GeostatService(adapter=GeostatSpyAdapter(), activity_log=log_service)
            csv = Path(tmp_dir) / "sample.csv"
            csv.write_text("x,y,z,target,dom\n0,0,0,1,a\n10,1,2,2,a\n20,2,4,3,b\n30,3,6,4,b\n", encoding="utf-8")
            service.load_csv(str(csv))
            service.set_variable_config("x", "y", "z", "target", domain_column="dom")
            service.set_workflow_step("Datos")
            service.set_workflow_step("EDA")
            service.set_workflow_step("Espacial")
            service.prepare_univariate_data()
            service.prepare_visual_data()

            content = log_service.session_log_path.read_text(encoding="utf-8")
            self.assertIn("workflow_step_data_opened", content)
            self.assertIn("workflow_step_eda_opened", content)
            self.assertIn("workflow_step_spatial_opened", content)
            self.assertIn("eda_domain_boxplot_rendered", content)
            self.assertIn("probability_plot_rendered", content)
            self.assertIn("spatial_2d_rendered", content)


if __name__ == "__main__":
    unittest.main()
