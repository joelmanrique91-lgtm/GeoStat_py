"""Tests for workflow navigation and context state."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from app.adapters.geostatspy_adapter import GeostatSpyAdapter
from app.services.activity_log_service import ActivityLogService
from app.services.geostat_service import GeostatService


class WorkflowStateTests(unittest.TestCase):
    def test_change_step_updates_state_and_logs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            logger = ActivityLogService(logs_dir=Path(tmp_dir))
            service = GeostatService(adapter=GeostatSpyAdapter(), activity_log=logger)

            msg = service.set_workflow_step("Variografía")
            self.assertIn("Paso activo", msg)
            self.assertEqual(service.workflow_state.current_step, "Variografía")

            lines = logger.session_log_path.read_text(encoding="utf-8").strip().splitlines()
            events = [json.loads(line)["event"] for line in lines]
            self.assertIn("workflow_step_changed", events)
            self.assertIn("variografía_opened", events)


if __name__ == "__main__":
    unittest.main()
