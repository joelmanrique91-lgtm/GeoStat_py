"""Geoestatistical quality validation helpers for variogram modeling outputs."""

from __future__ import annotations

from dataclasses import dataclass, asdict
import math


@dataclass(frozen=True)
class FitReliability:
    level: str
    flags: list[str]
    notes: list[str]
    metrics: dict[str, float]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _median(values: list[float]) -> float:
    if not values:
        return math.nan
    s = sorted(values)
    mid = len(s) // 2
    if len(s) % 2:
        return float(s[mid])
    return float((s[mid - 1] + s[mid]) * 0.5)


def assess_fit_reliability(
    *,
    lag_centers: list[float],
    gamma_values: list[float],
    pair_counts: list[int],
    model_payload: dict[str, object],
    min_pairs: int,
) -> FitReliability:
    flags: list[str] = []
    notes: list[str] = []
    metrics: dict[str, float] = {}

    valid_pairs = [int(v) for v in pair_counts if int(v) > 0]
    finite_gamma = [float(v) for v in gamma_values if math.isfinite(float(v))]
    low_pair_lags = sum(1 for v in pair_counts if int(v) < max(1, int(min_pairs)))
    low_pair_ratio = (low_pair_lags / max(1, len(pair_counts))) if pair_counts else 1.0
    metrics["low_pair_ratio"] = float(low_pair_ratio)
    metrics["total_pairs"] = float(sum(valid_pairs))

    quality = model_payload.get("quality", {}) if isinstance(model_payload.get("quality"), dict) else {}
    rmse = float(quality.get("rmse", math.nan)) if quality else math.nan
    valid_lags = int(quality.get("valid_lags", 0)) if quality else 0
    metrics["rmse"] = rmse
    metrics["valid_lags"] = float(valid_lags)

    sill = float(model_payload.get("sill", 0.0) or 0.0)
    nugget_rel = float(model_payload.get("nugget_relative_pct", 0.0) or 0.0)
    metrics["sill"] = sill
    metrics["nugget_relative_pct"] = nugget_rel

    active_structures = [
        item
        for item in (model_payload.get("structures", []) if isinstance(model_payload.get("structures"), list) else [])
        if isinstance(item, dict) and bool(item.get("active", True))
    ]
    ranges = [float(item.get("range_major", 0.0) or 0.0) for item in active_structures]
    median_lag = _median([float(v) for v in lag_centers if float(v) > 0])
    max_lag = max([float(v) for v in lag_centers if float(v) > 0], default=0.0)
    if math.isfinite(median_lag):
        metrics["median_lag"] = float(median_lag)
    metrics["max_lag"] = float(max_lag)

    if valid_lags < 3:
        flags.append("LOW_VALID_LAGS")
        notes.append("Ajuste soportado por pocos lags válidos.")
    if low_pair_ratio > 0.5:
        flags.append("HIGH_LOW_PAIR_RATIO")
        notes.append("Más de la mitad de los lags tienen npairs bajos.")
    if nugget_rel > 70.0:
        flags.append("HIGH_NUGGET_RATIO")
        notes.append("Nugget alto respecto al sill: continuidad espacial débil.")
    if sill <= 0 or (not math.isfinite(sill)):
        flags.append("INVALID_SILL")
        notes.append("Sill inválido o no positivo.")
    if math.isfinite(rmse) and math.isfinite(sill) and sill > 0 and (rmse / sill) > 0.35:
        flags.append("HIGH_RELATIVE_RMSE")
        notes.append("Error de ajuste alto respecto al sill.")
    if max_lag > 0 and ranges:
        too_short = sum(1 for r in ranges if r < max(median_lag * 0.5, 1e-9))
        too_long = sum(1 for r in ranges if r > max_lag * 3.0)
        if too_short:
            flags.append("RANGE_TOO_SHORT")
            notes.append("Hay estructuras con rango menor al espaciamiento representativo.")
        if too_long:
            flags.append("RANGE_TOO_LONG")
            notes.append("Hay estructuras con rango excesivo respecto a lags modelados.")

    if len(flags) >= 3:
        level = "low"
    elif flags:
        level = "medium"
    else:
        level = "high"
    return FitReliability(level=level, flags=flags, notes=notes, metrics=metrics)

