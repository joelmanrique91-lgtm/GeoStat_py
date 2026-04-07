"""PyVista 3D renderer pilot adapter.

Current status:
- This adapter is intentionally conservative for Tk/CustomTkinter.
- If PyVista/VTK (and optional Tk-compatible embedding strategy) is not available,
  the adapter reports `is_available=False` so HomePanel can fallback to Matplotlib.
"""

from __future__ import annotations

import os
from typing import Any

import customtkinter as ctk

from app.models.spatial import SceneState
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
        self._feature_toggle_env = "GEOSTAT_ENABLE_PYVISTA_3D"
        self._policy_disabled_message = (
            "PyVista/VTK detectado, pero backend 3D deshabilitado por política "
            f"(exporta {self._feature_toggle_env}=1 para habilitar modo experimental)."
        )

    def is_available(self) -> tuple[bool, str]:
        try:
            import pyvista  # noqa: F401
            import vtk  # noqa: F401
        except Exception as exc:
            self._last_unavailable_reason = f"PyVista no disponible en entorno actual: {exc}"
            return False, self._last_unavailable_reason

        if not self._is_feature_enabled():
            self._last_unavailable_reason = self._policy_disabled_message
            return False, self._last_unavailable_reason

        self._last_unavailable_reason = ""
        return True, "ok"

    def _is_feature_enabled(self) -> bool:
        raw = os.environ.get(self._feature_toggle_env, "")
        return str(raw).strip().lower() in {"1", "true", "yes", "on", "enabled"}

    def create_widget(self, parent: ctk.CTkFrame) -> Any:
        host = ctk.CTkFrame(parent, fg_color="transparent")
        host.grid_columnconfigure(0, weight=1)
        return host

    def render(self, widget: Any, scene: SceneState, color_display_label: str) -> None:
        # Embedded interactive PyVista is still experimental in Tk host.
        # Keep UX explicit to avoid blank panels if feature-toggle is enabled.
        self.show_unavailable(
            widget,
            (
                "Backend PyVista habilitado en modo experimental, pero render embebido Tk "
                "aún no implementado de forma estable. Se recomienda usar fallback 2D/3D matplotlib."
            ),
        )
        _ = (scene, color_display_label)

    def show_unavailable(self, widget: Any, reason: str) -> None:
        if isinstance(widget, ctk.CTkFrame):
            for child in widget.winfo_children():
                child.destroy()
            ctk.CTkLabel(widget, text=reason, justify="left").grid(row=0, column=0, sticky="w")
