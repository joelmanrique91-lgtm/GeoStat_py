"""Main window for the GeoStat desktop GUI."""

from __future__ import annotations

import customtkinter as ctk

from app.services.geostat_service import GeostatService
from app.ui.panels.home_panel import HomePanel


class MainWindow:
    """Configures and runs the main CustomTkinter window."""

    def __init__(self, service: GeostatService) -> None:
        self.service = service
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        self.root = ctk.CTk()
        self.root.title("GeoStat Py - Geostatistics Desktop")
        self.root.geometry("1360x860")
        self.root.minsize(1180, 760)

        self._build_layout()

    def _build_layout(self) -> None:
        home_panel = HomePanel(parent=self.root, service=self.service)
        home_panel.pack(fill="both", expand=True, padx=10, pady=10)

    def run(self) -> None:
        """Start the Tkinter event loop."""
        self.root.mainloop()
