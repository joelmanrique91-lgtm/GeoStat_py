"""Reusable matplotlib dashboard grids for CustomTkinter tabs."""

from __future__ import annotations

import customtkinter as ctk
import logging
import time
from matplotlib import pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from app.ui.theme import CHART_BG, apply_axis_style, apply_dashboard_layout, apply_figure_theme

logger = logging.getLogger(__name__)


def compute_responsive_figure_size(
    *,
    container_width: int,
    container_height: int,
    dpi: float,
    min_width_inches: float = 2.0,
    min_height_inches: float = 1.6,
    max_aspect_ratio: float | None = None,
    base_aspect_ratio: float | None = None,
) -> tuple[float, float]:
    """Compute a host-bounded responsive figure size in inches."""
    avail_w = max(float(container_width) / max(dpi, 1e-6), min_width_inches)
    avail_h = max(float(container_height) / max(dpi, 1e-6), min_height_inches)
    new_w = avail_w
    new_h = avail_h
    if max_aspect_ratio is not None:
        ratio = new_w / max(new_h, 1e-6)
        if ratio > max_aspect_ratio:
            new_w = max(new_h * max_aspect_ratio, min_width_inches)
    if base_aspect_ratio is not None:
        ratio = new_w / max(new_h, 1e-6)
        min_ratio = max(base_aspect_ratio * 0.55, 0.60)
        if ratio < min_ratio:
            candidate_w = max(new_h * min_ratio, min_width_inches)
            if candidate_w <= avail_w:
                new_w = candidate_w
            else:
                new_h = max(new_w / min_ratio, min_height_inches)
    new_w = min(new_w, avail_w)
    new_h = min(new_h, avail_h)
    return new_w, new_h


def compute_responsive_figure_size(
    *,
    container_width: int,
    container_height: int,
    dpi: float,
    min_width_inches: float = 2.0,
    min_height_inches: float = 1.6,
    max_aspect_ratio: float | None = None,
    base_aspect_ratio: float | None = None,
) -> tuple[float, float]:
    """Compute a host-bounded responsive figure size in inches."""
    avail_w = max(float(container_width) / max(dpi, 1e-6), min_width_inches)
    avail_h = max(float(container_height) / max(dpi, 1e-6), min_height_inches)
    new_w = avail_w
    new_h = avail_h
    if max_aspect_ratio is not None:
        ratio = new_w / max(new_h, 1e-6)
        if ratio > max_aspect_ratio:
            new_w = max(new_h * max_aspect_ratio, min_width_inches)
    if base_aspect_ratio is not None:
        ratio = new_w / max(new_h, 1e-6)
        min_ratio = max(base_aspect_ratio * 0.55, 0.60)
        if ratio < min_ratio:
            candidate_w = max(new_h * min_ratio, min_width_inches)
            if candidate_w <= avail_w:
                new_w = candidate_w
            else:
                new_h = max(new_w / min_ratio, min_height_inches)
    new_w = min(new_w, avail_w)
    new_h = min(new_h, avail_h)
    return new_w, new_h


class DashboardGrid:
    """Simple reusable figure grid wrapper (1x1, 1x2, 2x2, 3x1)."""
    _instances_by_parent: dict[int, list["DashboardGrid"]] = {}

    def __init__(
        self,
        parent: ctk.CTkFrame,
        rows: int,
        cols: int,
        figsize: tuple[float, float] | None = None,
        *,
        width_ratios: list[float] | None = None,
        height_ratios: list[float] | None = None,
        max_aspect_ratio: float | None = None,
    ) -> None:
        self.parent = parent
        self._last_parent_size: tuple[int, int] | None = None
        self._resize_after_id: str | None = None
        self._configure_bound = False
        self._destroyed = False
        self._last_resize_draw_at = 0.0
        self._last_size_inches: tuple[float, float] | None = None
        self._configured_figsize = figsize
        self._max_aspect_ratio = max_aspect_ratio if (max_aspect_ratio is None or max_aspect_ratio > 0) else None
        self._base_aspect_ratio = (figsize[0] / max(figsize[1], 1e-6)) if figsize is not None else None
        figure_kwargs: dict[str, object] = {"dpi": 100}
        if figsize is not None:
            figure_kwargs["figsize"] = figsize
        self.figure = Figure(**figure_kwargs)
        apply_figure_theme(self.figure)
        if width_ratios or height_ratios:
            grid_spec = self.figure.add_gridspec(rows, cols, width_ratios=width_ratios, height_ratios=height_ratios)
            self.axes = [[self.figure.add_subplot(grid_spec[r, c]) for c in range(cols)] for r in range(rows)]
        else:
            self.axes = self.figure.subplots(rows, cols, squeeze=False).tolist()
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.parent)
        self.canvas.get_tk_widget().configure(bg=CHART_BG, highlightthickness=0, bd=0)
        for row_axes in self.axes:
            for axis in row_axes:
                apply_axis_style(axis)
        self._register()

    def axis(self, row: int, col: int):
        return self.axes[row][col]

    def hide_axis(self, row: int, col: int) -> None:
        self.axes[row][col].axis("off")

    def render(self) -> None:
        if self._destroyed:
            return
        widget = self.canvas.get_tk_widget()
        if not widget.winfo_manager():
            widget.pack(fill="both", expand=True, padx=0, pady=0)
            logger.debug("UI_CANVAS event=CANVAS_CREATED parent_id=%s canvas_id=%s", id(self.parent), id(widget))
        else:
            logger.debug("UI_CANVAS event=CANVAS_REUSED parent_id=%s canvas_id=%s", id(self.parent), id(widget))
        if not self._configure_bound:
            widget.bind("<Configure>", self._on_parent_configure, add="+")
            self._configure_bound = True
        self._resize_to_parent(force=True)

    def _on_parent_configure(self, _event) -> None:
        if self._destroyed:
            return
        if self._resize_after_id is not None:
            try:
                self.parent.after_cancel(self._resize_after_id)
            except Exception:
                pass
        self._resize_after_id = self.parent.after(80, self._resize_to_parent)

    def _resize_to_parent(self, *, force: bool = False) -> None:
        if self._destroyed:
            return
        self._resize_after_id = None
        parent_width = int(self.parent.winfo_width())
        parent_height = int(self.parent.winfo_height())
        width = int(parent_width)
        height = int(parent_height)
        if width <= 16 or height <= 16:
            return
        size = (width, height)
        if not force and self._last_parent_size == size:
            logger.debug("UI_RESIZE source=DashboardGrid changed=False width=%s height=%s", width, height)
            return
        self._last_parent_size = size
        dpi = float(self.figure.get_dpi())
        new_w, new_h = compute_responsive_figure_size(
            container_width=width,
            container_height=height,
            dpi=dpi,
            min_width_inches=2.0,
            min_height_inches=1.6,
            max_aspect_ratio=self._max_aspect_ratio,
            base_aspect_ratio=self._base_aspect_ratio,
        )
        size_inches = (round(new_w, 4), round(new_h, 4))
        size_changed = self._last_size_inches != size_inches
        self._last_size_inches = size_inches
        self.figure.set_size_inches(new_w, new_h, forward=True)
        override = getattr(self.figure, "_dashboard_layout_override", None)
        if isinstance(override, dict):
            apply_dashboard_layout(self.figure, **override)
        else:
            apply_dashboard_layout(self.figure)
        now = time.perf_counter()
        if force or size_changed or (now - self._last_resize_draw_at) >= 0.08:
            logger.debug(
                "UI_DRAW event=DRAW_REQUEST source=DashboardGrid reason=resize force=%s size_changed=%s width=%s height=%s",
                force,
                size_changed,
                width,
                height,
            )
            self.canvas.draw_idle()
            self._last_resize_draw_at = now
            logger.debug("UI_RESIZE source=DashboardGrid changed=True width=%s height=%s", width, height)

    def destroy(self) -> None:
        self._destroyed = True
        if self._resize_after_id is not None:
            try:
                self.parent.after_cancel(self._resize_after_id)
            except Exception:
                pass
            self._resize_after_id = None
        widget = self.canvas.get_tk_widget()
        if widget.winfo_exists():
            widget.destroy()
        plt.close(self.figure)
        self._unregister()

    @staticmethod
    def clear(parent: ctk.CTkFrame) -> None:
        parent_key = id(parent)
        for grid in list(DashboardGrid._instances_by_parent.get(parent_key, [])):
            grid.destroy()
        DashboardGrid._instances_by_parent.pop(parent_key, None)
        for child in parent.winfo_children():
            child.destroy()

    @staticmethod
    def force_resize_under(root: ctk.CTkFrame) -> None:
        for child in root.winfo_children():
            child_id = id(child)
            for grid in list(DashboardGrid._instances_by_parent.get(child_id, [])):
                grid._resize_to_parent(force=True)
            DashboardGrid.force_resize_under(child)

    def _register(self) -> None:
        parent_key = id(self.parent)
        DashboardGrid._instances_by_parent.setdefault(parent_key, []).append(self)

    def _unregister(self) -> None:
        parent_key = id(self.parent)
        instances = DashboardGrid._instances_by_parent.get(parent_key, [])
        if self in instances:
            instances.remove(self)
        if not instances and parent_key in DashboardGrid._instances_by_parent:
            DashboardGrid._instances_by_parent.pop(parent_key, None)
