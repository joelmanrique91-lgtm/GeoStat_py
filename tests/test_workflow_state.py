"""Tests for workflow navigation and stage-specific events."""

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

            msg = service.set_workflow_step("Espacial")
            self.assertIn("Paso activo", msg)
            self.assertEqual(service.workflow_state.current_step, "Espacial")

            lines = logger.session_log_path.read_text(encoding="utf-8").strip().splitlines()
            events = [json.loads(line)["event"] for line in lines]
            self.assertIn("workflow_step_changed", events)
            self.assertIn("workflow_step_spatial_opened", events)

    def test_workflow_readiness_contract_without_dataset(self) -> None:
        service = GeostatService(adapter=GeostatSpyAdapter())
        readiness = service.get_workflow_readiness()

        self.assertEqual(set(readiness.keys()), {"current_step", "analysis_context", "base_state", "stages"})
        self.assertEqual(readiness["current_step"], "Datos")
        self.assertEqual(
            set(readiness["base_state"].keys()),
            {
                "has_dataset",
                "has_variable_config",
                "resolved_target_column",
                "resolved_target_type",
                "active_domain_column",
                "active_domain_filter",
            },
        )
        self.assertIn("eda", readiness["stages"])
        self.assertIn("spatial", readiness["stages"])
        self.assertIn("domains", readiness["stages"])
        self.assertIn("variography", readiness["stages"])
        self.assertFalse(readiness["stages"]["eda"]["ready"])
        self.assertIn("missing_dataset", readiness["stages"]["eda"]["blocking_reasons"])

    def test_workflow_readiness_consistent_with_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            service = GeostatService(adapter=GeostatSpyAdapter())
            csv_path = Path(tmp_dir) / "workflow_snapshot.csv"
            csv_path.write_text("x,y,z,target\n0,0,0,1\n1,1,1,2\n", encoding="utf-8")
            self.assertTrue(service.load_csv(str(csv_path)).success)
            self.assertTrue(service.set_variable_config("x", "y", "z", "target").success)
            snapshot = service.get_analysis_context_snapshot()
            readiness = service.get_workflow_readiness()

            self.assertEqual(readiness["base_state"]["resolved_target_column"], snapshot["resolved_target_column"])
            self.assertEqual(readiness["base_state"]["resolved_target_type"], snapshot["resolved_target_type"])
            self.assertEqual(readiness["base_state"]["active_domain_column"], snapshot["active_domain_column"])
            self.assertEqual(readiness["base_state"]["active_domain_filter"], snapshot["active_domain_filter"])

    def test_workflow_readiness_spatial_blocked_when_spatial_columns_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            service = GeostatService(adapter=GeostatSpyAdapter())
            csv_path = Path(tmp_dir) / "workflow_spatial_missing.csv"
            csv_path.write_text("x,y,z,target\n0,0,0,1\n1,1,1,2\n", encoding="utf-8")
            self.assertTrue(service.load_csv(str(csv_path)).success)
            self.assertTrue(service.set_variable_config("x", "y", "z", "target").success)
            service.current_dataset.dataframe.drop(columns=["x"], inplace=True)

            readiness = service.get_workflow_readiness()
            self.assertFalse(readiness["stages"]["spatial"]["ready"])
            self.assertIn("missing_spatial_columns", readiness["stages"]["spatial"]["blocking_reasons"])

    def test_workflow_readiness_domains_stage_is_blocked_without_support_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            service = GeostatService(adapter=GeostatSpyAdapter())
            csv_path = Path(tmp_dir) / "workflow_domains_missing.csv"
            csv_path.write_text("x,y,z,target,dom\n0,0,0,1,a\n1,1,1,2,b\n", encoding="utf-8")
            self.assertTrue(service.load_csv(str(csv_path)).success)
            self.assertTrue(service.set_variable_config("x", "y", "z", "target", domain_column="dom").success)

            readiness = service.get_workflow_readiness()
            self.assertFalse(readiness["stages"]["domains"]["ready"])
            self.assertIn("missing_support_confirmation", readiness["stages"]["domains"]["blocking_reasons"])

    def test_workflow_readiness_variography_blocked_without_domain_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            service = GeostatService(adapter=GeostatSpyAdapter())
            csv_path = Path(tmp_dir) / "workflow_ready.csv"
            csv_path.write_text("x,y,z,target,dom\n0,0,0,1,a\n1,1,1,2,a\n2,2,2,4,b\n", encoding="utf-8")
            self.assertTrue(service.load_csv(str(csv_path)).success)
            self.assertTrue(service.set_variable_config("x", "y", "z", "target", domain_column="dom").success)
            self.assertFalse(service.apply_domain_definition({"variable_base": "dom", "domains": {"A": ["a"], "B": ["b"]}}).success)
            readiness = service.get_workflow_readiness()
            self.assertTrue(readiness["stages"]["data"]["ready"])
            self.assertTrue(readiness["stages"]["eda"]["ready"])
            self.assertTrue(readiness["stages"]["cutoffs"]["ready"])
            self.assertTrue(readiness["stages"]["spatial"]["ready"])
            self.assertFalse(readiness["stages"]["domains"]["ready"])
            self.assertFalse(readiness["stages"]["variography"]["ready"])
            self.assertIn("missing_domain_confirmation", readiness["stages"]["variography"]["blocking_reasons"])

    def test_workflow_readiness_exposes_current_step(self) -> None:
        service = GeostatService(adapter=GeostatSpyAdapter())
        service.set_workflow_step("Dominios")
        readiness = service.get_workflow_readiness()
        self.assertEqual(readiness["current_step"], "Dominios")


if __name__ == "__main__":
    unittest.main()
