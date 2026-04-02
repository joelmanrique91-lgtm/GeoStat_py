"""Behavioral contract tests for PyVistaSpatial3DRenderer availability states."""

from __future__ import annotations

import builtins
import os
import types
import unittest
from unittest.mock import patch

from app.ui.renderers.pyvista_spatial3d_renderer import PyVistaSpatial3DRenderer


class PyVistaRendererContractTests(unittest.TestCase):
    def test_is_available_reports_missing_backend(self) -> None:
        renderer = PyVistaSpatial3DRenderer()
        original_import = builtins.__import__

        def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name in {"pyvista", "vtk"}:
                raise ImportError("missing dep")
            return original_import(name, globals, locals, fromlist, level)

        with patch("builtins.__import__", side_effect=fake_import):
            available, reason = renderer.is_available()

        self.assertFalse(available)
        self.assertIn("PyVista no disponible", reason)

    def test_is_available_reports_policy_disabled_when_backend_exists(self) -> None:
        renderer = PyVistaSpatial3DRenderer()
        original_import = builtins.__import__

        def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name in {"pyvista", "vtk"}:
                return types.SimpleNamespace(__name__=name)
            return original_import(name, globals, locals, fromlist, level)

        with patch.dict(os.environ, {"GEOSTAT_ENABLE_PYVISTA_3D": "0"}, clear=False), patch(
            "builtins.__import__", side_effect=fake_import
        ):
            available, reason = renderer.is_available()

        self.assertFalse(available)
        self.assertIn("deshabilitado por política", reason)

    def test_is_available_can_be_enabled_with_feature_flag_when_deps_present(self) -> None:
        renderer = PyVistaSpatial3DRenderer()
        original_import = builtins.__import__

        def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name in {"pyvista", "vtk"}:
                return types.SimpleNamespace(__name__=name)
            return original_import(name, globals, locals, fromlist, level)

        with patch.dict(os.environ, {"GEOSTAT_ENABLE_PYVISTA_3D": "1"}, clear=False), patch(
            "builtins.__import__", side_effect=fake_import
        ):
            available, reason = renderer.is_available()

        self.assertTrue(available)
        self.assertEqual(reason, "ok")


if __name__ == "__main__":
    unittest.main()
