"""Controller that orchestrates spatial scene build, cache and renderer delegation."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha1

from app.models.spatial import SceneState
from app.services.geometry_cache_service import GeometryCacheService
from app.services.scene_builder_service import SceneBuilderService
from app.services.spatial_geometry_service import SpatialGeometryService


@dataclass(frozen=True)
class SpatialRenderResult:
    success: bool
    message: str
    fallback_to_2d: bool = False
    scene: SceneState | None = None


class SpatialViewerController:
    def __init__(self, service, *, geometry_cache: GeometryCacheService | None = None) -> None:
        self.service = service
        self.geometry_cache = geometry_cache or GeometryCacheService()
        self.geometry_service = SpatialGeometryService()
        self.scene_builder = SceneBuilderService()

    def build_or_get_scene(self, *, color_by: str | None, view_mode: str = "3d") -> SceneState:
        snapshot = self.service.get_analysis_context_snapshot()
        active_variable = str(color_by or snapshot.get("resolved_target_column") or "")
        active_domain = str(snapshot.get("active_domain_filter") or "Todos")
        dataset_signature = self._dataset_signature()
        filters = {
            "active_domain_filter": snapshot.get("active_domain_filter", ""),
            "active_domain_column": snapshot.get("active_domain_column", ""),
        }
        cache_key = self.geometry_cache.build_key(
            dataset_signature=dataset_signature,
            active_domain=active_domain,
            active_variable=active_variable,
            view_mode=view_mode,
            filters=filters,
        )
        cached = self.geometry_cache.get(cache_key)
        if isinstance(cached, SceneState):
            return cached

        prep = self.service.prepare_visual_3d_data(color_by=active_variable)
        if not prep.success or prep.spatial_3d_data is None:
            raise ValueError(prep.message)

        df = self.service._get_filtered_dataframe(snapshot)
        if df is None:
            raise ValueError("No hay dataset filtrado disponible para construir escena.")
        payload = prep.spatial_3d_data
        geometry = self.geometry_service.build_geometry(
            df,
            x_col=self.service.variable_config.x_column,
            y_col=self.service.variable_config.y_column,
            z_col=self.service.variable_config.z_column,
            color_col=payload.color_label,
            hole_id_col=(self.service.variable_config.hole_id_column or "") if self.service.variable_config else None,
            color_mode=payload.color_mode,
            color_tick_positions=payload.color_tick_positions,
            color_tick_labels=payload.color_tick_labels,
        )
        scene = self.scene_builder.build_scene(
            geometry,
            active_variable=active_variable,
            active_domain=active_domain,
            context_key=f"{dataset_signature}:{active_variable}:{active_domain}:{view_mode}",
            render_mode=view_mode,
        )
        self.geometry_cache.put(cache_key, scene)
        return scene

    def render_scene(self, *, parent, renderer, color_by: str | None, view_mode: str = "3d") -> SpatialRenderResult:
        available, reason = renderer.is_available()
        widget = renderer.create_widget(parent)
        widget.grid(row=1, column=0, sticky="nsew", padx=4, pady=(2, 0))

        if not available:
            renderer.show_unavailable(widget, f"{reason}. Volviendo automáticamente a 2D.")
            return SpatialRenderResult(False, reason, fallback_to_2d=True)

        try:
            scene = self.build_or_get_scene(color_by=color_by, view_mode=view_mode)
        except Exception as exc:  # noqa: BLE001
            renderer.show_unavailable(widget, f"No se pudo renderizar 3D: {exc}. Volviendo a 2D.")
            return SpatialRenderResult(False, str(exc), fallback_to_2d=True)

        renderer.render(widget, scene, scene.active_variable or "No definido")
        return SpatialRenderResult(True, "ok", scene=scene)

    def _dataset_signature(self) -> str:
        dataset = self.service.current_dataset
        if dataset is None:
            return "no-dataset"
        raw = f"{dataset.file_path}:{dataset.row_count}:{dataset.column_count}"
        return sha1(raw.encode("utf-8")).hexdigest()
