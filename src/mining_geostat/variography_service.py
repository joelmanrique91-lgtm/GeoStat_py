from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np

from .errors import VariographyError
from .variography_backend import VariographyBackendResult, compute_experimental_backend


@dataclass(frozen=True)
class DirectionalCone:
    azimuth_deg: float = 0.0
    dip_deg: float = 0.0
    angular_tolerance_deg: float = 90.0
    band_width: float = 0.0
    band_height: float = 0.0


def direction_vector_from_angles(azimuth_deg: float, dip_deg: float) -> np.ndarray:
    az = math.radians(float(azimuth_deg))
    dip = math.radians(float(dip_deg))
    c = math.cos(dip)
    return np.array([c * math.cos(az), c * math.sin(az), math.sin(dip)], dtype=float)


def is_pair_within_direction(h_vector: np.ndarray, direction_vector: np.ndarray, angular_tolerance_deg: float) -> bool:
    h_norm = float(np.linalg.norm(h_vector))
    d_norm = float(np.linalg.norm(direction_vector))
    if h_norm <= 1e-12 or d_norm <= 1e-12:
        return False
    cos_theta = float(np.dot(h_vector, direction_vector) / (h_norm * d_norm))
    cos_theta = abs(max(-1.0, min(1.0, cos_theta)))
    theta = math.degrees(math.acos(cos_theta))
    return theta <= float(angular_tolerance_deg)


def compute_experimental_variogram(*, coords: np.ndarray, values: np.ndarray, lag: float, n_lags: int, max_distance: float,
                                   lag_tolerance: float | None = None, direction: DirectionalCone | None = None) -> VariographyBackendResult:
    if lag <= 0 or n_lags <= 0 or max_distance <= 0:
        raise VariographyError("Parámetros inválidos para variograma experimental.")
    direction = direction or DirectionalCone()
    if not (0.0 < float(direction.angular_tolerance_deg) <= 90.0):
        raise VariographyError("La tolerancia angular debe estar en (0, 90].")
    return compute_experimental_backend(
        coords=coords,
        values=values,
        lag=float(lag),
        n_lags=int(n_lags),
        max_distance=float(max_distance),
        azimuth=float(direction.azimuth_deg),
        dip=float(direction.dip_deg),
        angular_tolerance=float(direction.angular_tolerance_deg),
        band_width=float(direction.band_width),
        band_height=float(direction.band_height),
        lag_tolerance=lag_tolerance,
    )
