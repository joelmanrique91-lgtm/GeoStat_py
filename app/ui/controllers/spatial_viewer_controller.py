"""Controller that orchestrates spatial scene build, cache and renderer delegation."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha1
import time

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
    backend: str = ""
    geometry_ms: float = 0.0
    render_ms: float = 0.0


class SpatialViewerController:
    def __init__(self, service, *, geometry_cache: GeometryCacheService | None = None) -> None:
        self.service = service
        self.geometry_cache = geometry_cache or GeometryCacheService()
        self.geometry_service = SpatialGeometryService()
        self.scene_builder = SceneBuilderService()

    def build_or_get_scene(
        self,
        *,
        color_by: str | None,
        view_mode: str = "3d",
        quality: str = "Media",
        style_options: dict[str, object] | None = None,
    ) -> SceneState:
        snapshot = self.service.get_analysis_context_snapshot()
        active_variable = str(color_by or snapshot.get("resolved_target_column") or "")
        active_domain = str(snapshot.get("active_domain_filter") or "Todos")
        dataset_signature = self._dataset_signature()
        style = style_options or {}
        filters = {
            "active_domain_filter": snapshot.get("active_domain_filter", ""),
            "active_domain_column": snapshot.get("active_domain_column", ""),
            "quality": quality,
        }
        cache_key = self.geometry_cache.build_key(
            dataset_signature=dataset_signature,
            active_domain=active_domain,
            active_variable=active_variable,
            view_mode=f"{view_mode}:scene",
            filters=filters,
        )
        cached = self.geometry_cache.get(cache_key)
        if isinstance(cached, SceneState):
            return cached

        geometry = self._build_or_get_geometry(
            snapshot=snapshot,
            active_variable=active_variable,
            dataset_signature=dataset_signature,
            quality=quality,
        )
        scene = self.scene_builder.build_scene(
            geometry,
            active_variable=active_variable,
            active_domain=active_domain,
            context_key=f"{dataset_signature}:{active_variable}:{active_domain}:{view_mode}",
            render_mode=view_mode,
            view_profile=str(style.get("profile", "Puntos + Trazas")),
            point_size=float(style.get("point_size", 7.0)),
            opacity=float(style.get("opacity", 0.85)),
            z_focus_pct=float(style.get("z_focus_pct", 100.0)),
        )
        self.geometry_cache.put(cache_key, scene)
        return scene

    def _build_or_get_geometry(self, *, snapshot: dict[str, object], active_variable: str, dataset_signature: str, quality: str):
        geometry_key = self.geometry_cache.build_key(
            dataset_signature=dataset_signature,
            active_domain=str(snapshot.get("active_domain_filter") or "Todos"),
            active_variable=active_variable,
            view_mode="geometry",
            filters={"quality": quality},
        )
        cached = self.geometry_cache.get(geometry_key)
        if cached is not None:
            return cached
        max_points = {"Alta": 50000, "Media": 28000, "Ligera": 14000}.get(str(quality), 28000)
        prep = self.service.prepare_visual_3d_data(color_by=active_variable, max_points=max_points)
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
        self.geometry_cache.put(geometry_key, geometry)
        return geometry

    def render_scene(
        self,
        *,
        parent,
        renderer,
        color_by: str | None,
        view_mode: str = "3d",
        quality: str = "Media",
        style_options: dict[str, object] | None = None,
    ) -> SpatialRenderResult:
        available, reason = renderer.is_available()
        widget = renderer.create_widget(parent)
        widget.grid(row=1, column=0, sticky="nsew", padx=4, pady=(2, 0))
        backend_name = renderer.__class__.__name__

        if not available:
            renderer.show_unavailable(widget, f"{reason}. Volviendo automáticamente a 2D.")
            return SpatialRenderResult(False, reason, fallback_to_2d=True, backend=backend_name)

        start_geometry = time.perf_counter()
        try:
            scene = self.build_or_get_scene(
                color_by=color_by,
                view_mode=view_mode,
                quality=quality,
                style_options=style_options,
            )
        except Exception as exc:  # noqa: BLE001
            renderer.show_unavailable(widget, f"No se pudo renderizar 3D: {exc}. Volviendo a 2D.")
            return SpatialRenderResult(False, str(exc), fallback_to_2d=True, backend=backend_name)
        geometry_ms = (time.perf_counter() - start_geometry) * 1000.0

        start_render = time.perf_counter()
        renderer.render(widget, scene, scene.active_variable or "No definido")
        render_ms = (time.perf_counter() - start_render) * 1000.0
        scene.diagnostics["geometry_ms"] = round(geometry_ms, 2)
        scene.diagnostics["render_ms"] = round(render_ms, 2)
        scene.diagnostics["backend"] = backend_name
        return SpatialRenderResult(True, "ok", scene=scene, backend=backend_name, geometry_ms=geometry_ms, render_ms=render_ms)

    def _dataset_signature(self) -> str:
        dataset = self.service.current_dataset
        if dataset is None:
            return "no-dataset"
        raw = f"{dataset.file_path}:{dataset.row_count}:{dataset.column_count}"
        return sha1(raw.encode("utf-8")).hexdigest()
