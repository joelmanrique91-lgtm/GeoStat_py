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

    @staticmethod
    def _model_payload() -> dict[str, object]:
        return {
            "usage_target": "kriging",
            "nugget": {"enabled": True, "value": 0.1, "locked": False},
            "structures": [
                {
                    "active": True,
                    "type": "spherical",
                    "contribution": 0.9,
                    "range_major": 60.0,
                    "range_minor": 40.0,
                    "range_vertical": 20.0,
                    "azimuth": 0.0,
                    "dip": 0.0,
                    "lock_contribution": False,
                    "lock_range": False,
                }
            ],
            "fit": {"method": "manual", "min_pairs": 30, "exclude_lags": []},
        }

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
                "model": self._model_payload(),
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
                "model": self._model_payload(),
            }
        )
        self.assertFalse(response.ok)
        codes = {item.code for item in response.blockers}
        self.assertIn("INVALID_LAG_DISTANCE", codes)
        self.assertIn("INVALID_N_LAGS", codes)
        self.assertIn("INVALID_MAX_DISTANCE", codes)

    def test_compute_returns_low_npairs_warning(self) -> None:
        csv_path = FIXTURES / "variography_small_numeric.csv"
        self.assertTrue(self.service.load_csv(str(csv_path)).success)
        self.assertTrue(self.service.set_variable_config("x", "y", "z", "target").success)
        response = self.service.compute_experimental_variography(
            {
                "target_col": "target",
                "lag_distance": 5.0,
                "n_lags": 20,
                "lag_tolerance": 2.5,
                "max_distance": 100.0,
                "azimuth": 0.0,
                "dip": 0.0,
                "ang_tol_h": 90.0,
                "ang_tol_v": 90.0,
                "band_width": 0.0,
                "band_height": 0.0,
                "estimator": "classical",
                "model": self._model_payload(),
            }
        )
        warning_codes = {item.code for item in response.warnings}
        self.assertIn("LOW_NPAIRS_LAG", warning_codes)

    def test_compute_blocks_when_dataframe_is_empty(self) -> None:
        csv_path = FIXTURES / "variography_small_numeric.csv"
        self.assertTrue(self.service.load_csv(str(csv_path)).success)
        self.assertTrue(self.service.set_variable_config("x", "y", "z", "target").success)
        self.service.current_dataset.dataframe = self.service.current_dataset.dataframe.iloc[0:0]
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
                "model": self._model_payload(),
            }
        )
        self.assertFalse(response.ok)
        blocker_codes = {item.code for item in response.blockers}
        self.assertIn("NO_ACTIVE_ROWS", blocker_codes)

    def test_directional_parameters_affect_pair_counts(self) -> None:
        csv_path = FIXTURES / "variography_small_numeric.csv"
        self.assertTrue(self.service.load_csv(str(csv_path)).success)
        self.assertTrue(self.service.set_variable_config("x", "y", "z", "target").success)
        base = self.service.compute_experimental_variography(
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
                "model": self._model_payload(),
            }
        )
        directional = self.service.compute_experimental_variography(
            {
                "target_col": "target",
                "lag_distance": 10.0,
                "n_lags": 5,
                "lag_tolerance": 5.0,
                "max_distance": 60.0,
                "azimuth": 90.0,
                "dip": 0.0,
                "ang_tol_h": 5.0,
                "ang_tol_v": 10.0,
                "band_width": 8.0,
                "band_height": 8.0,
                "model": self._model_payload(),
            }
        )
        self.assertIsNotNone(base.result)
        if directional.result is None:
            self.assertFalse(directional.ok)
        else:
            self.assertLessEqual(sum(directional.result.pair_counts), sum(base.result.pair_counts))
            self.assertTrue(bool(directional.result.metadata.get("direction_applied")))

    def test_compute_no_pairs_in_range_returns_specific_blocker(self) -> None:
        csv_path = FIXTURES / "variography_small_numeric.csv"
        self.assertTrue(self.service.load_csv(str(csv_path)).success)
        self.assertTrue(self.service.set_variable_config("x", "y", "z", "target").success)
        response = self.service.compute_experimental_variography(
            {
                "target_col": "target",
                "lag_distance": 1.0,
                "n_lags": 6,
                "lag_tolerance": 0.5,
                "max_distance": 1.5,
                "azimuth": 0.0,
                "dip": 0.0,
                "ang_tol_h": 90.0,
                "ang_tol_v": 90.0,
                "band_width": 0.0,
                "band_height": 0.0,
                "estimator": "classical",
                "model": self._model_payload(),
            }
        )
        self.assertFalse(response.ok)
        blocker_codes = {item.code for item in response.blockers}
        self.assertIn("NO_PAIRS_IN_RANGE", blocker_codes)

    def test_compute_without_variable_config_returns_blockers_instead_of_crashing(self) -> None:
        csv_path = FIXTURES / "variography_small_numeric.csv"
        self.assertTrue(self.service.load_csv(str(csv_path)).success)
        response = self.service.compute_experimental_variography(
            {
                "target_col": "target",
                "lag_distance": 10.0,
                "n_lags": 5,
                "lag_tolerance": 5.0,
                "max_distance": 60.0,
                "model": self._model_payload(),
            }
        )
        self.assertFalse(response.ok)
        blocker_codes = {item.code for item in response.blockers}
        self.assertIn("MISSING_VARIABLE_CONFIG", blocker_codes)
        self.assertIn("INVALID_CONTEXT_COLUMNS", blocker_codes)

    def test_compute_blocks_manual_fit_without_active_structures(self) -> None:
        csv_path = FIXTURES / "variography_small_numeric.csv"
        self.assertTrue(self.service.load_csv(str(csv_path)).success)
        self.assertTrue(self.service.set_variable_config("x", "y", "z", "target").success)
        response = self.service.compute_experimental_variography(
            {
                "target_col": "target",
                "lag_distance": 10.0,
                "n_lags": 5,
                "lag_tolerance": 5.0,
                "max_distance": 60.0,
                "model": {
                    "nugget": {"enabled": True, "value": 0.1, "locked": False},
                    "structures": [],
                    "fit": {"method": "manual", "min_pairs": 30, "exclude_lags": []},
                },
            }
        )
        self.assertFalse(response.ok)
        blocker_codes = {item.code for item in response.blockers}
        self.assertIn("MISSING_ACTIVE_STRUCTURES_MANUAL", blocker_codes)

    def test_compute_blocks_non_numeric_context_columns(self) -> None:
        csv_path = FIXTURES / "variography_invalid_context.csv"
        self.assertTrue(self.service.load_csv(str(csv_path)).success)
        self.assertTrue(self.service.set_variable_config("x", "y", "z", "target").success)
        response = self.service.compute_experimental_variography(
            {
                "target_col": "target",
                "lag_distance": 10.0,
                "n_lags": 5,
                "lag_tolerance": 5.0,
                "max_distance": 60.0,
            }
        )
        self.assertFalse(response.ok)
        blocker_codes = {item.code for item in response.blockers}
        self.assertIn("NON_NUMERIC_CONTEXT_COLUMN", blocker_codes)


if __name__ == "__main__":
    unittest.main()
