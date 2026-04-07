from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from app.adapters.geostatspy_adapter import GeostatSpyAdapter
from app.services.activity_log_service import ActivityLogService
from app.services.geostat_service import GeostatService


class VariographyTraceabilityTests(unittest.TestCase):
    def test_variography_log_contains_backend_and_audit_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            activity = ActivityLogService(logs_dir=Path(tmp_dir))
            service = GeostatService(adapter=GeostatSpyAdapter(), activity_log=activity)
            fixture = Path("tests/fixtures/variography/variography_small_numeric.csv")
            self.assertTrue(service.load_csv(str(fixture)).success)
            self.assertTrue(service.set_variable_config("x", "y", "z", "target", domain_column="domain").success)
            self.assertTrue(service.apply_basic_compositing(composite_length=2.0, target_column="target").success)
            self.assertTrue(service.set_variography_domain_bypass(enabled=True, reason="audit-trace").success)
            _response = service.compute_experimental_variography(
                {"lag_distance": 10.0, "n_lags": 8, "lag_tolerance": 5.0, "max_distance": 120.0}
            )

            lines = activity.session_log_path.read_text(encoding="utf-8").strip().splitlines()
            events = [json.loads(line) for line in lines if line.strip()]
            compute_events = [item for item in events if item.get("event") == "variography_compute"]
            self.assertTrue(compute_events)
            details = compute_events[-1]["details"]
            self.assertIn("backend_used", details)
            self.assertIn("warning_codes", details)
            self.assertIn("blocker_codes", details)
            self.assertIn("domain_bypass_reason", details)
            self.assertIn("support_mode", details)


if __name__ == "__main__":
    unittest.main()
