"""Reusable matplotlib dashboard grids for CustomTkinter tabs."""

from __future__ import annotations

import customtkinter as ctk
from matplotlib import pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from app.ui.theme import CHART_BG, apply_axis_style, apply_figure_theme


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
    ) -> None:
        self.parent = parent
        self._last_parent_size: tuple[int, int] | None = None
        self._resize_after_id: str | None = None
        self._configure_bound = False
        self._configured_figsize = figsize
        figure_kwargs: dict[str, object] = {"dpi": 100, "constrained_layout": True}
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
        widget = self.canvas.get_tk_widget()
        if not widget.winfo_manager():
            widget.pack(fill="both", expand=True, padx=0, pady=0)
        if not self._configure_bound:
            widget.bind("<Configure>", self._on_parent_configure, add="+")
            self.parent.bind("<Configure>", self._on_parent_configure, add="+")
            self._configure_bound = True
        self._resize_to_parent(force=True)

    def _on_parent_configure(self, _event) -> None:
        if self._resize_after_id is not None:
            try:
                self.parent.after_cancel(self._resize_after_id)
            except Exception:
                pass
        self._resize_after_id = self.parent.after(80, self._resize_to_parent)

    def _resize_to_parent(self, *, force: bool = False) -> None:
        self._resize_after_id = None
        widget = self.canvas.get_tk_widget()
        width = int(widget.winfo_width() or self.parent.winfo_width())
        height = int(widget.winfo_height() or self.parent.winfo_height())
        if width <= 16 or height <= 16:
            self.parent.after(50, self._resize_to_parent)
            return
        size = (width, height)
        if not force and self._last_parent_size == size:
            return
        self._last_parent_size = size
        dpi = float(self.figure.get_dpi())
        new_w = max(width / dpi, 2.0)
        new_h = max(height / dpi, 1.6)
        self.figure.set_size_inches(new_w, new_h, forward=True)
        self.canvas.draw_idle()

    def destroy(self) -> None:
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
