"""Regression checks for window geometry normalization and DPI bootstrap."""

from __future__ import annotations

from pathlib import Path
import unittest

from app.ui.window_geometry import Rect, clamp_to_visible_area, parse_tk_geometry, to_tk_geometry


class WindowGeometryPolicyTests(unittest.TestCase):
    def test_parse_and_serialize_tk_geometry(self) -> None:
        parsed = parse_tk_geometry("1360x860-1920+40")
        self.assertEqual(parsed, Rect(x=-1920, y=40, width=1360, height=860))
        self.assertEqual(to_tk_geometry(parsed), "1360x860-1920+40")

    def test_clamp_keeps_window_fully_visible(self) -> None:
        visible = Rect(x=-1920, y=0, width=1920, height=1080)
        rect = Rect(x=-2500, y=-120, width=1800, height=1000)
        clamped = clamp_to_visible_area(rect, visible=visible, min_width=900, min_height=620)
        self.assertGreaterEqual(clamped.x, visible.x)
        self.assertGreaterEqual(clamped.y, visible.y)
        self.assertLessEqual(clamped.x + clamped.width, visible.x + visible.width)
        self.assertLessEqual(clamped.y + clamped.height, visible.y + visible.height)

    def test_clamp_degrades_gracefully_when_visible_area_is_small(self) -> None:
        visible = Rect(x=0, y=0, width=960, height=540)
        rect = Rect(x=10, y=10, width=1360, height=860)
        clamped = clamp_to_visible_area(rect, visible=visible, min_width=1180, min_height=760)
        self.assertEqual(clamped.width, 960)
        self.assertEqual(clamped.height, 540)
        self.assertEqual(clamped.x, 0)
        self.assertEqual(clamped.y, 0)

    def test_main_bootstrap_calls_dpi_before_window_creation(self) -> None:
        source = Path("app/main.py").read_text(encoding="utf-8")
        main_block_start = source.index("def main() -> None:")
        dpi_call = source.index("_configure_windows_dpi_awareness()", main_block_start)
        main_window_call = source.index("app = MainWindow(service=service)", main_block_start)
        self.assertLess(dpi_call, main_window_call)


if __name__ == "__main__":
    unittest.main()
