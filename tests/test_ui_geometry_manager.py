"""Regression checks for Tk geometry manager consistency in data step."""

from pathlib import Path
import unittest


class GeometryManagerRegressionTests(unittest.TestCase):
    def test_data_step_uses_grid_only_inside_subframe(self) -> None:
        source = Path("app/ui/panels/home_panel.py").read_text(encoding="utf-8")
        self.assertNotIn("CTkLabel(self.center_panel, text=label).grid", source)
        self.assertNotIn("CTkOptionMenu(self.center_panel", source)
        self.assertIn("config_grid = ctk.CTkFrame(self.center_panel", source)


if __name__ == "__main__":
    unittest.main()
