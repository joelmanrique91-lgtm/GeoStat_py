from __future__ import annotations

import numpy as np
import pandas as pd


def make_synthetic_drillholes(n: int = 120, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    x = rng.uniform(0, 500, size=n)
    y = rng.uniform(0, 400, size=n)
    z = rng.uniform(-250, 0, size=n)
    trend = 0.004 * x + 0.008 * y - 0.003 * z
    noise = rng.normal(0, 0.4, size=n)
    grade = np.maximum(0.01, trend + noise)
    return pd.DataFrame({"hole_id": [f"DH{i:03d}" for i in range(n)], "X": x, "Y": y, "Z": z, "grade": grade})
