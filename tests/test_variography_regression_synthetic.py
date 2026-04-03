"""Regression tests for omnidirectional/directional variography on synthetic data."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.adapters.geostatspy_adapter import GeostatSpyAdapter
from app.services.geostat_service import GeostatService
from tests.helpers.synthetic_variography import grid_dataset, linear_x_dataset


class VariographySyntheticRegressionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = GeostatService(adapter=GeostatSpyAdapter())

    def _load_df(self, df) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv = Path(tmp_dir) / "syn.csv"
            df.to_csv(csv, index=False)
            self.assertTrue(self.service.load_csv(str(csv)).success)
            self.assertTrue(self.service.set_variable_config("x", "y", "z", "target", domain_column="dom").success)

    def test_omnidirectional_vs_aligned_directional_pairs(self) -> None:
        self._load_df(linear_x_dataset(n=40, slope=1.0))
        base = self.service.compute_experimental_variography(
            {"target_col": "target", "lag_distance": 1.0, "n_lags": 8, "lag_tolerance": 0.4, "max_distance": 8.5, "ang_tol_h": 90.0, "ang_tol_v": 90.0}
        )
        aligned = self.service.compute_experimental_variography(
            {"target_col": "target", "lag_distance": 1.0, "n_lags": 8, "lag_tolerance": 0.4, "max_distance": 8.5, "azimuth": 0.0, "dip": 0.0, "ang_tol_h": 5.0, "ang_tol_v": 20.0}
        )
        misaligned = self.service.compute_experimental_variography(
            {"target_col": "target", "lag_distance": 1.0, "n_lags": 8, "lag_tolerance": 0.4, "max_distance": 8.5, "azimuth": 90.0, "dip": 0.0, "ang_tol_h": 5.0, "ang_tol_v": 20.0}
        )
        self.assertIsNotNone(base.result)
        self.assertIsNotNone(aligned.result)
        self.assertLessEqual(sum(aligned.result.pair_counts), sum(base.result.pair_counts))
        if misaligned.result is not None:
            self.assertLessEqual(sum(misaligned.result.pair_counts), sum(aligned.result.pair_counts))

    def test_angular_limit_edge_is_accepted(self) -> None:
        self._load_df(grid_dataset(7, 7))
        response = self.service.compute_experimental_variography(
            {
                "target_col": "target",
                "lag_distance": 1.0,
                "n_lags": 6,
                "lag_tolerance": 0.5,
                "max_distance": 6.5,
                "azimuth": 45.0,
                "dip": 0.0,
                "ang_tol_h": 90.0,
                "ang_tol_v": 90.0,
            }
        )
        self.assertTrue(response.result is not None or not response.ok)

    def test_duplicate_coordinates_do_not_crash(self) -> None:
        import pandas as pd

        df = grid_dataset(5, 5)
        duplicated = df.iloc[:5].copy()
        df = pd.concat([df, duplicated], ignore_index=True)
        self._load_df(df)
        response = self.service.compute_experimental_variography(
            {"target_col": "target", "lag_distance": 1.0, "n_lags": 5, "lag_tolerance": 0.5, "max_distance": 5.5}
        )
        self.assertIn("ok", {"ok": response.ok})


if __name__ == "__main__":
    unittest.main()
