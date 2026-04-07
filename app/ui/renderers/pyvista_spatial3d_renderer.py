"""High-impact spatial renderer using dedicated external 3D viewers.

This renderer intentionally avoids heavy embedded Tk 3D loops. It opens a dedicated
interactive 3D viewer (PyVista preferred, Plotly fallback) so the desktop UI remains
responsive while delivering a significantly better 3D experience.
"""

from __future__ import annotations

from dataclasses import dataclass
import threading
from typing import Any

import customtkinter as ctk

from app.models.spatial import AssayIntervals3D, DrillholeTrajectory, PointCloudGeometry, SceneState
from app.ui.renderers.base import Spatial3DRenderer


@dataclass(frozen=True)
class _BackendState:
    backend: str
    reason: str


class PyVistaSpatial3DRenderer(Spatial3DRenderer):
    def __init__(self) -> None:
        self._last_state = _BackendState(backend="", reason="")
        self._latest_scene: SceneState | None = None

    def _resolve_backend(self) -> _BackendState:
        try:
            import pyvista  # noqa: F401
            import vtk  # noqa: F401

            return _BackendState("pyvista", "ok")
        except Exception:
            pass
        try:
            import plotly  # noqa: F401

            return _BackendState("plotly", "ok")
        except Exception as exc:
            return _BackendState("", f"No hay backend 3D dedicado disponible (pyvista/plotly): {exc}")

    def is_available(self) -> tuple[bool, str]:
        self._last_state = self._resolve_backend()
        if not self._last_state.backend:
            return False, self._last_state.reason
        return True, self._last_state.backend

    def create_widget(self, parent: ctk.CTkFrame) -> Any:
        host = ctk.CTkFrame(parent, fg_color="transparent")
        host.grid_columnconfigure(0, weight=1)
        return host

    def render(self, widget: Any, scene: SceneState, color_display_label: str) -> None:
        self._latest_scene = scene
        if not isinstance(widget, ctk.CTkFrame):
            return
        for child in widget.winfo_children():
            child.destroy()

        backend = self._last_state.backend or self._resolve_backend().backend
        info = ctk.CTkFrame(widget, fg_color="transparent")
        info.grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(
            info,
            text=(
                f"Viewer 3D dedicado ({backend.upper()}) · {color_display_label}\n"
                "Se abre en ventana/navegador externo para evitar bloqueos de Tk y mejorar fluidez."
            ),
            justify="left",
        ).pack(anchor="w", padx=4, pady=(2, 6))
        ctk.CTkButton(info, text="Abrir viewer 3D dedicado", command=self._open_external_viewer, height=32).pack(anchor="w", padx=4, pady=(0, 4))

    def _open_external_viewer(self) -> None:
        if self._latest_scene is None:
            return
        backend = self._last_state.backend or self._resolve_backend().backend
        if backend == "pyvista":
            threading.Thread(target=self._open_pyvista, args=(self._latest_scene,), daemon=True).start()
            return
        threading.Thread(target=self._open_plotly, args=(self._latest_scene,), daemon=True).start()

    def launch_external(self, scene: SceneState, color_display_label: str = "") -> None:
        """Open external 3D viewer explicitly (secondary action)."""
        _ = color_display_label
        self._latest_scene = scene
        self._last_state = self._resolve_backend()
        self._open_external_viewer()

    def _open_pyvista(self, scene: SceneState) -> None:
        import pyvista as pv

        point_layer = next((layer for layer in scene.layers if layer.layer_type == "point_cloud"), None)
        if point_layer is None or not isinstance(point_layer.payload, PointCloudGeometry):
            return
        payload = point_layer.payload
        points = list(payload.points_xyz)
        cloud = pv.PolyData(points)
        cloud["values"] = list(payload.color_values)
        plotter = pv.Plotter(title="GeoStat Spatial Viewer")
        plotter.set_background("#0c1726")
        plotter.add_mesh(cloud, scalars="values", cmap="viridis", point_size=float(point_layer.style.get("size", 8.0)), render_points_as_spheres=True, opacity=float(point_layer.opacity))

        dr = next((layer for layer in scene.layers if layer.layer_type == "drillholes" and layer.visible), None)
        if dr is not None and isinstance(dr.payload, tuple):
            for traj in dr.payload:
                if not isinstance(traj, DrillholeTrajectory) or len(traj.points_xyz) < 2:
                    continue
                spline = pv.Spline(list(traj.points_xyz), len(traj.points_xyz))
                plotter.add_mesh(spline, color="#d9dde4", line_width=2.0, opacity=float(dr.opacity))

        iv = next((layer for layer in scene.layers if layer.layer_type == "assay_intervals" and layer.visible), None)
        if iv is not None and isinstance(iv.payload, tuple):
            for intervals in iv.payload:
                if not isinstance(intervals, AssayIntervals3D):
                    continue
                for seg in intervals.segments_xyz:
                    line = pv.Line(seg[0], seg[1])
                    plotter.add_mesh(line, color="#ff9f43", line_width=3.0, opacity=float(iv.opacity))

        plotter.show_grid(color="#7f8fa6")
        plotter.show()

    def _open_plotly(self, scene: SceneState) -> None:
        import plotly.graph_objects as go

        point_layer = next((layer for layer in scene.layers if layer.layer_type == "point_cloud"), None)
        if point_layer is None or not isinstance(point_layer.payload, PointCloudGeometry):
            return
        payload = point_layer.payload
        xs = [p[0] for p in payload.points_xyz]
        ys = [p[1] for p in payload.points_xyz]
        zs = [p[2] for p in payload.points_xyz]
        fig = go.Figure()
        fig.add_trace(
            go.Scatter3d(
                x=xs,
                y=ys,
                z=zs,
                mode="markers",
                marker=dict(size=float(point_layer.style.get("size", 4.0)), color=list(payload.color_values), colorscale="Viridis", opacity=float(point_layer.opacity)),
                name="Muestras",
            )
        )

        dr = next((layer for layer in scene.layers if layer.layer_type == "drillholes" and layer.visible), None)
        if dr is not None and isinstance(dr.payload, tuple):
            for traj in dr.payload:
                if not isinstance(traj, DrillholeTrajectory):
                    continue
                fig.add_trace(
                    go.Scatter3d(
                        x=[p[0] for p in traj.points_xyz],
                        y=[p[1] for p in traj.points_xyz],
                        z=[p[2] for p in traj.points_xyz],
                        mode="lines",
                        line=dict(color="#dfe6e9", width=3),
                        opacity=float(dr.opacity),
                        showlegend=False,
                    )
                )

        fig.update_layout(
            title="GeoStat Spatial Viewer (WebGL)",
            template="plotly_dark",
            scene=dict(bgcolor="#0c1726"),
        )
        fig.show(renderer="browser")

    def show_unavailable(self, widget: Any, reason: str) -> None:
        if isinstance(widget, ctk.CTkFrame):
            for child in widget.winfo_children():
                child.destroy()
            ctk.CTkLabel(widget, text=reason, justify="left").grid(row=0, column=0, sticky="w")
