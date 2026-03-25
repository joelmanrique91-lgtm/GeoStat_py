"""Variogram theoretical modeling helpers (nested structures + fitting)."""

from __future__ import annotations

from dataclasses import dataclass
import math


ALLOWED_STRUCTURE_TYPES = {"spherical", "exponential", "gaussian", "linear"}


@dataclass(frozen=True)
class ModelQuality:
    rmse: float
    sse: float
    valid_lags: int
    invalid_lags: list[int]


def _component_gamma(h: float, model_type: str, contribution: float, model_range: float) -> float:
    if contribution <= 0:
        return 0.0
    if model_type == "spherical":
        if h >= model_range:
            return contribution
        ratio = h / model_range
        return contribution * (1.5 * ratio - 0.5 * (ratio**3))
    if model_type == "exponential":
        return contribution * (1.0 - math.exp(-3.0 * h / model_range))
    if model_type == "gaussian":
        return contribution * (1.0 - math.exp(-3.0 * ((h / model_range) ** 2)))
    if model_type == "linear":
        return contribution * min(1.0, h / model_range)
    return 0.0


def evaluate_model(lags: list[float], nugget: float, structures: list[dict[str, object]]) -> tuple[list[float], list[list[float]], float]:
    active_structures = [s for s in structures if bool(s.get("active", True))]
    by_structure: list[list[float]] = []
    for structure in active_structures:
        s_type = str(structure.get("type", "spherical")).strip().lower()
        contribution = max(0.0, float(structure.get("contribution", 0.0) or 0.0))
        model_range = max(1e-9, float(structure.get("range_major", 1.0) or 1.0))
        by_structure.append([_component_gamma(float(h), s_type, contribution, model_range) for h in lags])
    total = [max(0.0, nugget) + sum(series[idx] for series in by_structure) for idx in range(len(lags))]
    sill = max(0.0, nugget) + sum(max(0.0, float(s.get("contribution", 0.0) or 0.0)) for s in active_structures)
    return total, by_structure, sill


def evaluate_quality(
    lags: list[float],
    gamma: list[float],
    npairs: list[int],
    modeled: list[float],
    min_pairs: int,
    excluded_lags: list[int],
) -> ModelQuality:
    del lags
    sq_errors: list[float] = []
    invalid: list[int] = []
    excluded = set(int(v) for v in excluded_lags)
    for idx, (g_exp, pairs, g_model) in enumerate(zip(gamma, npairs, modeled), start=1):
        if idx in excluded:
            continue
        if pairs < min_pairs or (not math.isfinite(float(g_exp))):
            invalid.append(idx)
            continue
        sq_errors.append((float(g_exp) - float(g_model)) ** 2)
    if not sq_errors:
        return ModelQuality(rmse=math.nan, sse=math.nan, valid_lags=0, invalid_lags=invalid)
    sse = float(sum(sq_errors))
    return ModelQuality(rmse=math.sqrt(sse / len(sq_errors)), sse=sse, valid_lags=len(sq_errors), invalid_lags=invalid)


def auto_fit_wls(
    lags: list[float],
    gamma: list[float],
    npairs: list[int],
    nugget: dict[str, object],
    structures: list[dict[str, object]],
    min_pairs: int,
    excluded_lags: list[int],
) -> tuple[dict[str, object], list[dict[str, object]]]:
    if not structures:
        return nugget, structures

    valid_idx = [idx for idx, (g, p) in enumerate(zip(gamma, npairs)) if p >= min_pairs and math.isfinite(float(g)) and (idx + 1) not in excluded_lags]
    if not valid_idx:
        return nugget, structures

    g_valid = [float(gamma[idx]) for idx in valid_idx]
    p_valid = [max(1, int(npairs[idx])) for idx in valid_idx]
    total_w = float(sum(p_valid))
    weighted_mean = sum(g * w for g, w in zip(g_valid, p_valid)) / total_w
    is_nugget_locked = bool(nugget.get("locked", False))
    nugget_value = max(0.0, float(nugget.get("value", 0.0) or 0.0))
    if not is_nugget_locked:
        nugget_value = max(0.0, min(weighted_mean * 0.35, min(g_valid)))

    active_indices = [idx for idx, s in enumerate(structures) if bool(s.get("active", True))]
    if not active_indices:
        return {**nugget, "value": nugget_value}, structures
    remaining_sill = max(0.0, weighted_mean - nugget_value)
    per_structure = remaining_sill / max(1, len(active_indices))

    max_lag = max(float(lags[idx]) for idx in valid_idx)
    new_structures: list[dict[str, object]] = []
    for idx, structure in enumerate(structures):
        updated = dict(structure)
        if idx in active_indices:
            if not bool(updated.get("lock_contribution", False)):
                updated["contribution"] = per_structure
            if not bool(updated.get("lock_range", False)):
                t = str(updated.get("type", "spherical"))
                if t == "spherical":
                    updated["range_major"] = max_lag * 0.95
                elif t == "exponential":
                    updated["range_major"] = max_lag * 0.50
                elif t == "gaussian":
                    updated["range_major"] = max_lag * 0.70
                else:
                    updated["range_major"] = max_lag
        new_structures.append(updated)

    return {**nugget, "value": nugget_value}, new_structures
