"""Reusable matplotlib dashboard grids for CustomTkinter tabs."""

from __future__ import annotations

import customtkinter as ctk
from matplotlib import pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from app.ui.theme import apply_axis_style, apply_figure_theme


class DashboardGrid:
    """Simple reusable figure grid wrapper (1x1, 1x2, 2x2, 3x1)."""
    _instances_by_parent: dict[int, list["DashboardGrid"]] = {}

    def __init__(self, parent: ctk.CTkFrame, rows: int, cols: int, figsize: tuple[float, float] = (8.0, 5.2)) -> None:
        self.parent = parent
        self.figure = Figure(figsize=figsize, dpi=100)
        apply_figure_theme(self.figure)
        self.axes = self.figure.subplots(rows, cols, squeeze=False)
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.parent)
        for row_axes in self.axes:
            for axis in row_axes:
                apply_axis_style(axis)
        self._register()

    def axis(self, row: int, col: int):
        return self.axes[row][col]

    def hide_axis(self, row: int, col: int) -> None:
        self.axes[row][col].axis("off")

    def render(self) -> None:
        self.figure.tight_layout(pad=1.1, w_pad=0.9, h_pad=0.9)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=2, pady=2)

    def destroy(self) -> None:
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
