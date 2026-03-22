"""PyVista 3D renderer pilot adapter.

Current status:
- This adapter is intentionally conservative for Tk/CustomTkinter.
- If PyVista/VTK (and optional Tk-compatible embedding strategy) is not available,
  the adapter reports `is_available=False` so HomePanel can fallback to Matplotlib.
"""

from __future__ import annotations

from typing import Any

import customtkinter as ctk

from app.services.visualization_service import Spatial3DDataBundle
from app.ui.renderers.base import Spatial3DRenderer


class PyVistaSpatial3DRenderer(Spatial3DRenderer):
    """Availability-gated PyVista pilot renderer.

    This pilot keeps integration risk low:
    - It only enables itself when PyVista + VTK can be imported.
    - It does not force a UI toolkit migration in this phase.
    - It exposes the same renderer interface for controlled fallback.
    """

    def __init__(self) -> None:
        self._last_unavailable_reason: str = ""

    def is_available(self) -> tuple[bool, str]:
        try:
            import pyvista  # noqa: F401
            import vtk  # noqa: F401
        except Exception as exc:
            self._last_unavailable_reason = f"PyVista no disponible en entorno actual: {exc}"
            return False, self._last_unavailable_reason

        # NOTE: Embedded Tk integration with interactive PyVista requires additional
        # integration work (e.g., dedicated event-loop bridge). This pilot keeps
        # behavior safe by deferring enablement until that bridge is implemented.
        self._last_unavailable_reason = (
            "PyVista detectado, pero integración embebida Tk no habilitada en esta fase "
            "(pendiente puente de event-loop)."
        )
        return False, self._last_unavailable_reason

    def create_widget(self, parent: ctk.CTkFrame) -> Any:
        host = ctk.CTkFrame(parent, fg_color="transparent")
        host.grid_columnconfigure(0, weight=1)
        return host

    def render(self, widget: Any, data: Spatial3DDataBundle, color_display_label: str) -> None:
        # Intentionally unreachable while is_available() is False.
        _ = (widget, data, color_display_label)

    def show_unavailable(self, widget: Any, reason: str) -> None:
        if isinstance(widget, ctk.CTkFrame):
            for child in widget.winfo_children():
                child.destroy()
            ctk.CTkLabel(widget, text=reason, justify="left").grid(row=0, column=0, sticky="w")
