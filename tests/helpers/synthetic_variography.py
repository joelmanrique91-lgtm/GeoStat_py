"""Synthetic deterministic datasets for variography regression tests."""

from __future__ import annotations

import pandas as pd


def linear_x_dataset(n: int = 30, slope: float = 1.0) -> pd.DataFrame:
    rows = []
    for i in range(n):
        x = float(i)
        y = 0.0
        z = 0.0
        target = slope * x
        rows.append({"x": x, "y": y, "z": z, "target": target, "dom": "A"})
    return pd.DataFrame(rows)


def grid_dataset(nx: int = 6, ny: int = 6) -> pd.DataFrame:
    rows = []
    for ix in range(nx):
        for iy in range(ny):
            x = float(ix)
            y = float(iy)
            z = 0.0
            target = float(ix + iy)
            rows.append({"x": x, "y": y, "z": z, "target": target, "dom": "A"})
    return pd.DataFrame(rows)

