from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np
from scipy.spatial import cKDTree

try:
    from numba import njit
except Exception:  # pragma: no cover
    njit = None

try:
    from skgstat import Variogram as SKGVariogram
except Exception:  # pragma: no cover
    SKGVariogram = None


if njit is not None:
    @njit(cache=True)
    def _accumulate_semivariance_numba(values: np.ndarray, i_idx: np.ndarray, j_idx: np.ndarray) -> np.ndarray:
        out = np.empty(i_idx.shape[0], dtype=np.float64)
        for k in range(i_idx.shape[0]):
            d = values[i_idx[k]] - values[j_idx[k]]
            out[k] = 0.5 * d * d
        return out
else:
    def _accumulate_semivariance_numba(values: np.ndarray, i_idx: np.ndarray, j_idx: np.ndarray) -> np.ndarray:
        return 0.5 * np.square(values[j_idx] - values[i_idx])


@dataclass(frozen=True)
class VariographyBackendResult:
    lag_centers: list[float]
    gamma: list[float]
    npairs: list[int]
    backend_used: str
    warnings: list[str]


def _unit_direction(azimuth_deg: float, dip_deg: float) -> tuple[float, float, float]:
    az = math.radians(float(azimuth_deg))
    dip = math.radians(float(dip_deg))
    c = math.cos(dip)
    return c * math.cos(az), c * math.sin(az), math.sin(dip)


def compute_experimental_backend(
    *,
    coords: np.ndarray,
    values: np.ndarray,
    lag: float,
    n_lags: int,
    max_distance: float,
    azimuth: float = 0.0,
    dip: float = 0.0,
    ang_tol_h: float = 90.0,
    ang_tol_v: float = 90.0,
    band_width: float = 0.0,
    band_height: float = 0.0,
    lag_tolerance: float | None = None,
    small_dataset_threshold: int = 1200,
    pair_chunk_size: int = 200_000,
) -> VariographyBackendResult:
    warnings: list[str] = []
    omnidirectional = (
        abs(float(azimuth)) < 1e-9
        and abs(float(dip)) < 1e-9
        and float(ang_tol_h) >= 89.9
        and float(ang_tol_v) >= 89.9
        and float(band_width) <= 1e-9
        and float(band_height) <= 1e-9
    )
    if omnidirectional and SKGVariogram is not None:
        estimator = SKGVariogram(coords, values, n_lags=n_lags, maxlag=float(max_distance), bin_func="even", normalize=False, use_nugget=True)
        lag_centers = [float(v) for v in estimator.bins.tolist()]
        gamma = [float(v) for v in estimator.experimental.tolist()]
        npairs = [int(v) for v in estimator.bin_count.tolist()]
        return VariographyBackendResult(lag_centers=lag_centers, gamma=gamma, npairs=npairs, backend_used="scikit-gstat", warnings=warnings)
    if omnidirectional and SKGVariogram is None:
        warnings.append("scikit-gstat_unavailable_fallback_numpy")

    n_points = len(coords)
    use_dense_pairs = n_points <= int(small_dataset_threshold)
    if use_dense_pairs:
        i_idx, j_idx = np.triu_indices(n_points, k=1)
    else:
        tree = cKDTree(coords)
        pair_set = tree.query_pairs(r=float(max_distance), output_type="set")
        if not pair_set:
            raise ValueError("No hay pares para el variograma con la configuración dada")
        # Deterministic ordering for reproducibility.
        ordered_pairs = np.array(sorted(pair_set), dtype=np.int64)
        i_idx = ordered_pairs[:, 0]
        j_idx = ordered_pairs[:, 1]
        warnings.append("pair_selection_kdtree")

    deltas = coords[j_idx] - coords[i_idx]
    dx = deltas[:, 0]
    dy = deltas[:, 1]
    dz = deltas[:, 2]
    d = np.sqrt(dx * dx + dy * dy + dz * dz)
    valid = (d > 0.0) & (d <= float(max_distance))

    ux, uy, uz = _unit_direction(azimuth, dip)
    dot = np.abs((dx * ux + dy * uy + dz * uz) / np.maximum(d, 1e-12))
    dot = np.clip(dot, -1.0, 1.0)
    ang = np.degrees(np.arccos(dot))
    valid &= ang <= float(ang_tol_h)
    horizontal = np.sqrt(dx * dx + dy * dy)
    pair_dip = np.degrees(np.arctan2(dz, horizontal))
    dip_diff = np.minimum(np.abs(pair_dip - float(dip)), np.abs(-pair_dip - float(dip)))
    valid &= dip_diff <= float(ang_tol_v)
    if float(band_width) > 0.0:
        proj = dx * ux + dy * uy + dz * uz
        perp = np.sqrt(np.maximum(0.0, d * d - proj * proj))
        valid &= perp <= float(band_width) * 0.5
    if float(band_height) > 0.0:
        valid &= np.abs(dz) <= float(band_height) * 0.5

    if not np.any(valid):
        raise ValueError("No hay pares para el variograma con la configuración dada")
    d_valid = d[valid]
    i_valid = i_idx[valid].astype(np.int64)
    j_valid = j_idx[valid].astype(np.int64)
    semivar = np.empty_like(d_valid, dtype=np.float64)
    values64 = values.astype(np.float64)
    chunk = max(10_000, int(pair_chunk_size))
    for start in range(0, d_valid.shape[0], chunk):
        end = min(start + chunk, d_valid.shape[0])
        semivar[start:end] = _accumulate_semivariance_numba(values64, i_valid[start:end], j_valid[start:end])

    lag_tol = float(lag_tolerance) if lag_tolerance is not None else float(lag) * 0.5
    lag_tol = max(1e-12, lag_tol)
    nearest_lag_index = np.rint((d_valid / float(lag)) - 1.0).astype(int)
    lag_center_for_pair = (nearest_lag_index + 1).astype(float) * float(lag)
    in_range = (
        (nearest_lag_index >= 0)
        & (nearest_lag_index < int(n_lags))
        & (np.abs(d_valid - lag_center_for_pair) <= lag_tol)
    )
    gamma_sum = np.bincount(nearest_lag_index[in_range], weights=semivar[in_range], minlength=int(n_lags))
    npairs_arr = np.bincount(nearest_lag_index[in_range], minlength=int(n_lags))
    lag_centers = [float((k + 1) * lag) for k in range(int(n_lags))]
    npairs = npairs_arr.astype(int).tolist()
    gamma = [float(gamma_sum[k] / npairs_arr[k]) if npairs_arr[k] > 0 else math.nan for k in range(int(n_lags))]
    backend_used = "numpy" if use_dense_pairs else "numpy+kdtree"
    return VariographyBackendResult(lag_centers=lag_centers, gamma=gamma, npairs=npairs, backend_used=backend_used, warnings=warnings)
