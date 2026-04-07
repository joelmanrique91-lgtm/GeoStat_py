"""Compose typed logical scene state from spatial geometry payloads."""

from __future__ import annotations

from app.models.spatial import CameraState, ClippingState, ColorMappingConfig, SceneLayer, SceneState
from app.services.spatial_geometry_service import SpatialGeometryPayload


class SceneBuilderService:
    def build_scene(
        self,
        geometry: SpatialGeometryPayload,
        *,
        active_variable: str,
        active_domain: str,
        context_key: str,
        render_mode: str = "3d",
        view_profile: str = "Puntos + Trazas",
        point_size: float = 7.0,
        opacity: float = 0.85,
        z_focus_pct: float = 100.0,
    ) -> SceneState:
        layers: list[SceneLayer] = []
        color_mapping = ColorMappingConfig(variable=active_variable)
        mode = str(view_profile or "Puntos + Trazas")
        z_values = [p[2] for p in geometry.point_cloud.points_xyz]
        z_min = min(z_values) if z_values else None
        z_max = max(z_values) if z_values else None
        clipping_enabled = bool(z_min is not None and z_max is not None and float(z_focus_pct) < 99.9)
        clip_min = z_min
        clip_max = z_max
        if clipping_enabled and z_min is not None and z_max is not None:
            span = max(z_max - z_min, 1e-9)
            keep = max(0.05, min(float(z_focus_pct), 100.0) / 100.0)
            margin = span * (1.0 - keep) * 0.5
            clip_min = z_min + margin
            clip_max = z_max - margin

        show_points = mode in {"Puntos", "Puntos + Trazas", "Dominio foco"}
        show_traces = mode in {"Puntos + Trazas", "Dominio foco"}
        show_intervals = mode in {"Intervalos", "Dominio foco"}
        point_opacity = float(opacity)
        if mode == "Dominio foco":
            point_opacity = max(0.2, min(1.0, point_opacity * 0.7))
        layers.append(
            SceneLayer(
                layer_id="points",
                layer_type="point_cloud",
                visible=show_points,
                opacity=point_opacity,
                color_by=active_variable,
                display_name="Muestras",
                payload=geometry.point_cloud,
                style={"scheme": color_mapping.scheme, "size": float(point_size), "profile": mode},
            )
        )
        if geometry.drillholes:
            layers.append(
                SceneLayer(
                    layer_id="drillholes",
                    layer_type="drillholes",
                    visible=show_traces,
                    opacity=0.72 if mode == "Dominio foco" else 0.62,
                    color_by=None,
                    display_name="Trayectorias",
                    payload=geometry.drillholes,
                    style={"line_width": 1.4, "color": "#d9dde4"},
                )
            )
        if geometry.assay_intervals:
            layers.append(
                SceneLayer(
                    layer_id="assay_intervals",
                    layer_type="assay_intervals",
                    visible=show_intervals,
                    opacity=0.82 if mode == "Intervalos" else 0.72,
                    color_by=active_variable,
                    display_name="Intervalos",
                    payload=geometry.assay_intervals,
                    style={"line_width": 2.0},
                )
            )
        return SceneState(
            layers=tuple(layers),
            active_variable=active_variable,
            active_domain=active_domain or "Todos",
            camera_state=CameraState(),
            clipping_state=ClippingState(enabled=clipping_enabled, mode="z_focus" if clipping_enabled else "none", z_min=clip_min, z_max=clip_max),
            render_mode=render_mode,
            context_key=context_key,
            diagnostics={
                "view_profile": mode,
                "point_size": float(point_size),
                "opacity": float(point_opacity),
                "point_count": len(geometry.point_cloud.points_xyz),
                "drillhole_count": len(geometry.drillholes),
                "interval_count": sum(len(item.segments_xyz) for item in geometry.assay_intervals),
                "z_focus_pct": float(z_focus_pct),
            },
        )
