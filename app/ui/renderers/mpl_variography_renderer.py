"""Matplotlib renderer for experimental variography vertical slice."""

from __future__ import annotations

import math
import numpy as np

from app.ui.renderers.base import VariographyRenderContext, VariographyRenderer
from app.ui.theme import SEM_BLUE, SEM_ORANGE, SEM_RED, apply_axis_style


class MatplotlibVariographyRenderer(VariographyRenderer):
    def render(self, grid, response: dict[str, object], context: VariographyRenderContext) -> None:
        def _safe_float_array(values) -> np.ndarray:
            clean: list[float] = []
            for value in values or []:
                try:
                    if value is None:
                        continue
                    converted = float(value)
                    if not np.isfinite(converted):
                        continue
                    clean.append(converted)
                except Exception:
                    continue
            return np.array(clean, dtype=float)

        print("DEBUG: renderer start")
        ax_gamma = grid.axis(0, 0)
        ax_pairs = grid.axis(1, 0)
        ax_diag = grid.axis(0, 1)
        ax_meta = grid.axis(1, 1)
        for axis in (ax_gamma, ax_pairs, ax_diag, ax_meta):
            apply_axis_style(axis)

        lag_values = response.get("lags", response.get("lag_centers", []))
        gamma_raw = response.get("gamma", response.get("gamma_values", []))
        npairs_raw = response.get("npairs", response.get("pair_counts", []))
        lag_centers = _safe_float_array(lag_values)
        gamma_values = _safe_float_array(gamma_raw)
        pair_counts = _safe_float_array(npairs_raw)

        print("lags:", len(lag_centers))
        print("gamma:", len(gamma_values))
        if len(lag_centers) == 0 or len(gamma_values) == 0:
            raise ValueError("Variograma vacío o inválido (lags/gamma)")

        min_len = min(len(lag_centers), len(gamma_values), len(pair_counts))
        if min_len <= 0:
            raise ValueError("Variograma inválido (sin datos alineados para render)")
        lag_centers = lag_centers[:min_len]
        gamma_values = gamma_values[:min_len]
        pair_counts = pair_counts[:min_len]

        finite_points = [(float(x), float(y)) for x, y in zip(lag_centers, gamma_values) if not math.isnan(float(y))]
        if finite_points:
            xs = [item[0] for item in finite_points]
            ys = [item[1] for item in finite_points]
            ax_gamma.plot(xs, ys, color=SEM_BLUE, linewidth=1.2, alpha=0.8)
            ax_gamma.scatter(xs, ys, color=SEM_BLUE, s=26, alpha=0.88, label="γ(h) experimental")
        ax_gamma.set_title(f"Variograma experimental · {context.target_label}", color=context.chart_text_color)
        ax_gamma.set_xlabel("Lag distance")
        ax_gamma.set_ylabel("Gamma")
        if finite_points:
            ax_gamma.legend(fontsize=context.chart_legend_size, frameon=False)

        pair_counts_int = [int(v) for v in pair_counts]
        bars = ax_pairs.bar(lag_centers.tolist(), pair_counts_int, width=0.8, color=SEM_ORANGE, alpha=0.75)
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
        diag_text += f"Lags válidos: {len(finite_points)}/{len(lag_centers)}\n"
        diag_text += f"Máx npairs: {max(pair_counts_int) if pair_counts_int else 0}\n"
        diag_text += f"Lags con npairs <30: {len(low_npairs)}"
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
        ]
        ax_meta.text(0.03, 0.96, "\n".join(lines), va="top", ha="left", fontsize=context.chart_label_size, color=context.chart_text_color)
        grid.render()
        grid.canvas.draw_idle()
