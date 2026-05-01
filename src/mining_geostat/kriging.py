from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .errors import KrigingError
from .variogram import VariogramModel

try:
    from pykrige.ok3d import OrdinaryKriging3D
except Exception:  # pragma: no cover - optional backend
    OrdinaryKriging3D = None


@dataclass(frozen=True)
class NeighborhoodConfig:
    min_samples: int = 4
    max_samples: int = 16
    search_radius: float | None = None
    numerical_nugget: float = 1e-6


@dataclass(frozen=True)
class KrigingResult:
    estimate: float
    variance: float
    n_used: int
    weights: list[float]
    backend_used: str = "numpy"
    solver_path: str = "direct"
    jitter_used: float = 0.0
    condition_number: float = 0.0


def _select_neighbors(samples_xyz: np.ndarray, target_xyz: np.ndarray, cfg: NeighborhoodConfig) -> np.ndarray:
    d = np.linalg.norm(samples_xyz - target_xyz[None, :], axis=1)
    idx = np.argsort(d)
    if cfg.search_radius is not None:
        idx = np.array([i for i in idx if d[i] <= cfg.search_radius], dtype=int)
    idx = idx[: cfg.max_samples]
    if len(idx) < cfg.min_samples:
        raise KrigingError("Vecindario insuficiente para kriging")
    return idx


def _cov(model: VariogramModel, h: float | np.ndarray) -> float | np.ndarray:
    if np.isscalar(h):
        return float(model.sill - model.semivariance(float(h)))
    h_arr = np.asarray(h, dtype=float)
    semiv = np.fromiter((model.semivariance(float(v)) for v in h_arr.ravel()), dtype=float, count=h_arr.size).reshape(h_arr.shape)
    return model.sill - semiv


def _solve_linear_system(k: np.ndarray, rhs: np.ndarray, numerical_nugget: float) -> tuple[np.ndarray, str, float, float]:
    cond_number = float(np.linalg.cond(k))
    try:
        l = np.linalg.cholesky(k)
        y = np.linalg.solve(l, rhs)
        return np.linalg.solve(l.T, y), "cholesky", 0.0, cond_number
    except np.linalg.LinAlgError:
        pass
    jitter = float(max(numerical_nugget, 1e-12))
    try:
        k2 = k.copy()
        k2[np.diag_indices_from(k2)] += jitter
        l = np.linalg.cholesky(k2)
        y = np.linalg.solve(l, rhs)
        return np.linalg.solve(l.T, y), "cholesky+jitter", jitter, cond_number
    except np.linalg.LinAlgError:
        return np.linalg.pinv(k) @ rhs, "pinv", jitter, cond_number

def ordinary_kriging(
    samples_xyz: np.ndarray,
    samples_val: np.ndarray,
    target_xyz: np.ndarray,
    model: VariogramModel,
    cfg: NeighborhoodConfig,
) -> KrigingResult:
    idx = _select_neighbors(samples_xyz, target_xyz, cfg)
    xyz = samples_xyz[idx]
    val = samples_val[idx]
    n = len(idx)
    if OrdinaryKriging3D is not None:
        variogram_parameters = [float(model.sill - model.nugget), float(model.range_), float(model.nugget)]
        ok3d = OrdinaryKriging3D(
            x=xyz[:, 0],
            y=xyz[:, 1],
            z=xyz[:, 2],
            val=val,
            variogram_model=model.model_type,
            variogram_parameters=variogram_parameters,
            enable_plotting=False,
            exact_values=False,
            verbose=False,
        )
        estimate, variance = ok3d.execute("points", np.array([target_xyz[0]]), np.array([target_xyz[1]]), np.array([target_xyz[2]]))
        return KrigingResult(
            estimate=float(estimate[0]),
            variance=max(0.0, float(variance[0])),
            n_used=n,
            weights=[],
            backend_used="pykrige",
        )

    dist_nn = np.linalg.norm(xyz[:, None, :] - xyz[None, :, :], axis=2)
    cov_nn = _cov(model, dist_nn).astype(float)
    k = np.zeros((n + 1, n + 1), dtype=float)
    k[:n,:n]=cov_nn
    k[:n, n] = 1.0
    k[n, :n] = 1.0

    rhs = np.zeros(n + 1, dtype=float)
    dist_nt = np.linalg.norm(xyz - target_xyz[None, :], axis=1)
    rhs[:n] = _cov(model, dist_nt).astype(float)
    rhs[n] = 1.0

    sol, solver_path, jitter_used, condition_number = _solve_linear_system(k, rhs, cfg.numerical_nugget)
    w = sol[:n]
    mu = sol[n]
    estimate = float(np.dot(w, val))
    variance = float(model.sill - np.dot(w, rhs[:n]) - mu)
    return KrigingResult(estimate=estimate, variance=max(0.0, variance), n_used=n, weights=w.tolist(), backend_used="numpy", solver_path=solver_path, jitter_used=jitter_used, condition_number=condition_number)


def simple_kriging(
    samples_xyz: np.ndarray,
    samples_val: np.ndarray,
    target_xyz: np.ndarray,
    model: VariogramModel,
    cfg: NeighborhoodConfig,
    mean: float,
) -> KrigingResult:
    idx = _select_neighbors(samples_xyz, target_xyz, cfg)
    xyz = samples_xyz[idx]
    val = samples_val[idx]
    n = len(idx)

    dist_nn = np.linalg.norm(xyz[:, None, :] - xyz[None, :, :], axis=2)
    k = _cov(model, dist_nn).astype(float)
    dist_nt = np.linalg.norm(xyz - target_xyz[None, :], axis=1)
    rhs = _cov(model, dist_nt).astype(float)

    w, solver_path, jitter_used, condition_number = _solve_linear_system(k, rhs, cfg.numerical_nugget)
    estimate = float(mean + np.dot(w, (val - mean)))
    variance = float(model.sill - np.dot(w, rhs))
    return KrigingResult(estimate=estimate, variance=max(0.0, variance), n_used=n, weights=w.tolist(), backend_used="numpy", solver_path=solver_path, jitter_used=jitter_used, condition_number=condition_number)


def block_kriging(
    samples_xyz: np.ndarray,
    samples_val: np.ndarray,
    block_centroid_xyz: np.ndarray,
    model: VariogramModel,
    cfg: NeighborhoodConfig,
    block_size_xyz: tuple[float, float, float] = (10.0, 10.0, 5.0),
    discretization: tuple[int, int, int] = (2, 2, 2),
) -> KrigingResult:
    nx, ny, nz = discretization
    sx, sy, sz = block_size_xyz
    xs = np.linspace(-sx / 2, sx / 2, nx)
    ys = np.linspace(-sy / 2, sy / 2, ny)
    zs = np.linspace(-sz / 2, sz / 2, nz)

    points = np.array([[block_centroid_xyz[0] + i, block_centroid_xyz[1] + j, block_centroid_xyz[2] + k] for i in xs for j in ys for k in zs], dtype=float)

    idx = _select_neighbors(samples_xyz, block_centroid_xyz, cfg)
    xyz = samples_xyz[idx]
    val = samples_val[idx]
    n = len(idx)
    dist_nn = np.linalg.norm(xyz[:, None, :] - xyz[None, :, :], axis=2)
    cov_nn = _cov(model, dist_nn).astype(float)
    k = np.zeros((n + 1, n + 1), dtype=float)
    k[:n, :n] = cov_nn
    k[:n, n] = 1.0
    k[n, :n] = 1.0

    rhs_matrix = np.zeros((n + 1, points.shape[0]), dtype=float)
    dist_nt_all = np.linalg.norm(xyz[:, None, :] - points[None, :, :], axis=2)
    rhs_matrix[:n, :] = _cov(model, dist_nt_all).astype(float)
    rhs_matrix[n, :] = 1.0
    sol, solver_path, jitter_used, condition_number = _solve_linear_system(k, rhs_matrix, cfg.numerical_nugget)
    w_matrix = sol[:n, :]
    mu_vec = sol[n, :]
    estimates = np.dot(val, w_matrix)
    variances = model.sill - np.sum(w_matrix * rhs_matrix[:n, :], axis=0) - mu_vec

    return KrigingResult(
        estimate=float(np.mean(estimates)),
        variance=max(0.0, float(np.mean(variances))),
        n_used=n,
        weights=w_matrix[:, 0].tolist() if w_matrix.shape[1] else [],
        backend_used="numpy",
        solver_path=solver_path,
        jitter_used=jitter_used,
        condition_number=condition_number,
    )
