"""Minimal integration smoke for controller/service variography path."""

from __future__ import annotations

import unittest
from pathlib import Path

from app.adapters.geostatspy_adapter import GeostatSpyAdapter
from app.services.geostat_service import GeostatService
from app.ui.controllers.variography_controller import VariographyController


class VariographyIntegrationSmokeTests(unittest.TestCase):
    def test_controller_compute_returns_result_payload(self) -> None:
        service = GeostatService(adapter=GeostatSpyAdapter())
        csv_path = Path("tests/fixtures/variography/variography_small_numeric.csv")
        self.assertTrue(service.load_csv(str(csv_path)).success)
        self.assertTrue(service.set_variable_config("x", "y", "z", "target").success)
        controller = VariographyController(service=service)
        initial = controller.get_initial_state()
        response = controller.compute(
            {
                "target_col": initial["target_col"],
                "lag_distance": 10.0,
                "n_lags": 5,
                "lag_tolerance": 5.0,
                "max_distance": 60.0,
                "azimuth": 0.0,
                "dip": 0.0,
                "ang_tol_h": 90.0,
                "ang_tol_v": 90.0,
                "band_width": 0.0,
                "band_height": 0.0,
                "estimator": "classical",
            }
        )
        self.assertIn("ok", response)
        self.assertIn("message", response)
        self.assertIn("warnings", response)
        self.assertIn("blockers", response)
        self.assertIsInstance(response.get("result"), dict)

    def test_controller_mark_dirty_updates_session(self) -> None:
        service = GeostatService(adapter=GeostatSpyAdapter())
        csv_path = Path("tests/fixtures/variography/variography_small_numeric.csv")
        self.assertTrue(service.load_csv(str(csv_path)).success)
        self.assertTrue(service.set_variable_config("x", "y", "z", "target").success)
        controller = VariographyController(service=service)
        controller.mark_dirty("target")
        session = service.get_variography_session()
        self.assertTrue(session.compute_dirty)
        self.assertEqual(session.selected_target, "target")


if __name__ == "__main__":
    unittest.main()
