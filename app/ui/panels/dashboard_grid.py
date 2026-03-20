"""Reusable matplotlib dashboard grids for CustomTkinter tabs."""

from __future__ import annotations

import customtkinter as ctk
from matplotlib import pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure


class DashboardGrid:
    """Simple reusable figure grid wrapper (1x1, 1x2, 2x2, 3x1)."""

    def __init__(self, parent: ctk.CTkFrame, rows: int, cols: int, figsize: tuple[float, float] = (8.0, 5.2)) -> None:
        self.parent = parent
        self.figure = Figure(figsize=figsize, dpi=100)
        self.figure.patch.set_facecolor("#f7f8fb")
        self.axes = self.figure.subplots(rows, cols, squeeze=False)
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.parent)
        for row_axes in self.axes:
            for axis in row_axes:
                axis.set_facecolor("#ffffff")
                axis.grid(color="#d6deea", alpha=0.8, linestyle="--", linewidth=0.55)
                axis.tick_params(labelsize=8)
                axis.tick_params(colors="#334155")
                for spine in axis.spines.values():
                    spine.set_color("#cbd5e1")

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

    @staticmethod
    def clear(parent: ctk.CTkFrame) -> None:
        for child in parent.winfo_children():
            child.destroy()
        for fig_num in plt.get_fignums():
            plt.close(fig_num)
