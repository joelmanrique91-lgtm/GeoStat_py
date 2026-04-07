"""Regression guards for embedded 3D backend selection and external optional launch."""

from __future__ import annotations

import unittest
from pathlib import Path


class SpatialBackendSelectionTests(unittest.TestCase):
    def test_home_panel_prefers_embedded_renderer_for_3d(self) -> None:
        source = Path("app/ui/panels/home_panel.py").read_text(encoding="utf-8")
        self.assertIn("return self.spatial_3d_renderer, \"\"", source)
        self.assertIn("Embedded 3D remains primary", source)

    def test_external_viewer_is_explicit_secondary_action(self) -> None:
        source = Path("app/ui/panels/home_panel.py").read_text(encoding="utf-8")
        self.assertIn("Abrir viewer externo (opcional)", source)
        self.assertIn("_open_external_spatial_viewer", source)


if __name__ == "__main__":
    unittest.main()
