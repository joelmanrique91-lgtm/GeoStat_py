from __future__ import annotations

from dataclasses import asdict, dataclass
import math

import numpy as np
import pandas as pd

from .errors import VariographyError
from .variography_backend import compute_experimental_backend




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
    angular_tolerance: float | None = None,
    ang_tol_h: float | None = None,
    ang_tol_v: float | None = None,
    bandwidth: float = 0.0,
    seed: int = 42,
    max_points: int = 2000,
) -> ExperimentalVariogram:
    if angular_tolerance is None:
        angular_tolerance = float(ang_tol_h if ang_tol_h is not None else 90.0)

    clean = df[[x, y, z, value]].copy()
    clean[[x, y, z, value]] = clean[[x, y, z, value]].apply(pd.to_numeric, errors="coerce")
    clean = clean.dropna()
    if len(clean) < 3:
        raise VariographyError("Insuficientes datos válidos para variograma")

    downsampled = False
    if len(clean) > max_points:
        clean = clean.sort_values([x,y,z]).iloc[::max(1, int(len(clean)/max_points))].head(max_points)
        downsampled = True

    coords = clean[[x, y, z]].to_numpy(dtype=float)
    vals = clean[value].to_numpy(dtype=float)

    if not (-360.0 <= float(azimuth) <= 360.0 and -90.0 <= float(dip) <= 90.0):
        raise VariographyError("Dirección inválida (azimuth/dip).")
    if not (0.0 < float(angular_tolerance) <= 90.0):
        raise VariographyError("Tolerancia angular fuera de rango (0, 90].")
    if float(bandwidth) < 0.0:
        raise VariographyError("Band width no puede ser negativo.")

    backend_result = compute_experimental_backend(
        coords=coords,
        values=vals,
        lag=float(lag),
        n_lags=int(n_lags),
        max_distance=float(max_distance),
        lag_tolerance=None if lag_tolerance is None else float(lag_tolerance),
        azimuth=float(azimuth),
        dip=float(dip),
        angular_tolerance=float(angular_tolerance),
        band_width=float(bandwidth),
        band_height=float(bandwidth),
    )
    lag_centers = list(backend_result.lag_centers)
    npairs = list(backend_result.npairs)
    gamma = list(backend_result.gamma)
    if max(npairs) == 0:
        raise VariographyError("No hay pares para el variograma con la configuración dada")

    return ExperimentalVariogram(
        lag_centers=lag_centers,
        gamma=gamma,
        npairs=npairs,
        metadata={
            "n_points": int(len(clean)),
            "downsampled": downsampled,
            "direction": {"azimuth_deg": float(azimuth), "dip_deg": float(dip), "angular_tolerance_deg": float(angular_tolerance), "band_width": float(bandwidth), "band_height": float(bandwidth)},
            "backend": backend_result.backend_used,
            "backend_warnings": list(backend_result.warnings),
        },
    )


def fit_variogram_model(exp: ExperimentalVariogram, model_type: str = "spherical", min_pairs: int = 5) -> VariogramModel:
    if model_type not in {"spherical", "exponential", "gaussian"}:
        raise VariographyError("Modelo no soportado")

    mask = [i for i, (g, p) in enumerate(zip(exp.gamma, exp.npairs)) if p >= min_pairs and math.isfinite(g)]
    if len(mask) < 2:
        raise VariographyError("No hay lags suficientes para ajustar")

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
        raise VariographyError("Fallo el ajuste del variograma")
    return best[1]
