"""Behavior tests for spatial viewer controller orchestration."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

try:
    import pandas as pd

    HAS_PANDAS = True
except ModuleNotFoundError:
    HAS_PANDAS = False

from app.adapters.geostatspy_adapter import GeostatSpyAdapter
from app.services.geostat_service import GeostatService
from app.ui.controllers.spatial_viewer_controller import SpatialViewerController


class _StubWidget:
    def grid(self, **_kwargs) -> None:
        return None


class _StubRenderer:
    def __init__(self, available: bool = True) -> None:
        self._available = available
        self.render_called = False

    def is_available(self):
        return (self._available, "missing" if not self._available else "ok")

    def create_widget(self, parent):
        _ = parent
        return _StubWidget()

    def render(self, widget, scene, color_display_label):
        _ = (widget, scene, color_display_label)
        self.render_called = True

    def show_unavailable(self, widget, reason):
        _ = (widget, reason)


@unittest.skipUnless(HAS_PANDAS, "pandas no disponible en este entorno")
class SpatialViewerControllerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = GeostatService(adapter=GeostatSpyAdapter())
        with tempfile.TemporaryDirectory() as tmp_dir:
            p = Path(tmp_dir) / "d.csv"
            p.write_text("x,y,z,target,hole\n1,2,3,10,DH1\n2,3,4,11,DH1\n3,4,5,12,DH2\n", encoding="utf-8")
            self.service.load_csv(str(p))
            self.service.set_variable_config("x", "y", "z", "target", hole_id_column="hole")
            self._df = self.service.current_dataset.dataframe.copy()
        self.service.current_dataset.dataframe = self._df

    def test_build_or_get_scene_uses_cache(self) -> None:
        controller = SpatialViewerController(service=self.service)
        scene1 = controller.build_or_get_scene(color_by="target")
        scene2 = controller.build_or_get_scene(color_by="target")
        self.assertEqual(scene1.context_key, scene2.context_key)
        self.assertEqual(controller.geometry_cache.size(), 1)

    def test_render_scene_with_unavailable_renderer_requests_fallback(self) -> None:
        controller = SpatialViewerController(service=self.service)
        result = controller.render_scene(parent=object(), renderer=_StubRenderer(available=False), color_by="target")
        self.assertFalse(result.success)
        self.assertTrue(result.fallback_to_2d)


if __name__ == "__main__":
    unittest.main()
