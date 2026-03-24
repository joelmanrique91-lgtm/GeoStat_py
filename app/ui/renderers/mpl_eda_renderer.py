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
    """Renderer split into sibling chart panels (one figure per panel)."""

    def render_dashboard(
        self,
        *,
        histogram_grid,
        qq_grid,
        boxplot_grid,
        iqr_grid,
        data: dict[str, object],
        context: EDARenderContext,
        original_values: list[float],
        cutoff_value: float | None,
    ) -> None:
        values = [float(v) for v in data["target_values"]]
        sorted_values = sorted(values)
        n_values = len(sorted_values)
        bins = min(55, max(18, int(math.sqrt(n_values) * 2)))
        p50 = sorted_values[int(0.50 * (n_values - 1))]
        p90 = sorted_values[int(0.90 * (n_values - 1))]
        mean_val = sum(sorted_values) / n_values

        self._render_histogram(
            histogram_grid,
            values=values,
            original_values=original_values,
            bins=bins,
            p50=p50,
            p90=p90,
            mean_val=mean_val,
            cutoff_value=cutoff_value,
            context=context,
        )
        self._render_qq(qq_grid, data=data, context=context)
        self._render_boxplot(boxplot_grid, data=data, values=values, context=context)
        self._render_iqr(iqr_grid, sorted_values=sorted_values, p50=p50, p90=p90, mean_val=mean_val, context=context)

    def _render_histogram(
        self,
        grid,
        *,
        values: list[float],
        original_values: list[float],
        bins: int,
        p50: float,
        p90: float,
        mean_val: float,
        cutoff_value: float | None,
        context: EDARenderContext,
    ) -> None:
        ax = grid.axis(0, 0)
        grid.figure._dashboard_layout_override = {  # type: ignore[attr-defined]
            "left": 0.06,
            "right": 0.988,
            "top": 0.965,
            "bottom": 0.12,
            "wspace": 0.12,
            "hspace": 0.12,
        }
        apply_axis_style(ax)
        if original_values != values:
            ax.hist(original_values, bins=bins, color=SEM_GRAY, edgecolor="white", linewidth=0.25, alpha=0.20, label="Base")
        ax.hist(values, bins=bins, color=SEM_BLUE, edgecolor="white", linewidth=0.30, alpha=0.84, label="Activa")
        add_reference_line(ax, mean_val, label="Media", color=SEM_BLUE_SOFT, y_pos=0.95)
        add_reference_line(ax, p50, label="P50", color=SEM_GREEN, y_pos=0.88)
        add_reference_line(ax, p90, label="P90", color=SEM_ORANGE, y_pos=0.81)
        if cutoff_value is not None:
            add_reference_line(ax, cutoff_value, label=f"Cutoff {cutoff_value:.3g}", color=SEM_RED, y_pos=0.74)
        ax.set_title(f"Evidencia principal · Histograma ({context.active_variable})", color=context.chart_text_color, pad=8)
        ax.set_xlabel("Ley Cu (%)")
        ax.set_ylabel("Frecuencia (n)")
        ax.tick_params(axis="both", labelsize=context.chart_label_size + 1)
        ax.legend(loc="upper right", fontsize=context.chart_legend_size, frameon=False, borderaxespad=0.35, handlelength=1.4)
        ax.margins(x=0.02)
        tail_hint = "cola dominante alta" if mean_val >= p50 else "cola dominante baja"
        ax.text(
            0.015,
            0.965,
            f"Skew={context.skewness_text} · {tail_hint}",
            transform=ax.transAxes,
            ha="left",
            va="top",
            fontsize=context.chart_label_size,
            color=context.chart_text_color,
            bbox={"facecolor": CHART_BG, "edgecolor": CHART_BORDER, "boxstyle": "round,pad=0.22"},
        )
        grid.render()

    def _render_qq(self, grid, *, data: dict[str, object], context: EDARenderContext) -> None:
        ax = grid.axis(0, 0)
        grid.figure._dashboard_layout_override = {  # type: ignore[attr-defined]
            "left": 0.12,
            "right": 0.982,
            "top": 0.955,
            "bottom": 0.14,
            "wspace": 0.12,
            "hspace": 0.12,
        }
        apply_axis_style(ax)
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
            ax.scatter(core_x, core_y, s=14, color=SEM_BLUE, alpha=0.76, label="Cuerpo")
            if tail_x:
                ax.scatter(tail_x, tail_y, s=20, color=SEM_ORANGE, alpha=0.88, label="Cola")
            ax.plot(prob_x, ref_line, color=SEM_GRAY, linestyle="--", linewidth=1.1, label="Referencia")
            ax.set_title("QQ plot · Normalidad", color=context.chart_text_color, pad=8)
            ax.set_xlabel("Cuantiles normales")
            ax.set_ylabel("Ley Cu (%)")
            ax.tick_params(axis="both", labelsize=context.chart_label_size)
            ax.legend(loc="upper left", fontsize=context.chart_legend_size, frameon=False, borderaxespad=0.35, handlelength=1.4)
            ax.margins(x=0.03, y=0.05)
        else:
            ax.axis("off")
            ax.text(0.5, 0.5, "QQ no disponible", ha="center", va="center", color=context.chart_text_color)
        grid.render()

    def _render_boxplot(self, grid, *, data: dict[str, object], values: list[float], context: EDARenderContext) -> None:
        ax = grid.axis(0, 0)
        domain_data = data.get("domain_boxplot", {})
        domain_enabled = bool(domain_data.get("enabled"))
        label_count = len(domain_data.get("labels", [])) if domain_enabled else 0
        label_lengths = [len(str(label)) for label in domain_data.get("labels", [])] if domain_enabled else []
        max_label_len = max(label_lengths) if label_lengths else 0
        bottom_margin = 0.14
        if domain_enabled:
            bottom_margin = 0.19
            if label_count >= 4:
                bottom_margin += 0.03
            if max_label_len >= 16:
                bottom_margin += 0.03
            if max_label_len >= 24:
                bottom_margin += 0.03
            bottom_margin = min(bottom_margin, 0.33)
        grid.figure._dashboard_layout_override = {  # type: ignore[attr-defined]
            "left": 0.12,
            "right": 0.982,
            "top": 0.955,
            "bottom": bottom_margin,
            "wspace": 0.12,
            "hspace": 0.12,
        }
        apply_axis_style(ax)
        if domain_enabled:
            paired = list(zip(domain_data["labels"], domain_data["values"]))
            paired.sort(key=lambda item: (sum(item[1]) / len(item[1])) if item[1] else float("-inf"), reverse=True)
            ordered_labels = [f"{label} (n={len(vals)})" for label, vals in paired]
            ordered_values = [vals for _label, vals in paired]
            box = ax.boxplot(ordered_values, labels=ordered_labels, patch_artist=True)
            for patch, (label, _vals) in zip(box["boxes"], paired):
                patch.set_facecolor(get_domain_color(label))
                patch.set_alpha(0.72)
                patch.set_edgecolor(CHART_BORDER)
            rotation = 25 if max_label_len < 18 else 33
            ax.tick_params(axis="x", labelrotation=rotation, labelsize=max(context.chart_legend_size - 1, 8))
            for tick in ax.get_xticklabels():
                tick.set_horizontalalignment("right")
                tick.set_verticalalignment("top")
            ax.set_ylabel("Ley Cu (%)")
            ax.set_title("Comparación por dominio", color=context.chart_text_color, pad=8)
            ax.margins(x=0.10)
        else:
            box = ax.boxplot(values, vert=False, patch_artist=True, widths=0.50, showfliers=True)
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
            ax.set_yticks([])
            ax.set_title("Boxplot · Rango y outliers", color=context.chart_text_color, pad=8)
            ax.set_xlabel("Ley Cu (%)")
            ax.margins(x=0.03)
            ax.tick_params(axis="x", labelsize=context.chart_label_size)
        grid.render()

    def _render_iqr(self, grid, *, sorted_values: list[float], p50: float, p90: float, mean_val: float, context: EDARenderContext) -> None:
        ax = grid.axis(0, 0)
        grid.figure._dashboard_layout_override = {  # type: ignore[attr-defined]
            "left": 0.06,
            "right": 0.99,
            "top": 0.84,
            "bottom": 0.33,
            "wspace": 0.10,
            "hspace": 0.10,
        }
        apply_axis_style(ax)
        n_values = len(sorted_values)
        q10 = sorted_values[int(0.10 * (n_values - 1))]
        q25 = sorted_values[int(0.25 * (n_values - 1))]
        q75 = sorted_values[int(0.75 * (n_values - 1))]
        ax.set_title("Rango intercuartil y percentiles", color=context.chart_text_color, pad=6)
        ax.hlines(1.0, q10, p90, color=CHART_BORDER, linewidth=4.2, alpha=0.75)
        ax.hlines(1.0, q25, q75, color=SEM_BLUE, linewidth=6.8, alpha=0.78)
        ax.scatter([mean_val, p50, p90], [1.0, 1.0, 1.0], color=[SEM_BLUE_SOFT, SEM_GREEN, SEM_ORANGE], s=[26, 24, 26], zorder=3)
        ax.set_yticks([])
        ax.set_xlabel("Ley Cu (%)")
        ax.set_xlim(min(sorted_values), max(sorted_values))
        ax.margins(x=0.02, y=0.28)
        ax.grid(axis="y", alpha=0.0)
        ax.text(
            0.012,
            0.91,
            "P10–P90 / IQR",
            transform=ax.transAxes,
            ha="left",
            va="top",
            fontsize=max(context.chart_label_size - 1, 8),
            color=context.chart_text_color,
        )
        ax.tick_params(axis="both", labelsize=context.chart_label_size)
        grid.render()

    def render(self, grid, data: dict[str, object], context: EDARenderContext, *, original_values: list[float], cutoff_value: float | None) -> None:
        """Backward-compatible fallback: keeps single-grid contract if still used."""
        self._render_histogram(
            grid,
            values=[float(v) for v in data["target_values"]],
            original_values=original_values,
            bins=min(55, max(18, int(math.sqrt(len(data["target_values"])) * 2))),
            p50=sorted([float(v) for v in data["target_values"]])[int(0.50 * (len(data["target_values"]) - 1))],
            p90=sorted([float(v) for v in data["target_values"]])[int(0.90 * (len(data["target_values"]) - 1))],
            mean_val=sum(float(v) for v in data["target_values"]) / len(data["target_values"]),
            cutoff_value=cutoff_value,
            context=context,
        )
