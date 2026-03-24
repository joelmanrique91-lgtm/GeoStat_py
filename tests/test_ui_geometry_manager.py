"""Regression checks for Tk geometry manager structure in data step."""

from __future__ import annotations

import ast
from pathlib import Path
import unittest


class GeometryManagerRegressionTests(unittest.TestCase):
    def test_data_step_builds_local_grid_container(self) -> None:
        source = Path("app/ui/panels/home_panel.py").read_text(encoding="utf-8")
        tree = ast.parse(source)

        target_method: ast.FunctionDef | None = None
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name == "HomePanel":
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name == "_build_data_controls":
                        target_method = item
                        break
        self.assertIsNotNone(target_method, "_build_data_controls debe existir en HomePanel.")

        local_grid_assignments = []
        for stmt in target_method.body:
            if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
                if stmt.targets[0].id == "grid":
                    local_grid_assignments.append(stmt)
        self.assertEqual(len(local_grid_assignments), 1, "Se espera un contenedor local `grid` para los controles de datos.")

        grid_call = local_grid_assignments[0].value
        self.assertIsInstance(grid_call, ast.Call, "`grid` debe inicializarse con llamada a constructor.")
        self.assertIsInstance(grid_call.func, ast.Attribute)
        self.assertEqual(grid_call.func.attr, "CTkFrame")

        # Protege contra reintroducción de referencias legacy en el método.
        method_source = ast.get_source_segment(source, target_method) or ""
        self.assertNotIn("self.center_panel", method_source)

    def test_cutoff_controls_include_manual_enable_switch(self) -> None:
        source = Path("app/ui/panels/home_panel.py").read_text(encoding="utf-8")
        tree = ast.parse(source)

        target_method: ast.FunctionDef | None = None
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name == "HomePanel":
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name == "_build_cutoff_controls":
                        target_method = item
                        break
        self.assertIsNotNone(target_method, "_build_cutoff_controls debe existir en HomePanel.")
        method_source = ast.get_source_segment(source, target_method) or ""
        self.assertIn("cutoff_enabled_var", method_source)
        self.assertIn("Activar límites manuales", method_source)

    def test_methodological_guardrail_texts_present(self) -> None:
        source = Path("app/ui/panels/home_panel.py").read_text(encoding="utf-8")
        self.assertIn("no implica independencia espacial", source)
        self.assertIn("no inferencia de continuidad", source)
        self.assertIn("Screening exploratorio: no reemplaza decisión minera final", source)
        self.assertIn("Módulo temporalmente deshabilitado", source)


if __name__ == "__main__":
    unittest.main()
