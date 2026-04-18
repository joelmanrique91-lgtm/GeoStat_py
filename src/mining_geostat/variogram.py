from __future__ import annotations

from dataclasses import asdict, dataclass
import math

import numpy as np
import pandas as pd

from .variography_backend import compute_experimental_backend


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
    lag_tolerance: float | None = None,
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

    backend_result = compute_experimental_backend(
        coords=coords,
        values=vals,
        lag=float(lag),
        n_lags=int(n_lags),
        max_distance=float(max_distance),
        lag_tolerance=None if lag_tolerance is None else float(lag_tolerance),
        azimuth=float(azimuth),
        dip=float(dip),
        ang_tol_h=float(ang_tol_h),
        ang_tol_v=float(ang_tol_v),
        band_width=float(bandwidth),
        band_height=float(bandwidth),
    )
    lag_centers = list(backend_result.lag_centers)
    npairs = list(backend_result.npairs)
    gamma = list(backend_result.gamma)
    if max(npairs) == 0:
        raise ValueError("No hay pares para el variograma con la configuración dada")

    return ExperimentalVariogram(
        lag_centers=lag_centers,
        gamma=gamma,
        npairs=npairs,
        metadata={
            "n_points": int(len(clean)),
            "downsampled": downsampled,
            "direction": asdict(direction),
            "backend": backend_result.backend_used,
            "backend_warnings": list(backend_result.warnings),
        },
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
