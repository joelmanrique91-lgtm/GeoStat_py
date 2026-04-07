"""End-to-end geoestatistical pipeline built on top of existing variography services.

Mother routines reused:
- compute_experimental_variogram (pairwise Matheron estimator + directional filter)
- auto_fit_wls/evaluate_model/evaluate_quality (theoretical fitting)
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math

import pandas as pd

from app.services.variogram_modeling_service import auto_fit_wls, evaluate_model, evaluate_quality
from app.services.visualization_service import compute_experimental_variogram


@dataclass(frozen=True)
class DataQualityReport:
    total_rows: int
    valid_rows: int
    usable_pct: float
    nulls_by_column: dict[str, int]
    duplicates_xyz_target: int
    warnings: list[str]


@dataclass(frozen=True)
class EDAReport:
    stats: dict[str, float]
    percentiles: dict[str, float]
    outlier_iqr_count: int
    suggested_top_cut: float


@dataclass(frozen=True)
class FittedVariogram:
    model_type: str
    nugget: float
    sill: float
    range_major: float
    range_semi_major: float
    range_minor: float
    azimuth: float
    dip: float
    pitch: float
    rmse: float
    valid_lags: int
    npairs_total: int


def validate_geological_data(dataframe: pd.DataFrame, target_col: str) -> DataQualityReport:
    required = ["X", "Y", "Z", target_col]
    missing = [col for col in required if col not in dataframe.columns]
    if missing:
        raise ValueError(f"Faltan columnas obligatorias: {', '.join(missing)}")

    numeric_failures = [col for col in ["X", "Y", "Z", target_col] if not pd.api.types.is_numeric_dtype(dataframe[col])]
    if numeric_failures:
        raise ValueError(f"Columnas no numéricas: {', '.join(numeric_failures)}")

    working = dataframe[["X", "Y", "Z", target_col]].copy()
    nulls = {col: int(working[col].isna().sum()) for col in working.columns}
    valid = working.dropna()
    duplicates = int(valid.duplicated(subset=["X", "Y", "Z", target_col]).sum())

    warnings: list[str] = []
    if len(valid) < 30:
        warnings.append("Muestras válidas < 30: soporte débil para variografía.")
    if duplicates > 0:
        warnings.append("Se detectaron duplicados XYZ+target; revisar compositado/declustering.")

    total = int(len(working))
    valid_rows = int(len(valid))
    usable_pct = (100.0 * valid_rows / total) if total else 0.0
    if usable_pct < 70:
        warnings.append("Porcentaje utilizable bajo (<70%).")

    return DataQualityReport(
        total_rows=total,
        valid_rows=valid_rows,
        usable_pct=usable_pct,
        nulls_by_column=nulls,
        duplicates_xyz_target=duplicates,
        warnings=warnings,
    )


def build_eda_report(dataframe: pd.DataFrame, target_col: str) -> EDAReport:
    series = pd.to_numeric(dataframe[target_col], errors="coerce").dropna().astype(float)
    if series.empty:
        raise ValueError("No hay datos válidos para EDA.")

    q1 = float(series.quantile(0.25))
    q3 = float(series.quantile(0.75))
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    outliers = int(((series < lower) | (series > upper)).sum())

    stats = {
        "mean": float(series.mean()),
        "median": float(series.median()),
        "std": float(series.std()),
        "variance": float(series.var()),
        "cv": float(series.std() / series.mean()) if float(series.mean()) != 0 else 0.0,
        "min": float(series.min()),
        "max": float(series.max()),
    }
    percentiles = {f"p{p}": float(series.quantile(p / 100.0)) for p in [5, 10, 25, 50, 75, 90, 95]}
    suggested_top_cut = float(series.quantile(0.98))
    return EDAReport(stats=stats, percentiles=percentiles, outlier_iqr_count=outliers, suggested_top_cut=suggested_top_cut)


def fit_directional_variogram_wls(
    dataframe: pd.DataFrame,
    target_col: str,
    *,
    lag_distance: float,
    n_lags: int,
    max_distance: float,
    azimuth: float,
    dip: float,
    ang_tol: float,
    bandwidth: float,
    model_type: str,
) -> FittedVariogram:
    if model_type not in {"spherical", "exponential", "gaussian"}:
        raise ValueError("model_type debe ser spherical/exponential/gaussian")

    result = compute_experimental_variogram(
        dataframe=dataframe,
        x_col="X",
        y_col="Y",
        z_col="Z",
        target_col=target_col,
        lag=lag_distance,
        n_lags=n_lags,
        max_distance=max_distance,
        lag_tolerance=lag_distance * 0.5,
        azimuth=azimuth,
        dip=dip,
        ang_tol_h=ang_tol,
        ang_tol_v=ang_tol,
        band_width=bandwidth,
        band_height=bandwidth,
        max_points=2500,
    )

    structures = [
        {
            "active": True,
            "type": model_type,
            "contribution": max(float(pd.Series(result.gamma_values).dropna().max()), 1e-6),
            "range_major": max(lag_distance, max_distance * 0.5),
            "range_minor": max(lag_distance * 0.8, max_distance * 0.35),
            "range_vertical": max(lag_distance * 0.6, max_distance * 0.2),
            "azimuth": azimuth,
            "dip": dip,
            "lock_contribution": False,
            "lock_range": False,
        }
    ]
    nugget = {"enabled": True, "value": 0.0, "locked": False}

    fitted_nugget, fitted_structures, _ = auto_fit_wls(
        lags=result.lag_centers,
        gamma=result.gamma_values,
        npairs=result.pair_counts,
        nugget=nugget,
        structures=structures,
        min_pairs=10,
        excluded_lags=[],
    )
    modeled, _, sill = evaluate_model(result.lag_centers, float(fitted_nugget["value"]), fitted_structures)
    quality = evaluate_quality(result.lag_centers, result.gamma_values, result.pair_counts, modeled, min_pairs=10, excluded_lags=[])

    structure = fitted_structures[0]
    range_major = float(structure["range_major"])
    range_semi_major = float(structure["range_minor"])
    range_minor = float(structure["range_vertical"])
    if not (float(fitted_nugget["value"]) >= 0 and sill >= 0 and range_major > 0 and range_semi_major > 0 and range_minor > 0):
        raise ValueError("Parámetros no físicos detectados tras el fitting.")

    return FittedVariogram(
        model_type=model_type,
        nugget=float(fitted_nugget["value"]),
        sill=float(sill),
        range_major=range_major,
        range_semi_major=range_semi_major,
        range_minor=range_minor,
        azimuth=float(structure.get("azimuth", azimuth)),
        dip=float(structure.get("dip", dip)),
        pitch=0.0,
        rmse=float(quality.rmse) if math.isfinite(quality.rmse) else math.inf,
        valid_lags=int(quality.valid_lags),
        npairs_total=int(sum(result.pair_counts)),
    )


def export_leapfrog_parameters(model: FittedVariogram) -> str:
    return "\n".join(
        [
            "# Leapfrog variogram parameters (convención: azimuth desde +X hacia +Y, dip desde horizontal)",
            f"model={model.model_type}",
            f"nugget={model.nugget:.6f}",
            f"sill_total={model.sill:.6f}",
            "structures=1",
            f"range_major={model.range_major:.6f}",
            f"range_semi_major={model.range_semi_major:.6f}",
            f"range_minor={model.range_minor:.6f}",
            f"azimuth={model.azimuth:.3f}",
            f"dip={model.dip:.3f}",
            f"pitch={model.pitch:.3f}",
            f"fit_rmse={model.rmse:.6f}",
            f"fit_valid_lags={model.valid_lags}",
            f"npairs_total={model.npairs_total}",
        ]
    )


def run_pipeline(dataframe: pd.DataFrame, target_col: str, *, model_type: str = "spherical") -> dict[str, object]:
    qc = validate_geological_data(dataframe, target_col)
    if qc.valid_rows < 20:
        raise ValueError("Bloqueado: datos insuficientes para variografía confiable (<20 válidos).")
    clean = dataframe[["X", "Y", "Z", target_col]].dropna().copy()
    eda = build_eda_report(clean, target_col)

    fit = fit_directional_variogram_wls(
        clean,
        target_col,
        lag_distance=20.0,
        n_lags=12,
        max_distance=240.0,
        azimuth=35.0,
        dip=0.0,
        ang_tol=25.0,
        bandwidth=50.0,
        model_type=model_type,
    )
    if fit.npairs_total < 100 or fit.valid_lags < 4 or not math.isfinite(fit.rmse):
        raise ValueError("Bloqueado: variograma con soporte insuficiente o ajuste inestable.")

    return {
        "qa_qc": asdict(qc),
        "eda": asdict(eda),
        "fitted_model": asdict(fit),
        "leapfrog_export": export_leapfrog_parameters(fit),
    }
