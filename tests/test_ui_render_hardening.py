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
        self.assertIn("def force_resize_under", source)
        self.assertIn("width = int(parent_width)", source)
        self.assertNotIn("max(widget.winfo_width(), parent_width)", source)
        self.assertIn("new_w = min(new_w, avail_w)", source)
        self.assertIn("new_h = min(new_h, avail_h)", source)

    def test_eda_view_uses_typed_cutoff_state_access(self) -> None:
        source = Path("app/ui/panels/home_panel.py").read_text(encoding="utf-8")
        self.assertNotIn("state[\"dynamic_enabled\"]", source)
        self.assertNotIn("state[\"dynamic_cutoff_value\"]", source)
        self.assertNotIn("state[\"enabled\"]", source)
        self.assertIn("def _notify_stage_requirement", source)
        self.assertIn("accion_restringida_por_etapa", source)

    def test_eda_view_shows_visible_fallback_and_logs_renderer_failures(self) -> None:
        source = Path("app/ui/panels/home_panel.py").read_text(encoding="utf-8")
        self.assertIn("No se pudo renderizar el panel EDA", source)
        self.assertIn("eda_render_failed", source)
        self.assertIn("Render EDA falló", source)
        self.assertIn("Estado render:", source)
        self.assertIn("Actualizar EDA", source)
        self.assertIn("aplica en la etapa", source)

    def test_eda_view_uses_responsive_host_weights_and_aspect_guards(self) -> None:
        source = Path("app/ui/panels/home_panel.py").read_text(encoding="utf-8")
        self.assertIn("plot_card.grid_rowconfigure(1, weight=4, minsize=72)", source)
        self.assertIn("main_row.grid_columnconfigure(0, weight=11)", source)
        self.assertIn("right_col.grid_rowconfigure(0, weight=13)", source)
        self.assertIn("max_aspect_ratio=2.25", source)
        self.assertIn("max_aspect_ratio=1.65", source)
        self.assertIn("DashboardGrid.force_resize_under(active_host)", source)
        self.assertIn("secondary_block.grid_rowconfigure(1, weight=1)", source)
        self.assertIn('detail_plots.grid(row=1, column=0, sticky="nsew"', source)

    def test_outlier_preview_uses_modern_boxplot_api_and_visible_fallback(self) -> None:
        source = Path("app/ui/panels/home_panel.py").read_text(encoding="utf-8")
        self.assertIn("tick_labels=[\"Base\", \"Cap\"]", source)
        self.assertIn("cutoff_preview_render_failed", source)
        self.assertIn("No se pudo renderizar el panel de outliers", source)
        self.assertIn("add_reference_line,", source)

    def test_eda_renderer_adjusts_boxplot_bottom_margin_for_long_labels(self) -> None:
        source = Path("app/ui/renderers/mpl_eda_renderer.py").read_text(encoding="utf-8")
        self.assertIn("max_label_len", source)
        self.assertIn("bottom_margin = min(bottom_margin, 0.42)", source)
        self.assertIn("labelrotation=rotation", source)

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

    def test_variography_controls_panel_is_scrollable_and_compact(self) -> None:
        source = Path("app/ui/panels/stages/variography_stage_view.py").read_text(encoding="utf-8")
        self.assertIn("CTkScrollableFrame(", source)
        self.assertIn("height=30", source)
        self.assertIn("width=124", source)

    def test_spatial_3d_view_supports_mouse_wheel_zoom_and_camera_persistence(self) -> None:
        source = Path("app/ui/panels/spatial_3d_view.py").read_text(encoding="utf-8")
        self.assertIn('mpl_connect("scroll_event", self._on_mouse_wheel_zoom)', source)
        self.assertIn("def _on_mouse_wheel_zoom", source)
        self.assertIn("self._last_elev", source)
        self.assertIn("self._last_azim", source)
        self.assertIn("def _sync_figure_to_host", source)
        self.assertIn("self.plot_host.bind(\"<Configure>\"", source)
        self.assertIn("def destroy(self)", source)


if __name__ == "__main__":
    unittest.main()
