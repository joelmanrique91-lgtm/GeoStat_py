"""Contract tests for typed operational state in GeostatService."""

from __future__ import annotations

import unittest
from pathlib import Path

from app.adapters.geostatspy_adapter import GeostatSpyAdapter
from app.models.operational_state import GeostatOperationalState
from app.services.geostat_service import GeostatService


class OperationalStateContractsTests(unittest.TestCase):
    def test_service_exposes_typed_operational_state(self) -> None:
        service = GeostatService(adapter=GeostatSpyAdapter())
        state = service.get_operational_state()
        self.assertIsInstance(state, GeostatOperationalState)
        self.assertEqual(state.analysis.dataset_name, "No cargado")
        self.assertFalse(state.readiness.stage("data").ready)

    def test_dict_compatibility_bridge_matches_typed_state(self) -> None:
        service = GeostatService(adapter=GeostatSpyAdapter())
        csv_path = Path("tests/fixtures/variography/variography_small_numeric.csv")
        self.assertTrue(service.load_csv(str(csv_path)).success)
        self.assertTrue(service.set_variable_config("x", "y", "z", "target").success)

        typed = service.get_operational_state()
        snapshot = service.get_analysis_context_snapshot()
        readiness = service.get_workflow_readiness()
        cutoff = service.get_cutoff_state()
        domain = service.get_domain_state()

        self.assertEqual(snapshot["resolved_target_column"], typed.analysis.resolved_target_column)
        self.assertEqual(bool(readiness["stages"]["eda"]["ready"]), typed.readiness.stage("eda").ready)
        self.assertEqual(cutoff["effective_target_column"], typed.cutoff.effective_target_column)
        self.assertEqual(domain["effective_target_column"], typed.domain.effective_target_column)

    def test_domains_stage_reflects_disabled_module_state(self) -> None:
        service = GeostatService(adapter=GeostatSpyAdapter())
        csv_path = Path("tests/fixtures/variography/variography_small_numeric.csv")
        self.assertTrue(service.load_csv(str(csv_path)).success)
        self.assertTrue(service.set_variable_config("x", "y", "z", "target").success)

        readiness = service.get_workflow_readiness_state()
        self.assertFalse(readiness.stage("domains").ready)
        self.assertIn("domains_module_disabled", readiness.stage("domains").blocking_reasons)

        domain_state = service.get_domain_state_typed()
        self.assertFalse(domain_state.domains_ready)


if __name__ == "__main__":
    unittest.main()
