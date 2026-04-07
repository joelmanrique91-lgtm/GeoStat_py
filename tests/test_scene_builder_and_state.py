"""Tests for SceneBuilderService and SceneState persistence contracts."""

from __future__ import annotations

import unittest

from app.models.spatial import PointCloudGeometry, SceneState
from app.services.scene_builder_service import SceneBuilderService
from app.services.spatial_geometry_service import SpatialGeometryPayload


class SceneBuilderStateTests(unittest.TestCase):
    def _payload(self) -> SpatialGeometryPayload:
        point_cloud = PointCloudGeometry(
            points_xyz=((0.0, 0.0, 0.0), (1.0, 1.0, 1.0)),
            color_values=(1.0, 2.0),
            color_mode="numeric",
            color_label="au",
            source_point_count=2,
            rendered_point_count=2,
        )
        return SpatialGeometryPayload(point_cloud=point_cloud, drillholes=(), assay_intervals=())

    def test_scene_builder_creates_layers(self) -> None:
        builder = SceneBuilderService()
        scene = builder.build_scene(self._payload(), active_variable="au", active_domain="A", context_key="ctx")
        self.assertEqual(scene.active_variable, "au")
        self.assertGreaterEqual(len(scene.layers), 1)
        self.assertEqual(scene.layers[0].layer_type, "point_cloud")

    def test_scene_builder_applies_profile_and_clipping(self) -> None:
        builder = SceneBuilderService()
        scene = builder.build_scene(
            self._payload(),
            active_variable="au",
            active_domain="A",
            context_key="ctx",
            view_profile="Intervalos",
            z_focus_pct=50.0,
        )
        self.assertTrue(scene.clipping_state.enabled)
        self.assertEqual(scene.diagnostics["view_profile"], "Intervalos")

    def test_scene_state_json_roundtrip(self) -> None:
        builder = SceneBuilderService()
        scene = builder.build_scene(self._payload(), active_variable="au", active_domain="A", context_key="ctx")
        loaded = SceneState.from_json(scene.to_json())
        self.assertEqual(loaded.active_variable, "au")
        self.assertEqual(loaded.active_domain, "A")
        self.assertEqual(len(loaded.layers), len(scene.layers))


if __name__ == "__main__":
    unittest.main()
