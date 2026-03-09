"""Tests for non-implemented module behavior."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from app.adapters.geostatspy_adapter import GeostatSpyAdapter
from app.services.activity_log_service import ActivityLogService
from app.services.geostat_service import GeostatService


class ModulePlaceholderTests(unittest.TestCase):
    def test_placeholder_click_registers_log_event(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            logger = ActivityLogService(logs_dir=Path(tmp_dir))
            service = GeostatService(adapter=GeostatSpyAdapter(), activity_log=logger)

            message = service.module_not_implemented("Kriging")
            self.assertIn("no implementado", message)

            entries = logger.session_log_path.read_text(encoding="utf-8").strip().splitlines()
            event = json.loads(entries[-1])
            self.assertEqual(event["event"], "placeholder_module_clicked")
            self.assertEqual(event["details"]["module"], "Kriging")


if __name__ == "__main__":
    unittest.main()
