"""Tests for JSONL activity logging and export."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from app.services.activity_log_service import ActivityLogService


class ActivityLogTests(unittest.TestCase):
    def test_log_event_written_as_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            logger = ActivityLogService(logs_dir=Path(tmp_dir))
            logger.log("app_started", "success", "Aplicación iniciada.", {"version": "test"})

            lines = logger.session_log_path.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 1)
            event = json.loads(lines[0])
            self.assertEqual(event["event"], "app_started")
            self.assertEqual(event["status"], "success")
            self.assertEqual(event["details"]["version"], "test")

    def test_export_log_creates_jsonl_copy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            logger = ActivityLogService(logs_dir=Path(tmp_dir))
            logger.log("csv_load_started", "info", "Inicio", {"file": "a.csv"})
            export_to = Path(tmp_dir) / "exports" / "session_export"
            exported = logger.export_log(str(export_to))

            self.assertTrue(exported.exists())
            self.assertEqual(exported.suffix, ".jsonl")
            self.assertIn("csv_load_started", exported.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
