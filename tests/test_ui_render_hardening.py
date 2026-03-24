"""Regression checks for UI render hardening and geometry stability."""

from __future__ import annotations

import ast
from pathlib import Path
import unittest


class UIRenderHardeningTests(unittest.TestCase):
    def test_render_step_avoids_double_action_bar_rebuild(self) -> None:
        source = Path("app/ui/panels/home_panel.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        target: ast.FunctionDef | None = None
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name == "HomePanel":
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name == "_render_step":
                        target = item
                        break
        self.assertIsNotNone(target, "_render_step debe existir.")
        calls = [
            stmt
            for stmt in ast.walk(target)
            if isinstance(stmt, ast.Call) and isinstance(stmt.func, ast.Attribute) and stmt.func.attr == "_render_stage_action_bar"
        ]
        self.assertEqual(len(calls), 0, "_render_step no debe reconstruir action bar directamente.")

    def test_spatial2d_renderer_enforces_equal_aspect(self) -> None:
        source = Path("app/ui/renderers/mpl_spatial2d_renderer.py").read_text(encoding="utf-8")
        self.assertIn('set_aspect("equal"', source)
        self.assertIn("def _set_equal_xy", source)

    def test_dashboard_grid_uses_resize_debounce(self) -> None:
        source = Path("app/ui/panels/dashboard_grid.py").read_text(encoding="utf-8")
        self.assertIn('bind("<Configure>"', source)
        self.assertIn("draw_idle()", source)
        self.assertIn("after(80, self._resize_to_parent)", source)

    def test_variography_view_restores_busy_state_after_compute_callback(self) -> None:
        source = Path("app/ui/panels/stages/variography_stage_view.py").read_text(encoding="utf-8")
        self.assertIn("finally:", source)
        self.assertIn("self._set_compute_busy(False)", source)
        self.assertIn('state="disabled" if busy else "normal"', source)

    def test_variography_view_marshals_worker_result_back_to_ui_thread(self) -> None:
        source = Path("app/ui/panels/stages/variography_stage_view.py").read_text(encoding="utf-8")
        self.assertIn("host.after(0, lambda: self._on_compute_finished(response))", source)
        self.assertNotIn("except Exception:\n                    pass", source)

    def test_variography_view_has_contextual_fallback_panel(self) -> None:
        source = Path("app/ui/panels/stages/variography_stage_view.py").read_text(encoding="utf-8")
        self.assertIn("def _render_compute_failure_panel", source)
        self.assertIn("Variografía no renderizable", source)
        self.assertIn("Ejecutar variografía", source)
        self.assertIn("Direccional (pendiente backend)", source)
        self.assertIn('state="disabled"', source)


if __name__ == "__main__":
    unittest.main()
