"""Reusable matplotlib dashboard grids for CustomTkinter tabs."""

from __future__ import annotations

import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure


class DashboardGrid:
    """Simple reusable figure grid wrapper (1x1, 1x2, 2x2, 3x1)."""

    def __init__(self, parent: ctk.CTkFrame, rows: int, cols: int, figsize: tuple[float, float] = (8.0, 5.2)) -> None:
        self.parent = parent
        self.figure = Figure(figsize=figsize, dpi=100)
        self.axes = self.figure.subplots(rows, cols, squeeze=False)
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.parent)

    def axis(self, row: int, col: int):
        return self.axes[row][col]

    def hide_axis(self, row: int, col: int) -> None:
        self.axes[row][col].axis("off")

    def render(self) -> None:
        self.figure.tight_layout()
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=4, pady=4)

    @staticmethod
    def clear(parent: ctk.CTkFrame) -> None:
        for child in parent.winfo_children():
            child.destroy()
