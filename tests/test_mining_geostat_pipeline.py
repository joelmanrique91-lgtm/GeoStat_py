from __future__ import annotations

import unittest
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from mining_geostat.kriging import NeighborhoodConfig, ordinary_kriging
from mining_geostat.pipeline import GeostatPipelineConfig, run_geostat_pipeline
from mining_geostat.synthetic import make_synthetic_drillholes
from mining_geostat.variogram import VariogramModel, experimental_variogram_3d


class TestMiningGeostatPipeline(unittest.TestCase):
    def test_variogram_invariance_under_row_order(self):
        df = make_synthetic_drillholes(n=80, seed=10)
        exp1 = experimental_variogram_3d(
            df,
            x="X",
            y="Y",
            z="Z",
            value="grade",
            lag=30.0,
            n_lags=8,
            max_distance=240.0,
        )
        exp2 = experimental_variogram_3d(
            df.sample(frac=1.0, random_state=99).reset_index(drop=True),
            x="X",
            y="Y",
            z="Z",
            value="grade",
            lag=30.0,
            n_lags=8,
            max_distance=240.0,
        )
        self.assertEqual(exp1.npairs, exp2.npairs)

    def test_basic_ordinary_kriging_numeric(self):
        xyz = np.array([[0, 0, 0], [10, 0, 0], [0, 10, 0], [10, 10, 0], [5, 5, 2]], dtype=float)
        val = np.array([1.0, 1.2, 0.8, 1.1, 1.0], dtype=float)
        model = VariogramModel(model_type="spherical", nugget=0.0, sill=1.0, range_=20.0)
        kr = ordinary_kriging(xyz, val, np.array([5.0, 5.0, 0.0]), model, NeighborhoodConfig(min_samples=4, max_samples=5))
        self.assertTrue(0.7 <= kr.estimate <= 1.3)
        self.assertGreaterEqual(kr.variance, 0.0)

    def test_pipeline_reproducibility_seed(self):
        c = GeostatPipelineConfig(seed=22)
        r1 = run_geostat_pipeline(c)
        r2 = run_geostat_pipeline(c)
        self.assertEqual(r1["cross_validation"], r2["cross_validation"])

    def test_pipeline_contains_cross_validation(self):
        r = run_geostat_pipeline(GeostatPipelineConfig(seed=5))
        self.assertIn("rmse", r["cross_validation"])
        self.assertGreater(r["cross_validation"]["n"], 0)


if __name__ == "__main__":
    unittest.main()
