from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from statistics import NormalDist

from .kriging import NeighborhoodConfig, simple_kriging
from .variogram import VariogramModel


@dataclass(frozen=True)
class NormalScoreTransform:
    sorted_values: np.ndarray
    scores: np.ndarray

    def forward(self, values: np.ndarray) -> np.ndarray:
        return np.interp(values, self.sorted_values, self.scores)

    def inverse(self, scores: np.ndarray) -> np.ndarray:
        return np.interp(scores, self.scores, self.sorted_values)


def build_normal_score_transform(values: np.ndarray) -> NormalScoreTransform:
    sorted_vals = np.sort(values.astype(float))
    n = len(sorted_vals)
    probs = (np.arange(1, n + 1) - 0.5) / n
    nd = NormalDist()
    z = np.array([nd.inv_cdf(float(p)) for p in probs], dtype=float)
    return NormalScoreTransform(sorted_values=sorted_vals, scores=z)


def sequential_gaussian_simulation(
    sample_xyz: np.ndarray,
    sample_values: np.ndarray,
    grid_xyz: np.ndarray,
    model: VariogramModel,
    cfg: NeighborhoodConfig,
    seed: int = 1234,
) -> np.ndarray:
    rng = np.random.default_rng(seed)
    nst = build_normal_score_transform(sample_values)
    cond_xyz = sample_xyz.astype(float).copy()
    cond_ns = nst.forward(sample_values.astype(float))

    path = np.arange(len(grid_xyz))
    rng.shuffle(path)
    simulated_ns = np.zeros(len(grid_xyz), dtype=float)

    for idx in path:
        loc = grid_xyz[idx]
        kr = simple_kriging(cond_xyz, cond_ns, loc, model, cfg, mean=0.0)
        draw = rng.normal(loc=kr.estimate, scale=max(1e-9, np.sqrt(kr.variance)))
        simulated_ns[idx] = draw

        cond_xyz = np.vstack([cond_xyz, loc])
        cond_ns = np.concatenate([cond_ns, np.array([draw])])

    return nst.inverse(simulated_ns)
