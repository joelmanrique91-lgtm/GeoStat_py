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
    ) -> SceneState:
        layers: list[SceneLayer] = []
        color_mapping = ColorMappingConfig(variable=active_variable)
        layers.append(
            SceneLayer(
                layer_id="points",
                layer_type="point_cloud",
                visible=True,
                opacity=0.85,
                color_by=active_variable,
                display_name="Muestras",
                payload=geometry.point_cloud,
                style={"scheme": color_mapping.scheme, "size": 7},
            )
        )
        if geometry.drillholes:
            layers.append(
                SceneLayer(
                    layer_id="drillholes",
                    layer_type="drillholes",
                    visible=True,
                    opacity=0.65,
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
                    visible=False,
                    opacity=0.75,
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
            clipping_state=ClippingState(),
            render_mode=render_mode,
            context_key=context_key,
        )
