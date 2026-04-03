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


def _effective_isotropic_range(structure: dict[str, object]) -> float:
    """Return conservative isotropic equivalent range from anisotropic axes.

    Current variogram visualization is 1D by lag distance and does not carry lag-direction
    per point on modeled curves; we therefore use geometric mean as explicit approximation.
    """
    r_major = max(1e-9, float(structure.get("range_major", 1.0) or 1.0))
    r_minor = max(1e-9, float(structure.get("range_minor", r_major) or r_major))
    r_vertical = max(1e-9, float(structure.get("range_vertical", r_major) or r_major))
    return float((r_major * r_minor * r_vertical) ** (1.0 / 3.0))


def evaluate_model(lags: list[float], nugget: float, structures: list[dict[str, object]]) -> tuple[list[float], list[list[float]], float]:
    active_structures = [s for s in structures if bool(s.get("active", True))]
    by_structure: list[list[float]] = []
    for structure in active_structures:
        s_type = str(structure.get("type", "spherical")).strip().lower()
        contribution = max(0.0, float(structure.get("contribution", 0.0) or 0.0))
        model_range = _effective_isotropic_range(structure)
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
) -> tuple[dict[str, object], list[dict[str, object]], dict[str, object]]:
    if not structures:
        return nugget, structures, {"applied": False, "reason": "no_structures"}

    valid_idx = [idx for idx, (g, p) in enumerate(zip(gamma, npairs)) if p >= min_pairs and math.isfinite(float(g)) and (idx + 1) not in excluded_lags]
    if not valid_idx:
        return nugget, structures, {"applied": False, "reason": "no_valid_lags"}

    try:
        from scipy.optimize import least_squares
    except Exception:
        return nugget, structures, {"applied": False, "reason": "scipy_not_available"}

    g_valid = [float(gamma[idx]) for idx in valid_idx]
    p_valid = [max(1.0, float(npairs[idx])) for idx in valid_idx]
    h_valid = [float(lags[idx]) for idx in valid_idx]
    g_scale = max(max(g_valid), 1e-9)
    w_valid = [math.sqrt(v) / g_scale for v in p_valid]

    working_structures = [dict(s) for s in structures]
    active_indices = [idx for idx, s in enumerate(working_structures) if bool(s.get("active", True))]
    if not active_indices:
        return nugget, structures, {"applied": False, "reason": "no_active_structures"}

    param_names: list[tuple[str, int | None]] = []
    x0: list[float] = []
    lo: list[float] = []
    hi: list[float] = []
    nugget_locked = bool(nugget.get("locked", False))
    if not nugget_locked:
        param_names.append(("nugget", None))
        x0.append(max(0.0, float(nugget.get("value", 0.0) or 0.0)))
        lo.append(0.0)
        hi.append(max(10.0 * max(g_valid), 1.0))

    for idx in active_indices:
        structure = working_structures[idx]
        if not bool(structure.get("lock_contribution", False)):
            param_names.append(("contribution", idx))
            x0.append(max(0.0, float(structure.get("contribution", 0.1) or 0.1)))
            lo.append(0.0)
            hi.append(max(10.0 * max(g_valid), 1.0))
        if not bool(structure.get("lock_range", False)):
            param_names.append(("range_iso", idx))
            x0.append(_effective_isotropic_range(structure))
            lo.append(1e-6)
            hi.append(max(max(h_valid) * 3.0, 1.0))

    if not param_names:
        return nugget, structures, {"applied": False, "reason": "all_params_locked"}

    fixed_nugget = max(0.0, float(nugget.get("value", 0.0) or 0.0))

    def decode(params: list[float]) -> tuple[float, list[dict[str, object]]]:
        nugget_value = fixed_nugget
        decoded = [dict(s) for s in working_structures]
        for value, (name, idx) in zip(params, param_names):
            if name == "nugget":
                nugget_value = max(0.0, float(value))
                continue
            if idx is None:
                continue
            if name == "contribution":
                decoded[idx]["contribution"] = max(0.0, float(value))
            elif name == "range_iso":
                # Preserve anisotropy ratios; update only geometric scale.
                current = _effective_isotropic_range(decoded[idx])
                scale = max(1e-9, float(value)) / max(current, 1e-9)
                decoded[idx]["range_major"] = max(1e-9, float(decoded[idx].get("range_major", 1.0) or 1.0) * scale)
                decoded[idx]["range_minor"] = max(1e-9, float(decoded[idx].get("range_minor", decoded[idx]["range_major"]) or decoded[idx]["range_major"]) * scale)
                decoded[idx]["range_vertical"] = max(1e-9, float(decoded[idx].get("range_vertical", decoded[idx]["range_major"]) or decoded[idx]["range_major"]) * scale)
        return nugget_value, decoded

    def residuals(params):
        nugget_value, decoded_structures = decode([float(v) for v in params])
        modeled, _, _ = evaluate_model(h_valid, nugget_value, decoded_structures)
        return [(float(gm) - float(ge)) * float(w) for gm, ge, w in zip(modeled, g_valid, w_valid)]

    x0 = [min(max(value, lo[idx]), hi[idx]) for idx, value in enumerate(x0)]
    result = least_squares(
        residuals,
        x0=x0,
        bounds=(lo, hi),
        method="trf",
        max_nfev=200,
    )
    fit_nugget, fit_structures = decode([float(v) for v in result.x])
    updated_nugget = dict(nugget)
    if not nugget_locked:
        updated_nugget["value"] = fit_nugget
    return updated_nugget, fit_structures, {
        "applied": True,
        "solver": "scipy.optimize.least_squares",
        "method": "trf",
        "nfev": int(getattr(result, "nfev", 0)),
        "cost": float(getattr(result, "cost", math.nan)),
        "success": bool(getattr(result, "success", False)),
        "message": str(getattr(result, "message", "")),
        "weights_mode": "sqrt(npairs)/max_gamma",
        "bounds": {"lower": [float(v) for v in lo], "upper": [float(v) for v in hi]},
        "parameter_order": [f"{name}:{idx if idx is not None else 'global'}" for name, idx in param_names],
        "used_lag_indices": [int(v) + 1 for v in valid_idx],
    }
