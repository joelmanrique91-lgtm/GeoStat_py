"""Main window for the GeoStat desktop GUI."""

from __future__ import annotations

import customtkinter as ctk

from app.services.geostat_service import GeostatService
from app.ui.panels.home_panel import HomePanel


class MainWindow:
    """Configures and runs the main CustomTkinter window."""

    def __init__(self, service: GeostatService) -> None:
        self.service = service
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        self.root = ctk.CTk()
        self.root.title("GeoStat Py - Desktop Workspace")
        self.root.geometry("920x600")
        self.root.minsize(860, 540)

        self._build_layout()

    def _build_layout(self) -> None:
        header = ctk.CTkLabel(
            self.root,
            text="GeoStat Py | Local Geostatistics Desktop Workspace",
            font=ctk.CTkFont(size=18, weight="bold"),
            anchor="w",
        )
        header.pack(fill="x", padx=20, pady=(16, 8))

        home_panel = HomePanel(parent=self.root, service=self.service)
        home_panel.pack(fill="both", expand=True, padx=20, pady=(0, 20))

    def run(self) -> None:
        """Start the Tkinter event loop."""
        self.root.mainloop()
