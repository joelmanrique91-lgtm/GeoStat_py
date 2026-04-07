from __future__ import annotations

from dataclasses import asdict, dataclass
import math

import numpy as np
import pandas as pd

try:
    from skgstat import Variogram as SKGVariogram
except Exception:  # pragma: no cover - optional backend
    SKGVariogram = None


@dataclass(frozen=True)
class DirectionalConfig:
    azimuth_deg: float
    dip_deg: float
    azimuth_tolerance_deg: float
    dip_tolerance_deg: float
    band_width: float
    band_height: float

    def validate(self) -> list[str]:
        errs: list[str] = []
        if not (-360.0 <= self.azimuth_deg <= 360.0):
            errs.append("azimuth fuera de rango")
        if not (-90.0 <= self.dip_deg <= 90.0):
            errs.append("dip fuera de rango")
        if not (0.0 < self.azimuth_tolerance_deg <= 90.0):
            errs.append("ang_tol_h fuera de rango")
        if not (0.0 < self.dip_tolerance_deg <= 90.0):
            errs.append("ang_tol_v fuera de rango")
        if self.band_width < 0 or self.band_height < 0:
            errs.append("bandwidth/bandheight no pueden ser negativos")
        return errs


def _unit_direction(azimuth_deg: float, dip_deg: float) -> tuple[float, float, float]:
    az = math.radians(float(azimuth_deg))
    dip = math.radians(float(dip_deg))
    c = math.cos(dip)
    return c * math.cos(az), c * math.sin(az), math.sin(dip)


def _matches_direction(dx: float, dy: float, dz: float, cfg: DirectionalConfig) -> bool:
    ux, uy, uz = _unit_direction(cfg.azimuth_deg, cfg.dip_deg)
    vnorm = math.sqrt(dx * dx + dy * dy + dz * dz)
    if vnorm < 1e-12:
        return False
    dot = abs((dx * ux + dy * uy + dz * uz) / vnorm)
    dot = max(-1.0, min(1.0, dot))
    ang = math.degrees(math.acos(dot))
    if ang > cfg.azimuth_tolerance_deg:
        return False
    horizontal = math.sqrt(dx * dx + dy * dy)
    pair_dip = math.degrees(math.atan2(dz, horizontal))
    if min(abs(pair_dip - cfg.dip_deg), abs(-pair_dip - cfg.dip_deg)) > cfg.dip_tolerance_deg:
        return False
    proj = dx * ux + dy * uy + dz * uz
    perp = math.sqrt(max(0.0, dx * dx + dy * dy + dz * dz - proj * proj))
    if cfg.band_width > 0.0 and perp > cfg.band_width * 0.5:
        return False
    if cfg.band_height > 0.0 and abs(dz) > cfg.band_height * 0.5:
        return False
    return True


@dataclass(frozen=True)
class ExperimentalVariogram:
    lag_centers: list[float]
    gamma: list[float]
    npairs: list[int]
    metadata: dict[str, object]


@dataclass(frozen=True)
class VariogramModel:
    model_type: str
    nugget: float
    sill: float
    range_: float

    def semivariance(self, h: float) -> float:
        h = max(0.0, float(h))
        c = max(0.0, self.sill - self.nugget)
        if self.model_type == "spherical":
            if h >= self.range_:
                return self.sill
            r = h / self.range_
            return self.nugget + c * (1.5 * r - 0.5 * r**3)
        if self.model_type == "exponential":
            return self.nugget + c * (1.0 - math.exp(-3.0 * h / self.range_))
        if self.model_type == "gaussian":
            return self.nugget + c * (1.0 - math.exp(-3.0 * (h / self.range_) ** 2))
        raise ValueError(f"Modelo no soportado: {self.model_type}")


def _distance(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.linalg.norm(a - b))


def experimental_variogram_3d(
    df: pd.DataFrame,
    *,
    x: str,
    y: str,
    z: str,
    value: str,
    lag: float,
    n_lags: int,
    max_distance: float,
    azimuth: float = 0.0,
    dip: float = 0.0,
    ang_tol_h: float = 90.0,
    ang_tol_v: float = 90.0,
    bandwidth: float = 0.0,
    seed: int = 42,
    max_points: int = 2000,
) -> ExperimentalVariogram:
    clean = df[[x, y, z, value]].copy()
    clean[[x, y, z, value]] = clean[[x, y, z, value]].apply(pd.to_numeric, errors="coerce")
    clean = clean.dropna()
    if len(clean) < 3:
        raise ValueError("Insuficientes datos válidos para variograma")

    downsampled = False
    if len(clean) > max_points:
        clean = clean.sample(n=max_points, random_state=seed)
        downsampled = True

    coords = clean[[x, y, z]].to_numpy(dtype=float)
    vals = clean[value].to_numpy(dtype=float)

    direction = DirectionalConfig(float(azimuth), float(dip), float(ang_tol_h), float(ang_tol_v), float(bandwidth), float(bandwidth))
    errs = direction.validate()
    if errs:
        raise ValueError("; ".join(errs))

    omnidirectional = (
        abs(float(azimuth)) < 1e-9
        and abs(float(dip)) < 1e-9
        and float(ang_tol_h) >= 89.9
        and float(ang_tol_v) >= 89.9
        and float(bandwidth) <= 1e-9
    )
    if omnidirectional and SKGVariogram is not None:
        estimator = SKGVariogram(
            coords,
            vals,
            n_lags=n_lags,
            maxlag=float(max_distance),
            bin_func="even",
            normalize=False,
            use_nugget=True,
        )
        lag_centers = [float(v) for v in estimator.bins.tolist()]
        gamma = [float(v) for v in estimator.experimental.tolist()]
        npairs = [int(v) for v in estimator.bin_count.tolist()]
        if max(npairs, default=0) == 0:
            raise ValueError("No hay pares para el variograma con la configuración dada")
        return ExperimentalVariogram(
            lag_centers=lag_centers,
            gamma=gamma,
            npairs=npairs,
            metadata={"n_points": int(len(clean)), "downsampled": downsampled, "direction": asdict(direction), "backend": "scikit-gstat"},
        )

    n_points = len(coords)
    i_idx, j_idx = np.triu_indices(n_points, k=1)
    deltas = coords[j_idx] - coords[i_idx]
    dx = deltas[:, 0]
    dy = deltas[:, 1]
    dz = deltas[:, 2]

    d = np.sqrt(dx * dx + dy * dy + dz * dz)
    valid = (d > 0.0) & (d <= float(max_distance))

    ux, uy, uz = _unit_direction(direction.azimuth_deg, direction.dip_deg)
    dot = np.abs((dx * ux + dy * uy + dz * uz) / np.maximum(d, 1e-12))
    dot = np.clip(dot, -1.0, 1.0)
    ang = np.degrees(np.arccos(dot))
    valid &= ang <= direction.azimuth_tolerance_deg

    horizontal = np.sqrt(dx * dx + dy * dy)
    pair_dip = np.degrees(np.arctan2(dz, horizontal))
    dip_diff = np.minimum(np.abs(pair_dip - direction.dip_deg), np.abs(-pair_dip - direction.dip_deg))
    valid &= dip_diff <= direction.dip_tolerance_deg

    if direction.band_width > 0.0:
        proj = dx * ux + dy * uy + dz * uz
        perp = np.sqrt(np.maximum(0.0, d * d - proj * proj))
        valid &= perp <= direction.band_width * 0.5
    if direction.band_height > 0.0:
        valid &= np.abs(dz) <= direction.band_height * 0.5

    if not np.any(valid):
        raise ValueError("No hay pares para el variograma con la configuración dada")

    d_valid = d[valid]
    semivar = 0.5 * np.square(vals[j_idx[valid]] - vals[i_idx[valid]])
    bins = np.rint((d_valid / lag) - 1.0).astype(int)
    in_range = (bins >= 0) & (bins < n_lags)

    gamma_sum = np.bincount(bins[in_range], weights=semivar[in_range], minlength=n_lags)
    npairs_arr = np.bincount(bins[in_range], minlength=n_lags)

    lag_centers = [float((k + 1) * lag) for k in range(n_lags)]
    npairs = npairs_arr.astype(int).tolist()
    gamma = [
        float(gamma_sum[k] / npairs_arr[k]) if npairs_arr[k] > 0 else math.nan
        for k in range(n_lags)
    ]
    if max(npairs) == 0:
        raise ValueError("No hay pares para el variograma con la configuración dada")

    return ExperimentalVariogram(
        lag_centers=lag_centers,
        gamma=gamma,
        npairs=npairs,
        metadata={"n_points": int(len(clean)), "downsampled": downsampled, "direction": asdict(direction), "backend": "numpy"},
    )


def fit_variogram_model(exp: ExperimentalVariogram, model_type: str = "spherical", min_pairs: int = 5) -> VariogramModel:
    if model_type not in {"spherical", "exponential", "gaussian"}:
        raise ValueError("Modelo no soportado")

    mask = [i for i, (g, p) in enumerate(zip(exp.gamma, exp.npairs)) if p >= min_pairs and math.isfinite(g)]
    if len(mask) < 2:
        raise ValueError("No hay lags suficientes para ajustar")

    h = np.array([exp.lag_centers[i] for i in mask], dtype=float)
    g = np.array([exp.gamma[i] for i in mask], dtype=float)
    w = np.array([exp.npairs[i] for i in mask], dtype=float)

    nugget_candidates = np.linspace(0.0, float(np.nanmin(g)), 6)
    sill_candidates = np.linspace(float(np.nanmax(g) * 0.7), float(np.nanmax(g) * 1.5), 12)
    range_candidates = np.linspace(float(np.nanmax(h) * 0.3), float(np.nanmax(h) * 1.5), 16)

    best: tuple[float, VariogramModel] | None = None
    for nugget in nugget_candidates:
        for sill in sill_candidates:
            if sill < nugget:
                continue
            for range_ in range_candidates:
                model = VariogramModel(model_type=model_type, nugget=float(nugget), sill=float(sill), range_=max(1e-6, float(range_)))
                pred = np.array([model.semivariance(v) for v in h], dtype=float)
                err = float(np.average((pred - g) ** 2, weights=w))
                if best is None or err < best[0]:
                    best = (err, model)

    if best is None:
        raise ValueError("Fallo el ajuste del variograma")
    return best[1]
