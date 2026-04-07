"""Main window for the GeoStat desktop GUI."""

from __future__ import annotations

import customtkinter as ctk

from app.services.geostat_service import GeostatService
from app.ui.panels.home_panel import HomePanel
from app.ui.window_geometry import Rect, clamp_to_visible_area, to_tk_geometry


class MainWindow:
    """Configures and runs the main CustomTkinter window."""

    def __init__(self, service: GeostatService) -> None:
        self._geometry_after_id: str | None = None
        self._is_applying_geometry = False
        self._last_window_state = "normal"
        self.service = service
        ctk.set_appearance_mode("Light")
        ctk.set_default_color_theme("blue")

        self.root = ctk.CTk()
        self.root.title("GeoStat Py - Geostatistics Desktop")
        self._configure_startup_geometry()

        self._build_layout()

    def _configure_startup_geometry(self) -> None:
        visible = self._screen_area()

        target_width = min(1360, max(980, visible.width - 80))
        target_height = min(860, max(680, visible.height - 80))

        min_width = min(1180, max(900, visible.width - 160))
        min_height = min(760, max(620, visible.height - 160))
        self.root.minsize(min_width, min_height)

        centered = Rect(
            x=visible.x + max((visible.width - target_width) // 2, 0),
            y=visible.y + max((visible.height - target_height) // 2, 0),
            width=target_width,
            height=target_height,
        )
        geometry = clamp_to_visible_area(centered, visible=visible, min_width=min_width, min_height=min_height)
        self.root.geometry(to_tk_geometry(geometry))

    def _build_layout(self) -> None:
        home_panel = HomePanel(parent=self.root, service=self.service)
        home_panel.pack(fill="both", expand=True, padx=10, pady=10)

    def _screen_area(self) -> Rect:
        width = int(self.root.winfo_screenwidth() or 1360)
        height = int(self.root.winfo_screenheight() or 860)
        x = 0
        y = 0
        return Rect(x=x, y=y, width=max(640, width), height=max(480, height))

    def run(self) -> None:
        """Start the Tkinter event loop."""
        self.root.mainloop()
