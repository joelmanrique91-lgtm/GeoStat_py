from __future__ import annotations

from dataclasses import dataclass

import numpy as np

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


def _select_neighbors(samples_xyz: np.ndarray, target_xyz: np.ndarray, cfg: NeighborhoodConfig) -> np.ndarray:
    d = np.linalg.norm(samples_xyz - target_xyz[None, :], axis=1)
    idx = np.argsort(d)
    if cfg.search_radius is not None:
        idx = np.array([i for i in idx if d[i] <= cfg.search_radius], dtype=int)
    idx = idx[: cfg.max_samples]
    if len(idx) < cfg.min_samples:
        raise ValueError("Vecindario insuficiente para kriging")
    return idx


def _cov(model: VariogramModel, h: float) -> float:
    return float(model.sill - model.semivariance(h))




def _solve_linear_system(k: np.ndarray, rhs: np.ndarray, numerical_nugget: float) -> np.ndarray:
    try:
        l = np.linalg.cholesky(k)
        y = np.linalg.solve(l, rhs)
        return np.linalg.solve(l.T, y)
    except np.linalg.LinAlgError:
        pass
    try:
        k2 = k.copy()
        k2[np.diag_indices_from(k2)] += float(numerical_nugget)
        l = np.linalg.cholesky(k2)
        y = np.linalg.solve(l, rhs)
        return np.linalg.solve(l.T, y)
    except np.linalg.LinAlgError:
        return np.linalg.pinv(k) @ rhs

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
    cov_nn = np.vectorize(lambda h: _cov(model, float(h)))(dist_nn)
    k = np.zeros((n + 1, n + 1), dtype=float)
    k[:n,:n]=cov_nn
    k[:n, n] = 1.0
    k[n, :n] = 1.0

    rhs = np.zeros(n + 1, dtype=float)
    dist_nt = np.linalg.norm(xyz - target_xyz[None, :], axis=1)
    rhs[:n] = np.vectorize(lambda h: _cov(model, float(h)))(dist_nt)
    rhs[n] = 1.0

    sol = _solve_linear_system(k, rhs, cfg.numerical_nugget)
    w = sol[:n]
    mu = sol[n]
    estimate = float(np.dot(w, val))
    variance = float(model.sill - np.dot(w, rhs[:n]) - mu)
    return KrigingResult(estimate=estimate, variance=max(0.0, variance), n_used=n, weights=w.tolist(), backend_used="numpy")


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
    k = np.vectorize(lambda h: _cov(model, float(h)))(dist_nn)
    dist_nt = np.linalg.norm(xyz - target_xyz[None, :], axis=1)
    rhs = np.vectorize(lambda h: _cov(model, float(h)))(dist_nt)

    w = _solve_linear_system(k, rhs, cfg.numerical_nugget)
    estimate = float(mean + np.dot(w, (val - mean)))
    variance = float(model.sill - np.dot(w, rhs))
    return KrigingResult(estimate=estimate, variance=max(0.0, variance), n_used=n, weights=w.tolist(), backend_used="numpy")


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
    cov_nn = np.vectorize(lambda h: _cov(model, float(h)))(dist_nn)
    k = np.zeros((n + 1, n + 1), dtype=float)
    k[:n, :n] = cov_nn
    k[:n, n] = 1.0
    k[n, :n] = 1.0

    estimates = []
    variances = []
    weights = None
    for p in points:
        rhs = np.zeros(n + 1, dtype=float)
        dist_nt = np.linalg.norm(xyz - p[None, :], axis=1)
        rhs[:n] = np.vectorize(lambda h: _cov(model, float(h)))(dist_nt)
        rhs[n] = 1.0
        sol = _solve_linear_system(k, rhs, cfg.numerical_nugget)
        w = sol[:n]
        mu = sol[n]
        estimates.append(float(np.dot(w, val)))
        variances.append(float(model.sill - np.dot(w, rhs[:n]) - mu))
        if weights is None:
            weights = w.tolist()

    return KrigingResult(
        estimate=float(np.mean(estimates)),
        variance=max(0.0, float(np.mean(variances))),
        n_used=n,
        weights=weights or [],
        backend_used="numpy",
    )
