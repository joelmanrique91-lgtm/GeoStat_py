from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .kriging import NeighborhoodConfig, ordinary_kriging
from .variogram import VariogramModel


@dataclass(frozen=True)
class CrossValidationReport:
    mae: float
    rmse: float
    bias: float
    n: int


def leave_one_out_cv(samples_xyz: np.ndarray, samples_val: np.ndarray, model: VariogramModel, cfg: NeighborhoodConfig) -> CrossValidationReport:
    preds: list[float] = []
    trues: list[float] = []
    for i in range(len(samples_val)):
        mask = np.ones(len(samples_val), dtype=bool)
        mask[i] = False
        kr = ordinary_kriging(samples_xyz[mask], samples_val[mask], samples_xyz[i], model, cfg)
        preds.append(float(kr.estimate))
        trues.append(float(samples_val[i]))
    e = np.array(preds) - np.array(trues)
    return CrossValidationReport(
        mae=float(np.mean(np.abs(e))),
        rmse=float(np.sqrt(np.mean(e**2))),
        bias=float(np.mean(e)),
        n=len(trues),
    )
