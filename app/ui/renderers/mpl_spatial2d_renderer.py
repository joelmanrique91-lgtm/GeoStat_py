"""Matplotlib implementation for 2D spatial chart rendering."""

from __future__ import annotations

from matplotlib.ticker import ScalarFormatter

from app.services.geostat_service import GeostatService
from app.services.visualization_service import SpatialDataBundle
from app.ui.renderers.base import Spatial2DRenderContext, Spatial2DRenderer
from app.ui.theme import CHART_FONT_SIZE_TICK, TEXT_MUTED, apply_axis_style, get_continuous_colormap


class MatplotlibSpatial2DRenderer(Spatial2DRenderer):
    def __init__(self, service: GeostatService) -> None:
        self.service = service

    def render(self, grid, spatial: SpatialDataBundle, context: Spatial2DRenderContext) -> None:
        ax_xy = grid.axis(0, 0)
        ax_xz = grid.axis(0, 1)
        ax_yz = grid.axis(1, 0)
        ax_info = grid.axis(1, 1)

        for axis in (ax_xy, ax_xz, ax_yz, ax_info):
            apply_axis_style(axis)
        cmap = "tab20" if spatial.target_tick_labels else get_continuous_colormap()
        point_kwargs = {"s": 12, "alpha": 0.66, "edgecolors": "white", "linewidths": 0.15}
        sc_xy = ax_xy.scatter(spatial.x, spatial.y, c=spatial.target, cmap=cmap, **point_kwargs)
        ax_xz.scatter(spatial.x, spatial.z, c=spatial.target, cmap=cmap, **point_kwargs)
        ax_yz.scatter(spatial.y, spatial.z, c=spatial.target, cmap=cmap, **point_kwargs)

        ax_xy.set_title("Planta XY (principal)", color=context.info_text_color)
        ax_xz.set_title("Sección XZ", color=context.info_text_color)
        ax_yz.set_title("Sección YZ", color=context.info_text_color)
        ax_xy.set_xlabel("X")
        ax_xy.set_ylabel("Y")
        ax_xz.set_xlabel("X")
        ax_xz.set_ylabel("Z")
        ax_yz.set_xlabel("Y")
        ax_yz.set_ylabel("Z")
        ax_xy.margins(x=0.02, y=0.02)
        ax_xz.margins(x=0.02, y=0.03)
        ax_yz.margins(x=0.02, y=0.03)
        plain_formatter = ScalarFormatter(useOffset=False)
        plain_formatter.set_scientific(False)
        for axis in [ax_xy.xaxis, ax_xy.yaxis, ax_xz.xaxis, ax_xz.yaxis, ax_yz.xaxis, ax_yz.yaxis]:
            axis.set_major_formatter(plain_formatter)

        colorbar = grid.figure.colorbar(sc_xy, ax=ax_xy, shrink=0.72, pad=0.015, fraction=0.045, label=spatial.target_label)
        if spatial.target_tick_positions and spatial.target_tick_labels:
            colorbar.set_ticks(spatial.target_tick_positions)
            colorbar.set_ticklabels(spatial.target_tick_labels)
        colorbar.ax.tick_params(labelsize=CHART_FONT_SIZE_TICK, colors=TEXT_MUTED)
        colorbar.ax.yaxis.label.set_color(TEXT_MUTED)
        colorbar.outline.set_edgecolor(context.info_border_color)

        ax_info.axis("off")
        msg = "Ficha espacial\n• Vistas: XY / XZ / YZ"
        msg += f"\n• Target resuelto global: {context.snapshot['resolved_target_column'] or 'No definido'}"
        msg += f"\n• Color mostrado (local): {context.color_by or context.snapshot['resolved_target_column'] or 'No definido'}"
        msg += f"\n• {context.guardrail_note}"
        state = self.service.get_cutoff_state()
        if state["dynamic_enabled"]:
            msg += f"\n• Capping confirmado: {state['dynamic_cutoff_value']:.6g}"
        if spatial.downsampled:
            msg += f"\n• Muestreo mostrado: {spatial.plotted_points:,}/{spatial.source_points:,}"
        msg += "\n• Preparado para lectura por ley o por dominio."
        ax_info.text(
            0.05,
            0.95,
            msg,
            va="top",
            color=context.info_text_color,
            fontsize=context.label_size,
            linespacing=1.35,
            bbox={"facecolor": context.info_bg_color, "edgecolor": context.info_border_color, "boxstyle": "round,pad=0.55"},
        )
        grid.render()
