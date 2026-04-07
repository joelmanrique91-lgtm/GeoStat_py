"""Behavioral contract tests for dedicated 3D renderer backend resolution."""

from __future__ import annotations

import builtins
import types
import unittest
from unittest.mock import patch

from app.ui.renderers.pyvista_spatial3d_renderer import PyVistaSpatial3DRenderer


class PyVistaRendererContractTests(unittest.TestCase):
    def test_is_available_reports_missing_backends(self) -> None:
        renderer = PyVistaSpatial3DRenderer()
        original_import = builtins.__import__

        def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name in {"pyvista", "vtk", "plotly"}:
                raise ImportError("missing dep")
            return original_import(name, globals, locals, fromlist, level)

        with patch("builtins.__import__", side_effect=fake_import):
            available, reason = renderer.is_available()

        self.assertFalse(available)
        self.assertIn("No hay backend 3D dedicado", reason)

    def test_is_available_prefers_pyvista(self) -> None:
        renderer = PyVistaSpatial3DRenderer()
        original_import = builtins.__import__

        def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name in {"pyvista", "vtk"}:
                return types.SimpleNamespace(__name__=name)
            return original_import(name, globals, locals, fromlist, level)

        with patch("builtins.__import__", side_effect=fake_import):
            available, reason = renderer.is_available()

        self.assertTrue(available)
        self.assertEqual(reason, "pyvista")

    def test_is_available_falls_back_to_plotly(self) -> None:
        renderer = PyVistaSpatial3DRenderer()
        original_import = builtins.__import__

        def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name in {"pyvista", "vtk"}:
                raise ImportError("missing pyvista")
            if name == "plotly":
                return types.SimpleNamespace(__name__=name)
            return original_import(name, globals, locals, fromlist, level)

        with patch("builtins.__import__", side_effect=fake_import):
            available, reason = renderer.is_available()

        self.assertTrue(available)
        self.assertEqual(reason, "plotly")


if __name__ == "__main__":
    unittest.main()
