"""Encapsulated 3D spatial point-cloud view for the Espacial stage."""

from __future__ import annotations

import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

from app.services.visualization_service import Spatial3DDataBundle
from app.ui.theme import (
    BG_CARD,
    BORDER_SOFT,
    CHART_FONT_SIZE_TICK,
    CHART_TEXT,
    FONT_SMALL,
    FONT_SUBTITLE,
    TEXT_MAIN,
    TEXT_MUTED,
    apply_figure_theme,
    get_continuous_colormap,
)


def _ui_font(token: dict[str, object]) -> ctk.CTkFont:
    return ctk.CTkFont(size=int(token["size"]), weight=str(token["weight"]))


def is_3d_backend_available() -> tuple[bool, str]:
    try:
        from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
    except Exception as exc:
        return False, f"Backend 3D no disponible: {exc}"
    return True, "ok"


class Spatial3DView(ctk.CTkFrame):
    def __init__(self, parent: ctk.CTkFrame) -> None:
        super().__init__(master=parent, fg_color="transparent")
        self._figure: Figure | None = None
        self._canvas: FigureCanvasTkAgg | None = None
        self._toolbar: NavigationToolbar2Tk | None = None
        self._axis = None
        self._colorbar = None
        self._last_elev = 26.0
        self._last_azim = -54.0

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self.header_label = ctk.CTkLabel(self, text="Nube 3D", text_color=TEXT_MAIN, font=_ui_font(FONT_SUBTITLE))
        self.header_label.grid(row=0, column=0, sticky="w", padx=6, pady=(0, 2))

        self.meta_label = ctk.CTkLabel(self, text="", text_color=TEXT_MUTED, font=_ui_font(FONT_SMALL), justify="left")
        self.meta_label.grid(row=1, column=0, sticky="w", padx=6, pady=(0, 4))

        self.canvas_host = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=8)
        self.canvas_host.grid(row=2, column=0, sticky="nsew", padx=4, pady=(0, 4))
        self.canvas_host.grid_columnconfigure(0, weight=1)
        self.canvas_host.grid_rowconfigure(1, weight=1)

        self.toolbar_host = ctk.CTkFrame(self.canvas_host, fg_color="transparent")
        self.toolbar_host.grid(row=0, column=0, sticky="ew", padx=4, pady=(3, 0))
        self.plot_host = ctk.CTkFrame(self.canvas_host, fg_color="transparent")
        self.plot_host.grid(row=1, column=0, sticky="nsew", padx=4, pady=3)

        self.footer = ctk.CTkFrame(self, fg_color="transparent")
        self.footer.grid(row=3, column=0, sticky="ew", padx=4, pady=(0, 1))
        self.footer.grid_columnconfigure(0, weight=1)
        ctk.CTkButton(self.footer, text="Reset view", command=self.reset_view, height=28).grid(row=0, column=0, sticky="e")

    def destroy_plot(self) -> None:
        if self._toolbar is not None:
            self._toolbar.destroy()
            self._toolbar = None
        if self._canvas is not None:
            self._canvas.get_tk_widget().destroy()
            self._canvas = None
        if self._figure is not None:
            import matplotlib.pyplot as plt

            plt.close(self._figure)
            self._figure = None
            self._axis = None
            self._colorbar = None

    def show_unavailable(self, reason: str) -> None:
        self.destroy_plot()
        self.meta_label.configure(text=reason)

    def update_cloud(self, data: Spatial3DDataBundle, color_display_label: str) -> None:
        self._ensure_plot()
        if self._figure is None:
            return
        self._figure.clear()
        apply_figure_theme(self._figure)
        self._axis = self._figure.add_subplot(111, projection="3d")
        self._axis.set_facecolor("#F7FAFE")
        self._axis.grid(True, alpha=0.28, linewidth=0.7, color="#C8D7E9")

        marker_size = 9 if data.point_count_rendered < 7000 else 7
        marker_alpha = 0.78 if data.point_count_rendered < 22000 else 0.64

        cmap = "tab20" if data.color_mode == "categorical" else get_continuous_colormap()
        scatter = self._axis.scatter(
            data.x,
            data.y,
            data.z,
            c=data.color_values,
            cmap=cmap,
            s=marker_size,
            alpha=marker_alpha,
            edgecolors="none",
            depthshade=True,
        )

        self._axis.set_xlabel("X", color=CHART_TEXT)
        self._axis.set_ylabel("Y", color=CHART_TEXT)
        self._axis.set_zlabel("Z", color=CHART_TEXT)
        self._axis.tick_params(labelsize=CHART_FONT_SIZE_TICK, colors=CHART_TEXT)
        for pane in (self._axis.xaxis.pane, self._axis.yaxis.pane, self._axis.zaxis.pane):
            pane.set_facecolor((0.97, 0.98, 1.0, 0.85))
            pane.set_edgecolor((0.83, 0.88, 0.94, 1.0))

        x_span = max(max(data.x) - min(data.x), 1e-6)
        y_span = max(max(data.y) - min(data.y), 1e-6)
        z_span = max(max(data.z) - min(data.z), 1e-6)
        max_span = max(x_span, y_span, z_span)
        self._axis.set_box_aspect((x_span / max_span, y_span / max_span, z_span / max_span))
        self._axis.view_init(elev=self._last_elev, azim=self._last_azim)

        self._colorbar = self._figure.colorbar(scatter, ax=self._axis, shrink=0.82, pad=0.03, fraction=0.045, label=color_display_label)
        if data.color_tick_positions and data.color_tick_labels:
            self._colorbar.set_ticks(data.color_tick_positions)
            self._colorbar.set_ticklabels(data.color_tick_labels)
        self._colorbar.ax.tick_params(labelsize=CHART_FONT_SIZE_TICK, colors=TEXT_MUTED)
        self._colorbar.ax.yaxis.label.set_color(TEXT_MUTED)
        self._colorbar.outline.set_edgecolor(BORDER_SOFT)

        self._figure.subplots_adjust(left=0.03, right=0.90, bottom=0.04, top=0.98)
        if self._canvas is not None:
            self._canvas.draw_idle()

        rendered_info = f"{data.point_count_rendered:,}/{data.point_count_original:,} puntos"
        if data.downsampling_applied:
            rendered_info += " (downsampling activo)"
        meta = f"Color: {color_display_label} ({'categórico' if data.color_mode == 'categorical' else 'numérico'}) · Render: {rendered_info}"
        self.meta_label.configure(text=meta)

    def reset_view(self) -> None:
        if self._axis is None or self._canvas is None:
            return
        self._axis.view_init(elev=26.0, azim=-54.0)
        self._canvas.draw_idle()

    def _ensure_plot(self) -> None:
        if self._figure is None:
            self._figure = Figure(figsize=(12.8, 8.2), dpi=100)
        if self._canvas is None:
            self._canvas = FigureCanvasTkAgg(self._figure, master=self.plot_host)
            self._canvas.get_tk_widget().pack(fill="both", expand=True)
        if self._toolbar is None:
            self._toolbar = NavigationToolbar2Tk(self._canvas, self.toolbar_host, pack_toolbar=False)
            self._toolbar.update()
            self._toolbar.pack(fill="x")
