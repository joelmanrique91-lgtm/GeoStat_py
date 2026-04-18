"""Matplotlib 3D renderer adapter for Spatial3DView."""

from __future__ import annotations

import customtkinter as ctk

from app.models.spatial import SceneState
from app.ui.panels.spatial_3d_view import Spatial3DView, is_3d_backend_available
from app.ui.renderers.base import Spatial3DRenderer, Spatial3DRendererCapabilities


class MatplotlibSpatial3DRenderer(Spatial3DRenderer):
    def capabilities(self) -> Spatial3DRendererCapabilities:
        return Spatial3DRendererCapabilities(
            backend="matplotlib",
            supports_points=True,
            supports_mesh=False,
            supports_drillholes=False,
            expected_performance="medium",
        )

    def is_available(self) -> tuple[bool, str]:
        return is_3d_backend_available()

    def create_widget(self, parent: ctk.CTkFrame) -> Spatial3DView:
        return Spatial3DView(parent)

    def render(self, widget: Spatial3DView, scene: SceneState, color_display_label: str) -> None:
        widget.update_scene(scene, color_display_label)

    def show_unavailable(self, widget: Spatial3DView, reason: str) -> None:
        widget.show_unavailable(reason)
