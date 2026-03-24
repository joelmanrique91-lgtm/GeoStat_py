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
        self._apply_desktop_open_policy()

        self._build_layout()

    def _apply_desktop_open_policy(self) -> None:
        """Prefer maximized desktop startup while keeping a safe geometry fallback."""
        try:
            self.root.state("zoomed")
        except Exception:
            # Fallback to the configured geometry/minsize on platforms that do not support zoomed.
            pass

    def _build_layout(self) -> None:
        home_panel = HomePanel(parent=self.root, service=self.service)
        home_panel.pack(fill="both", expand=True, padx=14, pady=14)

    def run(self) -> None:
        """Start the Tkinter event loop."""
        self.root.mainloop()
