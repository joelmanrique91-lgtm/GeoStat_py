from __future__ import annotations

import time
import unittest

import numpy as np
import pandas as pd

from app.services.visualization_service import compute_experimental_variogram


class VariographyPerformanceTests(unittest.TestCase):
    def test_experimental_variogram_synthetic_runtime(self) -> None:
        rng = np.random.default_rng(7)
        n = 600
        df = pd.DataFrame(
            {
                "x": rng.normal(0.0, 120.0, size=n),
                "y": rng.normal(0.0, 120.0, size=n),
                "z": rng.normal(0.0, 30.0, size=n),
                "target": rng.normal(1.5, 0.5, size=n),
            }
        )
        start = time.perf_counter()
        result = compute_experimental_variogram(
            df,
            "x",
            "y",
            "z",
            "target",
            lag=20.0,
            n_lags=12,
            max_distance=260.0,
            max_points=600,
        )
        elapsed = time.perf_counter() - start
        self.assertEqual(len(result.lag_centers), 12)
        self.assertGreater(max(result.pair_counts), 0)
        self.assertLess(elapsed, 5.0)


if __name__ == "__main__":
    unittest.main()
