"""Data-preparation helpers for dashboards, spatial views, swaths and variograms."""

from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass
class SpatialDataBundle:
    x: list[float]
    y: list[float]
    z: list[float]
    target: list[float]


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


def prepare_spatial_sections(dataframe, x_col: str, y_col: str, z_col: str, target_col: str) -> SpatialDataBundle:
    import pandas as pd

    required = [x_col, y_col, z_col, target_col]
    missing = [column for column in required if column not in dataframe.columns]
    if missing:
        raise ValueError(f"Columnas faltantes para secciones: {', '.join(missing)}")
    if not pd.api.types.is_numeric_dtype(dataframe[target_col]):
        raise ValueError("Target no numérico para secciones espaciales.")

    clean = dataframe[required].dropna()
    if clean.empty:
        raise ValueError("No hay datos válidos para secciones espaciales.")

    return SpatialDataBundle(
        x=clean[x_col].astype(float).tolist(),
        y=clean[y_col].astype(float).tolist(),
        z=clean[z_col].astype(float).tolist(),
        target=clean[target_col].astype(float).tolist(),
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
) -> VariogramResult:
    import pandas as pd

    required = [x_col, y_col, z_col, target_col]
    missing = [column for column in required if column not in dataframe.columns]
    if missing:
        raise ValueError(f"Columnas faltantes para variograma: {', '.join(missing)}")
    if lag <= 0 or n_lags <= 0 or max_distance <= 0:
        raise ValueError("Parámetros de variograma inválidos: lag, n_lags y max_distance deben ser > 0.")
    if not pd.api.types.is_numeric_dtype(dataframe[target_col]):
        raise ValueError("Target no numérico para variograma.")

    clean = dataframe[required].dropna()
    if len(clean) < 3:
        raise ValueError("No hay suficientes datos para calcular variograma experimental.")

    records = [
        (float(row[x_col]), float(row[y_col]), float(row[z_col]), float(row[target_col]))
        for _, row in clean.iterrows()
    ]

    dist_acc: list[list[float]] = [[] for _ in range(n_lags)]
    for i in range(len(records) - 1):
        x0, y0, z0, v0 = records[i]
        for j in range(i + 1, len(records)):
            x1, y1, z1, v1 = records[j]
            d = math.sqrt((x1 - x0) ** 2 + (y1 - y0) ** 2 + (z1 - z0) ** 2)
            if d > max_distance:
                continue
            idx = int(d // lag)
            if 0 <= idx < n_lags:
                dist_acc[idx].append(0.5 * (v1 - v0) ** 2)

    lag_centers, gammas, pairs = [], [], []
    for idx in range(n_lags):
        lag_centers.append((idx + 1) * lag)
        pair_count = len(dist_acc[idx])
        pairs.append(pair_count)
        gammas.append(sum(dist_acc[idx]) / pair_count if pair_count else math.nan)

    if max(pairs, default=0) == 0:
        raise ValueError("No se encontraron pares dentro de max_distance para el variograma.")

    return VariogramResult(lag_centers=lag_centers, gamma_values=gammas, pair_counts=pairs)
