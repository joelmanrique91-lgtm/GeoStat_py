"""Main window for the GeoStat desktop GUI."""

from __future__ import annotations

import customtkinter as ctk

from app.services.geostat_service import GeostatService
from app.ui.panels.home_panel import HomePanel
from app.ui.window_geometry import Rect, clamp_to_visible_area, parse_tk_geometry, to_tk_geometry


class MainWindow:
    """Configures and runs the main CustomTkinter window."""

    def __init__(self, service: GeostatService) -> None:
        self._geometry_after_id: str | None = None
        self._is_applying_geometry = False
        self._last_window_state = "normal"
        self.service = service
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        self.root = ctk.CTk()
        self.root.title("GeoStat Py - Geostatistics Desktop")
        self._configure_window_policy()

        self._build_layout()

    def _configure_window_policy(self) -> None:
        visible = self._visible_area()

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
        self._apply_geometry(clamp_to_visible_area(centered, visible=visible, min_width=min_width, min_height=min_height))

        self.root.bind("<Configure>", self._on_root_configure, add="+")
        self.root.bind("<Map>", self._on_root_map, add="+")
        self.root.after(0, lambda: self._sanitize_window_geometry(force=True))

    def _build_layout(self) -> None:
        home_panel = HomePanel(parent=self.root, service=self.service)
        home_panel.pack(fill="both", expand=True, padx=10, pady=10)

    def _visible_area(self) -> Rect:
        self.root.update_idletasks()
        width = int(self.root.winfo_vrootwidth() or self.root.winfo_screenwidth() or 1360)
        height = int(self.root.winfo_vrootheight() or self.root.winfo_screenheight() or 860)
        x = int(self.root.winfo_vrootx() or 0)
        y = int(self.root.winfo_vrooty() or 0)
        return Rect(x=x, y=y, width=max(640, width), height=max(480, height))

    def _on_root_map(self, _event) -> None:
        self._schedule_sanitize(delay_ms=20)

    def _on_root_configure(self, _event) -> None:
        if self._is_applying_geometry:
            return
        state = self.root.state()
        if state != self._last_window_state:
            self._last_window_state = state
            if state == "normal":
                self._schedule_sanitize(delay_ms=20)
            return
        if state == "normal":
            self._schedule_sanitize(delay_ms=120)

    def _schedule_sanitize(self, *, delay_ms: int) -> None:
        if self._geometry_after_id is not None:
            self.root.after_cancel(self._geometry_after_id)
        self._geometry_after_id = self.root.after(delay_ms, self._sanitize_window_geometry)

    def _sanitize_window_geometry(self, *, force: bool = False) -> None:
        self._geometry_after_id = None
        if self.root.state() != "normal" and not force:
            return
        current = parse_tk_geometry(self.root.winfo_geometry())
        if current is None:
            current = Rect(
                x=int(self.root.winfo_x()),
                y=int(self.root.winfo_y()),
                width=int(self.root.winfo_width()),
                height=int(self.root.winfo_height()),
            )
        min_size = self.root.minsize()
        min_width = int(min_size[0] or 900)
        min_height = int(min_size[1] or 620)
        normalized = clamp_to_visible_area(
            current,
            visible=self._visible_area(),
            min_width=min_width,
            min_height=min_height,
        )
        if normalized != current:
            self._apply_geometry(normalized)

    def _apply_geometry(self, rect: Rect) -> None:
        self._is_applying_geometry = True
        try:
            self.root.geometry(to_tk_geometry(rect))
            self.root.update_idletasks()
        finally:
            self._is_applying_geometry = False

    def run(self) -> None:
        """Start the Tkinter event loop."""
        self.root.mainloop()
