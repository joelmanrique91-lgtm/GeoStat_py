"""Service tests for experimental variography vertical slice."""

from __future__ import annotations

import unittest
from pathlib import Path

from app.adapters.geostatspy_adapter import GeostatSpyAdapter
from app.services.geostat_service import GeostatService

FIXTURES = Path("tests/fixtures/variography")


class VariographyServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = GeostatService(adapter=GeostatSpyAdapter())

    def test_compute_success_with_real_fixture(self) -> None:
        csv_path = FIXTURES / "variography_small_numeric.csv"
        load = self.service.load_csv(str(csv_path))
        self.assertTrue(load.success)
        self.assertTrue(self.service.set_variable_config("x", "y", "z", "target", domain_column="dom").success)
        response = self.service.compute_experimental_variography(
            {
                "target_col": "target",
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
        self.assertTrue(response.ok)
        self.assertIsNotNone(response.result)
        self.assertEqual(len(response.result.lag_centers), 5)
        self.assertEqual(len(response.result.gamma_values), 5)
        self.assertEqual(len(response.result.pair_counts), 5)

    def test_compute_blocks_invalid_lag_params(self) -> None:
        csv_path = FIXTURES / "variography_small_numeric.csv"
        self.assertTrue(self.service.load_csv(str(csv_path)).success)
        self.assertTrue(self.service.set_variable_config("x", "y", "z", "target").success)
        response = self.service.compute_experimental_variography(
            {
                "target_col": "target",
                "lag_distance": -1.0,
                "n_lags": 0,
                "lag_tolerance": 0.0,
                "max_distance": 0.0,
                "azimuth": 0.0,
                "dip": 0.0,
                "ang_tol_h": 90.0,
                "ang_tol_v": 90.0,
                "band_width": 0.0,
                "band_height": 0.0,
                "estimator": "classical",
            }
        )
        self.assertFalse(response.ok)
        codes = {item.code for item in response.blockers}
        self.assertIn("INVALID_LAG_DISTANCE", codes)
        self.assertIn("INVALID_N_LAGS", codes)
        self.assertIn("INVALID_MAX_DISTANCE", codes)


if __name__ == "__main__":
    unittest.main()
