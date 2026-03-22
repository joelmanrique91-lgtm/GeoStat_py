"""Smoke checks for shared UI theme tokens used by HomePanel."""

from __future__ import annotations

import re
import unittest

from app.ui import theme


HEX_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


class ThemeTokenTests(unittest.TestCase):
    def test_shared_visual_tokens_are_valid_hex_colors(self) -> None:
        tokens = [
            theme.CHIP_BG,
            theme.BTN_SECONDARY_BG,
            theme.BTN_SECONDARY_HOVER,
            theme.BTN_PRIMARY_HOVER,
            theme.KPI_PRIMARY_BG,
            theme.WF_IDLE,
            theme.WF_ACTIVE,
            theme.WF_READY,
            theme.WF_BLOCKED,
            theme.WF_WARNING,
        ]
        for token in tokens:
            self.assertRegex(token, HEX_COLOR_RE)

    def test_divider_soft_reuses_border_token(self) -> None:
        self.assertEqual(theme.DIVIDER_SOFT, theme.BORDER_SOFT)


if __name__ == "__main__":
    unittest.main()
