"""Matplotlib implementation for EDA chart rendering."""

from __future__ import annotations

import math

from app.ui.renderers.base import EDARenderContext, EDARenderer
from app.ui.theme import (
    CHART_BG,
    CHART_BORDER,
    KPI_PRIMARY_BG,
    SEM_BLUE,
    SEM_BLUE_SOFT,
    SEM_GRAY,
    SEM_GREEN,
    SEM_ORANGE,
    SEM_RED,
    add_reference_line,
    apply_axis_style,
    get_domain_color,
)


class MatplotlibEDARenderer(EDARenderer):
    def render(self, grid, data: dict[str, object], context: EDARenderContext, *, original_values: list[float], cutoff_value: float | None) -> None:
        ax_hist = grid.axis(0, 0)
        ax_hist_bottom = grid.axis(1, 0)
        ax_prob = grid.axis(0, 1)
        ax_secondary = grid.axis(1, 1)

        for axis in (ax_hist, ax_hist_bottom, ax_prob, ax_secondary):
            apply_axis_style(axis)
        ax_hist_bottom.axis("off")

        values = [float(v) for v in data["target_values"]]
        sorted_values = sorted(values)
        n_values = len(sorted_values)
        bins = min(55, max(18, int(math.sqrt(n_values) * 2)))
        p50 = sorted_values[int(0.50 * (n_values - 1))]
        p90 = sorted_values[int(0.90 * (n_values - 1))]
        mean_val = sum(sorted_values) / n_values

        if original_values != values:
            ax_hist.hist(original_values, bins=bins, color=SEM_GRAY, edgecolor="none", alpha=0.20, label="Base")
        ax_hist.hist(values, bins=bins, color=SEM_BLUE, edgecolor="none", alpha=0.76, label="Activa")
        add_reference_line(ax_hist, mean_val, label="Media", color=SEM_BLUE_SOFT, y_pos=0.95)
        add_reference_line(ax_hist, p50, label="P50", color=SEM_GREEN, y_pos=0.88)
        add_reference_line(ax_hist, p90, label="P90", color=SEM_ORANGE, y_pos=0.81)
        if cutoff_value is not None:
            add_reference_line(ax_hist, cutoff_value, label=f"Cutoff {cutoff_value:.3g}", color=SEM_RED, y_pos=0.74)
        ax_hist.set_title(f"Evidencia principal · Histograma ({context.active_variable})", color=context.chart_text_color, pad=8)
        ax_hist.set_xlabel("Ley Cu (%)")
        ax_hist.set_ylabel("Frecuencia (n)")
        ax_hist.legend(loc="upper right", bbox_to_anchor=(0.995, 0.995), fontsize=context.chart_legend_size, frameon=False)
        tail_hint = "cola dominante alta" if mean_val >= p50 else "cola dominante baja"
        ax_hist.text(
            0.015,
            0.96,
            f"Skew={context.skewness_text} · {tail_hint}",
            transform=ax_hist.transAxes,
            ha="left",
            va="top",
            fontsize=context.chart_label_size,
            color=context.chart_text_color,
            bbox={"facecolor": CHART_BG, "edgecolor": CHART_BORDER, "boxstyle": "round,pad=0.22"},
        )

        if data.get("probplot_x") and data.get("probplot_y") and not data.get("probability_failed"):
            prob_x = [float(v) for v in data["probplot_x"]]
            prob_y = [float(v) for v in data["probplot_y"]]
            qmin, qmax = min(prob_x), max(prob_x)
            ymin, ymax = min(prob_y), max(prob_y)
            slope = (ymax - ymin) / (qmax - qmin) if qmax != qmin else 1.0
            intercept = ymin - slope * qmin
            ref_line = [slope * q + intercept for q in prob_x]
            high_cut = sorted(prob_y)[int(0.90 * (len(prob_y) - 1))]
            core_x = [x for x, y in zip(prob_x, prob_y) if y <= high_cut]
            core_y = [y for y in prob_y if y <= high_cut]
            tail_x = [x for x, y in zip(prob_x, prob_y) if y > high_cut]
            tail_y = [y for y in prob_y if y > high_cut]
            ax_prob.scatter(core_x, core_y, s=13, color=SEM_BLUE, alpha=0.74, label="Cuerpo")
            if tail_x:
                ax_prob.scatter(tail_x, tail_y, s=18, color=SEM_ORANGE, alpha=0.86, label="Cola")
            ax_prob.plot(prob_x, ref_line, color=SEM_GRAY, linestyle="--", linewidth=1.0, label="Referencia")
            ax_prob.set_title("QQ plot · Normalidad", color=context.chart_text_color, pad=8)
            ax_prob.set_xlabel("Cuantiles normales")
            ax_prob.set_ylabel("Ley Cu (%)")
            ax_prob.legend(loc="upper left", bbox_to_anchor=(0.01, 0.99), fontsize=context.chart_legend_size, frameon=False)
        else:
            ax_prob.axis("off")
            ax_prob.text(0.5, 0.5, "QQ no disponible", ha="center", va="center", color=context.chart_text_color)

        domain_data = data.get("domain_boxplot", {})
        if domain_data.get("enabled"):
            paired = list(zip(domain_data["labels"], domain_data["values"]))
            paired.sort(key=lambda item: (sum(item[1]) / len(item[1])) if item[1] else float("-inf"), reverse=True)
            ordered_labels = [f"{label} (n={len(vals)})" for label, vals in paired]
            ordered_values = [vals for _label, vals in paired]
            box = ax_secondary.boxplot(ordered_values, labels=ordered_labels, patch_artist=True)
            for patch, (label, _vals) in zip(box["boxes"], paired):
                patch.set_facecolor(get_domain_color(label))
                patch.set_alpha(0.72)
                patch.set_edgecolor(CHART_BORDER)
            ax_secondary.tick_params(axis="x", rotation=10, labelsize=context.chart_legend_size)
            ax_secondary.set_ylabel("Ley Cu (%)")
            ax_secondary.set_title("Comparación por dominio", color=context.chart_text_color, pad=8)
        else:
            box = ax_secondary.boxplot(values, vert=False, patch_artist=True, widths=0.50, showfliers=True)
            for patch in box["boxes"]:
                patch.set_facecolor(KPI_PRIMARY_BG)
                patch.set_alpha(0.58)
                patch.set_edgecolor(SEM_BLUE_SOFT)
            for whisker in box["whiskers"]:
                whisker.set_color(CHART_BORDER)
            for cap in box["caps"]:
                cap.set_color(CHART_BORDER)
            for median in box["medians"]:
                median.set_color(SEM_GREEN)
                median.set_linewidth(1.8)
            ax_secondary.set_yticks([])
            ax_secondary.set_title("Boxplot · Rango y outliers", color=context.chart_text_color, pad=8)
            ax_secondary.set_xlabel("Ley Cu (%)")

        grid.figure.tight_layout(pad=0.75, w_pad=0.85, h_pad=0.85)
        grid.canvas.draw()
        grid.canvas.get_tk_widget().pack(fill="both", expand=True, padx=0, pady=0)
