"""Tests for SceneState persistence service."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.models.spatial import PointCloudGeometry
from app.services.scene_builder_service import SceneBuilderService
from app.services.scene_persistence_service import ScenePersistenceService
from app.services.spatial_geometry_service import SpatialGeometryPayload


class ScenePersistenceServiceTests(unittest.TestCase):
    def test_save_and_load_scene(self) -> None:
        point_cloud = PointCloudGeometry(
            points_xyz=((0.0, 0.0, 0.0),),
            color_values=(1.0,),
            color_mode="numeric",
            color_label="au",
            source_point_count=1,
            rendered_point_count=1,
        )
        scene = SceneBuilderService().build_scene(
            SpatialGeometryPayload(point_cloud=point_cloud, drillholes=(), assay_intervals=()),
            active_variable="au",
            active_domain="Todos",
            context_key="k",
        )
        service = ScenePersistenceService()
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "scene.json"
            service.save(scene, str(path))
            loaded = service.load(str(path))
        self.assertEqual(loaded.active_variable, "au")
        self.assertEqual(len(loaded.layers), len(scene.layers))


if __name__ == "__main__":
    unittest.main()
