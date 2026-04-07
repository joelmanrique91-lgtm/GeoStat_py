"""Encapsulated 3D spatial point-cloud view for the Espacial stage."""

from __future__ import annotations

import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

from app.models.spatial import PointCloudGeometry, SceneState
from app.services.visualization_service import Spatial3DDataBundle
from app.ui.theme import (
    BG_CARD,
    CHART_FONT_SIZE_TICK,
    CHART_TEXT,
    CHART_BG,
    CHART_GRID,
    CHART_BORDER,
    FONT_SMALL,
    FONT_SUBTITLE,
    TEXT_MAIN,
    TEXT_MUTED,
    apply_figure_theme,
    apply_dashboard_layout,
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
        self._scroll_cid: int | None = None
        self._draw_cid: int | None = None
        self._resize_after_id: str | None = None
        self._last_elev = 26.0
        self._last_azim = -54.0

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self.header_label = ctk.CTkLabel(self, text="Nube 3D", text_color=TEXT_MAIN, font=_ui_font(FONT_SUBTITLE))
        self.header_label.grid(row=0, column=0, sticky="w", padx=4, pady=(0, 1))

        self.meta_label = ctk.CTkLabel(self, text="", text_color=TEXT_MUTED, font=_ui_font(FONT_SMALL), justify="left")
        self.meta_label.grid(row=1, column=0, sticky="w", padx=4, pady=(0, 3))

        self.canvas_host = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=8)
        self.canvas_host.grid(row=2, column=0, sticky="nsew", padx=2, pady=(0, 3))
        self.canvas_host.grid_columnconfigure(0, weight=1)
        self.canvas_host.grid_rowconfigure(1, weight=1)

        self.toolbar_host = ctk.CTkFrame(self.canvas_host, fg_color="transparent")
        self.toolbar_host.grid(row=0, column=0, sticky="ew", padx=3, pady=(2, 0))
        self.plot_host = ctk.CTkFrame(self.canvas_host, fg_color="transparent")
        self.plot_host.grid(row=1, column=0, sticky="nsew", padx=3, pady=2)
        self.plot_host.bind("<Configure>", self._on_plot_host_configure, add="+")

        self.footer = ctk.CTkFrame(self, fg_color="transparent")
        self.footer.grid(row=3, column=0, sticky="ew", padx=2, pady=(0, 0))
        self.footer.grid_columnconfigure(0, weight=1)
        ctk.CTkButton(self.footer, text="Reset view", command=self.reset_view, height=28).grid(row=0, column=0, sticky="e")

    def destroy_plot(self) -> None:
        if self._resize_after_id is not None:
            try:
                self.after_cancel(self._resize_after_id)
            except Exception:
                pass
            self._resize_after_id = None
        if self._canvas is not None:
            if self._scroll_cid is not None:
                self._canvas.mpl_disconnect(self._scroll_cid)
                self._scroll_cid = None
            if self._draw_cid is not None:
                self._canvas.mpl_disconnect(self._draw_cid)
                self._draw_cid = None
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

    def destroy(self) -> None:
        self.destroy_plot()
        super().destroy()

    def show_unavailable(self, reason: str) -> None:
        self.destroy_plot()
        self.meta_label.configure(text=reason)


    def update_scene(self, scene: SceneState, color_display_label: str) -> None:
        point_layer = next((layer for layer in scene.layers if layer.layer_type == "point_cloud" and layer.visible), None)
        if point_layer is None or not isinstance(point_layer.payload, PointCloudGeometry):
            self.show_unavailable("Escena sin capa de puntos visible para render 3D.")
            return
        payload = point_layer.payload
        bundle = Spatial3DDataBundle(
            x=[p[0] for p in payload.points_xyz],
            y=[p[1] for p in payload.points_xyz],
            z=[p[2] for p in payload.points_xyz],
            color_values=list(payload.color_values),
            point_count_original=int(payload.source_point_count or len(payload.points_xyz)),
            point_count_rendered=int(payload.rendered_point_count or len(payload.points_xyz)),
            downsampling_applied=bool((payload.source_point_count or len(payload.points_xyz)) > (payload.rendered_point_count or len(payload.points_xyz))),
            color_mode=payload.color_mode,
            color_label=payload.color_label,
            color_tick_positions=list(payload.color_tick_positions) if payload.color_tick_positions else None,
            color_tick_labels=list(payload.color_tick_labels) if payload.color_tick_labels else None,
        )
        self.update_cloud(bundle, color_display_label)

    def update_cloud(self, data: Spatial3DDataBundle, color_display_label: str) -> None:
        self._ensure_plot()
        if self._figure is None:
            return
        if self._axis is not None:
            self._last_elev = float(getattr(self._axis, "elev", self._last_elev))
            self._last_azim = float(getattr(self._axis, "azim", self._last_azim))
        self._figure.clear()
        apply_figure_theme(self._figure)
        self._axis = self._figure.add_subplot(111, projection="3d")
        self._axis.set_facecolor(CHART_BG)
        self._axis.grid(True, alpha=0.28, linewidth=0.7, color=CHART_GRID)

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
            pane.set_facecolor((0.08, 0.13, 0.20, 0.88))
            pane.set_edgecolor((0.22, 0.33, 0.47, 1.0))

        x_min, x_max = min(data.x), max(data.x)
        y_min, y_max = min(data.y), max(data.y)
        z_min, z_max = min(data.z), max(data.z)
        x_mid = (x_min + x_max) * 0.5
        y_mid = (y_min + y_max) * 0.5
        z_mid = (z_min + z_max) * 0.5
        x_span = max(x_max - x_min, 1e-6)
        y_span = max(y_max - y_min, 1e-6)
        z_span = max(z_max - z_min, 1e-6)
        half = max(x_span, y_span, z_span) * 0.55
        self._axis.set_xlim(x_mid - half, x_mid + half)
        self._axis.set_ylim(y_mid - half, y_mid + half)
        self._axis.set_zlim(z_mid - half, z_mid + half)
        self._axis.set_box_aspect((1.0, 1.0, 1.0))
        self._axis.view_init(elev=self._last_elev, azim=self._last_azim)

        self._colorbar = self._figure.colorbar(scatter, ax=self._axis, shrink=0.82, pad=0.03, fraction=0.045, label=color_display_label)
        if data.color_tick_positions and data.color_tick_labels:
            self._colorbar.set_ticks(data.color_tick_positions)
            self._colorbar.set_ticklabels(data.color_tick_labels)
        self._colorbar.ax.tick_params(labelsize=CHART_FONT_SIZE_TICK, colors=TEXT_MUTED)
        self._colorbar.ax.yaxis.label.set_color(TEXT_MUTED)
        self._colorbar.outline.set_edgecolor(CHART_BORDER)

        apply_dashboard_layout(self._figure, left=0.03, right=0.88, bottom=0.07, top=0.95, wspace=0.10, hspace=0.10)
        self._sync_figure_to_host(force=True)
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
            self._figure = Figure(figsize=(12.0, 7.6), dpi=100)
        if self._canvas is None:
            self._canvas = FigureCanvasTkAgg(self._figure, master=self.plot_host)
            self._canvas.get_tk_widget().pack(fill="both", expand=True)
            self._scroll_cid = self._canvas.mpl_connect("scroll_event", self._on_mouse_wheel_zoom)
            self._draw_cid = self._canvas.mpl_connect("draw_event", self._on_draw)
        if self._toolbar is None:
            self._toolbar = NavigationToolbar2Tk(self._canvas, self.toolbar_host, pack_toolbar=False)
            self._toolbar.update()
            self._toolbar.pack(fill="x")
        self._sync_figure_to_host(force=True)

    def _on_mouse_wheel_zoom(self, event) -> None:
        if self._axis is None or self._canvas is None or event.inaxes != self._axis:
            return
        scale = 0.88 if event.button == "up" else 1.12
        x_min, x_max = self._axis.get_xlim3d()
        y_min, y_max = self._axis.get_ylim3d()
        z_min, z_max = self._axis.get_zlim3d()
        x_mid = (x_min + x_max) * 0.5
        y_mid = (y_min + y_max) * 0.5
        z_mid = (z_min + z_max) * 0.5
        x_half = max((x_max - x_min) * 0.5 * scale, 1e-6)
        y_half = max((y_max - y_min) * 0.5 * scale, 1e-6)
        z_half = max((z_max - z_min) * 0.5 * scale, 1e-6)
        self._axis.set_xlim3d(x_mid - x_half, x_mid + x_half)
        self._axis.set_ylim3d(y_mid - y_half, y_mid + y_half)
        self._axis.set_zlim3d(z_mid - z_half, z_mid + z_half)
        self._canvas.draw_idle()

    def _on_draw(self, _event) -> None:
        if self._axis is None:
            return
        self._last_elev = float(getattr(self._axis, "elev", self._last_elev))
        self._last_azim = float(getattr(self._axis, "azim", self._last_azim))

    def _on_plot_host_configure(self, _event) -> None:
        if self._resize_after_id is not None:
            try:
                self.after_cancel(self._resize_after_id)
            except Exception:
                pass
        self._resize_after_id = self.after(80, self._sync_figure_to_host)

    def _sync_figure_to_host(self, *, force: bool = False) -> None:
        self._resize_after_id = None
        if self._figure is None or self._canvas is None:
            return
        width = int(self.plot_host.winfo_width())
        height = int(self.plot_host.winfo_height())
        if width <= 24 or height <= 24:
            return
        dpi = float(self._figure.get_dpi())
        self._figure.set_size_inches(max(width / dpi, 2.4), max(height / dpi, 2.0), forward=force)
