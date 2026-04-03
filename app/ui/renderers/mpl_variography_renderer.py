"""Matplotlib renderer for experimental variography vertical slice."""

from __future__ import annotations

import logging
import math
import numpy as np

from app.ui.renderers.base import VariographyRenderContext, VariographyRenderer
from app.ui.theme import SEM_BLUE, SEM_ORANGE, SEM_RED, apply_axis_style

logger = logging.getLogger(__name__)


class MatplotlibVariographyRenderer(VariographyRenderer):
    def render(self, grid, response: dict[str, object], context: VariographyRenderContext) -> None:
        grid.figure._dashboard_layout_override = {  # type: ignore[attr-defined]
            "left": 0.07,
            "right": 0.98,
            "top": 0.92,
            "bottom": 0.11,
            "wspace": 0.24,
            "hspace": 0.27,
        }
        def _as_float_or_none(value):
            try:
                if value is None:
                    return None
                converted = float(value)
                if not np.isfinite(converted):
                    return None
                return converted
            except Exception:
                return None

        ax_gamma = grid.axis(0, 0)
        ax_pairs = grid.axis(1, 0)
        ax_diag = grid.axis(0, 1)
        ax_meta = grid.axis(1, 1)
        for axis in (ax_gamma, ax_pairs, ax_diag, ax_meta):
            apply_axis_style(axis)

        lag_values = response.get("lags", response.get("lag_centers", []))
        gamma_raw = response.get("gamma", response.get("gamma_values", []))
        npairs_raw = response.get("npairs", response.get("pair_counts", []))
        max_len = max(len(lag_values or []), len(gamma_raw or []), len(npairs_raw or []))
        if max_len <= 0:
            raise ValueError("Variograma vacío o inválido (sin series).")
        aligned: list[tuple[float | None, float | None, int | None]] = []
        for idx in range(max_len):
            lag_val = _as_float_or_none((lag_values or [])[idx] if idx < len(lag_values or []) else None)
            gamma_val = _as_float_or_none((gamma_raw or [])[idx] if idx < len(gamma_raw or []) else None)
            pair_val_raw = (npairs_raw or [])[idx] if idx < len(npairs_raw or []) else None
            pair_val = None
            if pair_val_raw is not None:
                try:
                    pair_val = int(float(pair_val_raw))
                except Exception:
                    pair_val = None
            aligned.append((lag_val, gamma_val, pair_val))

        finite_points = [(float(lag), float(gamma)) for lag, gamma, _pairs in aligned if lag is not None and gamma is not None and not math.isnan(float(gamma))]
        if finite_points:
            xs = [item[0] for item in finite_points]
            ys = [item[1] for item in finite_points]
            ax_gamma.plot(xs, ys, color=SEM_BLUE, linewidth=1.2, alpha=0.8)
            ax_gamma.scatter(xs, ys, color=SEM_BLUE, s=26, alpha=0.88, label="γ(h) experimental")
        else:
            raise ValueError("Variograma sin pares válidos para curva gamma.")
        ax_gamma.set_title(f"Variograma experimental · {context.target_label}", color=context.chart_text_color)
        ax_gamma.set_xlabel("Lag distance")
        ax_gamma.set_ylabel("Gamma")
        model_meta = response.get("metadata", {}).get("model", {}) if isinstance(response.get("metadata", {}), dict) else {}
        if isinstance(model_meta, dict):
            modeled = model_meta.get("curve_total", [])
            by_structure = model_meta.get("curves_by_structure", [])
            sill = _as_float_or_none(model_meta.get("sill"))
            nugget = _as_float_or_none((model_meta.get("nugget", {}) or {}).get("value") if isinstance(model_meta.get("nugget", {}), dict) else None)
            practical_range = _as_float_or_none(model_meta.get("practical_range"))
            if isinstance(modeled, list) and len(modeled) == len(xs):
                ax_gamma.plot(xs, [float(v) for v in modeled], color=SEM_ORANGE, linewidth=1.6, label="Modelo total")
            if isinstance(by_structure, list):
                for idx, curve in enumerate(by_structure, start=1):
                    if isinstance(curve, list) and len(curve) == len(xs):
                        ax_gamma.plot(xs, [float(v) for v in curve], linestyle="--", linewidth=0.9, alpha=0.75, label=f"Estructura {idx}")
            if sill is not None:
                ax_gamma.axhline(sill, color=SEM_RED, linestyle="-.", linewidth=1.0, alpha=0.8, label="Sill")
            if nugget is not None:
                ax_gamma.scatter([0.0], [nugget], color=SEM_RED, s=42, marker="x", label="Nugget")
            if practical_range is not None:
                ax_gamma.axvline(practical_range, color=SEM_RED, linestyle=":", linewidth=1.0, alpha=0.8, label="Range")

        if finite_points:
            ax_gamma.legend(fontsize=context.chart_legend_size, frameon=False)

        pair_positions = [float(lag) for lag, _gamma, pairs in aligned if lag is not None and pairs is not None]
        pair_counts_int = [int(pairs) for lag, _gamma, pairs in aligned if lag is not None and pairs is not None]
        bars = ax_pairs.bar(pair_positions, pair_counts_int, width=0.8, color=SEM_ORANGE, alpha=0.75)
        ax_pairs.set_title("Npaires por lag", color=context.chart_text_color)
        ax_pairs.set_xlabel("Lag distance")
        ax_pairs.set_ylabel("npairs")
        if pair_counts_int:
            threshold = 30
            ax_pairs.axhline(threshold, color=SEM_RED, linestyle="--", linewidth=1.0, alpha=0.8)
            for bar, count in zip(bars, pair_counts_int):
                if count < threshold:
                    bar.set_color(SEM_RED)

        low_npairs = [idx + 1 for idx, count in enumerate(pair_counts_int) if count < 30]
        diag_text = f"{context.info_text}\n\n"
        diag_text += f"Lags válidos: {len(finite_points)}/{max_len}\n"
        diag_text += f"Máx npairs: {max(pair_counts_int) if pair_counts_int else 0}\n"
        diag_text += f"Lags con npairs <30: {len(low_npairs)}\n"
        if isinstance(model_meta, dict):
            q = model_meta.get("quality", {}) if isinstance(model_meta.get("quality"), dict) else {}
            diag_text += f"RMSE ajuste: {q.get('rmse', '-')}"
        ax_diag.axis("off")
        ax_diag.text(0.03, 0.96, diag_text, va="top", ha="left", fontsize=context.chart_label_size, color=context.chart_text_color)

        metadata = response.get("metadata", {}) if isinstance(response.get("metadata", {}), dict) else {}
        ax_meta.axis("off")
        lines = [
            f"source_points: {response.get('source_points', 0)}",
            f"used_points: {response.get('used_points', 0)}",
            f"downsampled: {response.get('downsampled', False)}",
            f"hash: {metadata.get('computation_hash', '-')}",
            f"direction_applied: {metadata.get('direction_applied', False)}",
            f"direction_mode: {metadata.get('direction_mode', '-')}",
        ]
        if isinstance(model_meta, dict):
            nugget_meta = model_meta.get("nugget", {}) if isinstance(model_meta.get("nugget"), dict) else {}
            usage_warnings = model_meta.get("usage_warnings", []) if isinstance(model_meta.get("usage_warnings"), list) else []
            reliability = model_meta.get("reliability", {}) if isinstance(model_meta.get("reliability"), dict) else {}
            lines.extend(
                [
                    f"sill: {model_meta.get('sill', '-')}",
                    f"nugget_abs: {nugget_meta.get('value', '-')}",
                    f"nugget_rel%: {model_meta.get('nugget_relative_pct', '-')}",
                    f"anisotropy_mode: {model_meta.get('anisotropy_mode', '-')}",
                    f"fit_reliability: {reliability.get('level', '-')}",
                    f"usage_target: {model_meta.get('usage_target', '-')}",
                ]
            )
            if usage_warnings:
                lines.append(f"usage_warnings: {len(usage_warnings)}")
        ax_meta.text(0.03, 0.96, "\n".join(lines), va="top", ha="left", fontsize=context.chart_label_size, color=context.chart_text_color)
        grid.render()
        grid.canvas.draw_idle()
        logger.debug(
            "Variography renderer completed | valid_points=%s pair_bars=%s",
            len(finite_points),
            len(pair_counts_int),
        )
