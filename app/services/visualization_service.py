"""Data-preparation helpers for dashboards, spatial views, swaths and variograms."""

from __future__ import annotations

from dataclasses import dataclass
import math
import sys

from app.services.variography_geometry import DirectionalConfig
from app.utils.paths import PROJECT_ROOT

@dataclass
class SpatialDataBundle:
    x: list[float]
    y: list[float]
    z: list[float]
    target: list[float]
    source_points: int
    plotted_points: int
    downsampled: bool
    target_label: str = "Target"
    target_tick_positions: list[float] | None = None
    target_tick_labels: list[str] | None = None


@dataclass
class Spatial3DDataBundle:
    x: list[float]
    y: list[float]
    z: list[float]
    color_values: list[float]
    point_count_original: int
    point_count_rendered: int
    downsampling_applied: bool
    color_mode: str
    color_label: str
    color_tick_positions: list[float] | None = None
    color_tick_labels: list[str] | None = None


@dataclass
class SwathSeries:
    axis: str
    centers: list[float]
    means: list[float]
    counts: list[int]


@dataclass
class VariogramResult:
    lag_centers: list[float]
    gamma_values: list[float]
    pair_counts: list[int]
    source_points: int
    used_points: int
    downsampled: bool
    backend_used: str = "numpy"
    backend_warnings: list[str] | None = None


def _downsample_dataframe(dataframe, max_points: int, random_state: int = 42):
    if len(dataframe) <= max_points:
        return dataframe, False
    return dataframe.sample(n=max_points, random_state=random_state), True


def prepare_spatial_sections(
    dataframe,
    x_col: str,
    y_col: str,
    z_col: str,
    target_col: str,
    max_points: int = 20000,
    allow_categorical_target: bool = False,
) -> SpatialDataBundle:
    import pandas as pd

    required = [x_col, y_col, z_col, target_col]
    missing = [column for column in required if column not in dataframe.columns]
    if missing:
        raise ValueError(f"Columnas faltantes para secciones: {', '.join(missing)}")
    if not allow_categorical_target and not pd.api.types.is_numeric_dtype(dataframe[target_col]):
        raise ValueError("Target no numérico para secciones espaciales.")
    clean = dataframe[required].dropna()
    if clean.empty:
        raise ValueError("No hay datos válidos para secciones espaciales.")
    source_points = len(clean)
    sampled, downsampled = _downsample_dataframe(clean, max_points=max_points)

    target_tick_positions: list[float] | None = None
    target_tick_labels: list[str] | None = None
    target_label = "Target"
    if pd.api.types.is_numeric_dtype(sampled[target_col]):
        plotted_target = sampled[target_col].astype(float).tolist()
    else:
        categorical = sampled[target_col].astype("category")
        plotted_target = categorical.cat.codes.astype(float).tolist()
        categories = [str(cat) for cat in categorical.cat.categories]
        target_tick_positions = [float(idx) for idx in range(len(categories))]
        target_tick_labels = categories
        target_label = "Target (categorías)"

    return SpatialDataBundle(
        x=sampled[x_col].astype(float).tolist(),
        y=sampled[y_col].astype(float).tolist(),
        z=sampled[z_col].astype(float).tolist(),
        target=plotted_target,
        source_points=source_points,
        plotted_points=len(sampled),
        downsampled=downsampled,
        target_label=target_label,
        target_tick_positions=target_tick_positions,
        target_tick_labels=target_tick_labels,
    )


def prepare_spatial_3d_cloud(
    dataframe,
    x_col: str,
    y_col: str,
    z_col: str,
    color_col: str,
    max_points: int = 40000,
    allow_categorical_color: bool = False,
) -> Spatial3DDataBundle:
    import pandas as pd

    required = [x_col, y_col, z_col, color_col]
    missing = [column for column in required if column not in dataframe.columns]
    if missing:
        raise ValueError(f"Columnas faltantes para nube 3D: {', '.join(missing)}")
    if not allow_categorical_color and not pd.api.types.is_numeric_dtype(dataframe[color_col]):
        raise ValueError("Color no numérico para nube 3D.")

    clean = dataframe[required].dropna()
    if clean.empty:
        raise ValueError("No hay datos válidos para nube 3D.")

    point_count_original = len(clean)
    sampled, downsampled = _downsample_dataframe(clean, max_points=max_points)

    color_tick_positions: list[float] | None = None
    color_tick_labels: list[str] | None = None
    color_mode = "numeric"
    if pd.api.types.is_numeric_dtype(sampled[color_col]):
        color_values = sampled[color_col].astype(float).tolist()
    else:
        categorical = sampled[color_col].astype("category")
        color_values = categorical.cat.codes.astype(float).tolist()
        categories = [str(cat) for cat in categorical.cat.categories]
        color_tick_positions = [float(idx) for idx in range(len(categories))]
        color_tick_labels = categories
        color_mode = "categorical"

    return Spatial3DDataBundle(
        x=sampled[x_col].astype(float).tolist(),
        y=sampled[y_col].astype(float).tolist(),
        z=sampled[z_col].astype(float).tolist(),
        color_values=color_values,
        point_count_original=point_count_original,
        point_count_rendered=len(sampled),
        downsampling_applied=downsampled,
        color_mode=color_mode,
        color_label=color_col,
        color_tick_positions=color_tick_positions,
        color_tick_labels=color_tick_labels,
    )


def compute_swath_series(dataframe, axis_col: str, target_col: str, bins: int = 20) -> SwathSeries:
    import pandas as pd

    if axis_col not in dataframe.columns or target_col not in dataframe.columns:
        raise ValueError(f"Columnas faltantes para swath: {axis_col}, {target_col}")
    if bins < 3:
        raise ValueError("El número de bins debe ser >= 3.")
    if not pd.api.types.is_numeric_dtype(dataframe[target_col]):
        raise ValueError("Target no numérico para swath.")

    clean = dataframe[[axis_col, target_col]].dropna().copy()
    if clean.empty:
        raise ValueError("No hay datos válidos para swath.")

    min_val = float(clean[axis_col].min())
    max_val = float(clean[axis_col].max())
    if min_val == max_val:
        max_val += 1e-6
    edges = [min_val + idx * (max_val - min_val) / bins for idx in range(bins + 1)]
    clean["_bin"] = pd.cut(clean[axis_col], bins=edges, include_lowest=True, duplicates="drop")
    grouped = clean.groupby("_bin", observed=False)[target_col]

    intervals = list(grouped.mean().index)
    centers = [float((interval.left + interval.right) / 2.0) for interval in intervals]
    means = [float(value) if pd.notna(value) else math.nan for value in grouped.mean().tolist()]
    counts = grouped.count().astype(int).tolist()
    return SwathSeries(axis=axis_col, centers=centers, means=means, counts=counts)


def compute_experimental_variogram(
    dataframe,
    x_col: str,
    y_col: str,
    z_col: str,
    target_col: str,
    lag: float,
    n_lags: int,
    max_distance: float,
    lag_tolerance: float | None = None,
    azimuth: float = 0.0,
    dip: float = 0.0,
    ang_tol_h: float = 90.0,
    ang_tol_v: float = 90.0,
    band_width: float = 0.0,
    band_height: float = 0.0,
    max_points: int = 2500,
) -> VariogramResult:
    import pandas as pd
    import numpy as np

    required = [x_col, y_col, z_col, target_col]
    missing = [column for column in required if column not in dataframe.columns]
    if missing:
        raise ValueError(f"Columnas faltantes para variograma: {', '.join(missing)}")
    if lag <= 0 or n_lags <= 0 or max_distance <= 0:
        raise ValueError("Parámetros de variograma inválidos: lag, n_lags y max_distance deben ser > 0.")
    if lag_tolerance is not None and float(lag_tolerance) <= 0:
        raise ValueError("lag_tolerance debe ser > 0.")
    if not pd.api.types.is_numeric_dtype(dataframe[target_col]):
        raise ValueError("Target no numérico para variograma.")

    clean = dataframe[required].dropna()
    if len(clean) < 3:
        raise ValueError("No hay suficientes datos para calcular variograma experimental.")
    source_points = len(clean)
    sampled, downsampled = _downsample_dataframe(clean, max_points=max_points)

    coords = sampled[[x_col, y_col, z_col]].to_numpy(dtype=float)
    values = sampled[target_col].to_numpy(dtype=float)
    n_records = len(coords)

    lag_window = float(lag_tolerance) if lag_tolerance is not None else float(lag) * 0.5
    lag_window = max(1e-9, lag_window)
    direction = DirectionalConfig(
        azimuth_deg=float(azimuth),
        dip_deg=float(dip),
        azimuth_tolerance_deg=float(ang_tol_h),
        dip_tolerance_deg=float(ang_tol_v),
        band_width=float(band_width),
        band_height=float(band_height),
    )
    errors = direction.validate()
    if errors:
        raise ValueError("Configuración direccional inválida: " + "; ".join(errors))

    src_path = PROJECT_ROOT / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))
    from mining_geostat.variography_backend import compute_experimental_backend

    backend = compute_experimental_backend(
        coords=coords,
        values=values,
        lag=float(lag),
        n_lags=int(n_lags),
        max_distance=float(max_distance),
        azimuth=float(azimuth),
        dip=float(dip),
        ang_tol_h=float(ang_tol_h),
        ang_tol_v=float(ang_tol_v),
        band_width=float(band_width),
        band_height=float(band_height),
    )
    lag_centers = list(backend.lag_centers)
    gammas = list(backend.gamma)
    pairs = list(backend.npairs)

    if max(pairs, default=0) == 0:
        raise ValueError("No se encontraron pares dentro de max_distance para el variograma.")

    return VariogramResult(
        lag_centers=lag_centers,
        gamma_values=gammas,
        pair_counts=pairs,
        source_points=source_points,
        used_points=len(sampled),
        downsampled=downsampled,
        backend_used=str(backend.backend_used),
        backend_warnings=list(backend.warnings),
    )
