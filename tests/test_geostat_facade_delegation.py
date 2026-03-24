"""Facade delegation checks for GeostatService specialized state service."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from app.adapters.geostatspy_adapter import GeostatSpyAdapter
from app.services.geostat_service import GeostatService


class GeostatFacadeDelegationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = GeostatService(adapter=GeostatSpyAdapter())

    def test_analysis_context_state_delegates_to_operational_state_service(self) -> None:
        with patch.object(
            self.service.operational_state_service,
            "build_analysis_context_state",
            wraps=self.service.operational_state_service.build_analysis_context_state,
        ) as build_mock:
            state = self.service.get_analysis_context_state()
        self.assertGreaterEqual(build_mock.call_count, 1)
        self.assertEqual(state.readiness, "blocked")

    def test_workflow_readiness_state_delegates_to_operational_state_service(self) -> None:
        with patch.object(
            self.service.operational_state_service,
            "build_workflow_readiness_state",
            wraps=self.service.operational_state_service.build_workflow_readiness_state,
        ) as build_mock:
            readiness = self.service.get_workflow_readiness_state()
        self.assertGreaterEqual(build_mock.call_count, 1)
        self.assertIn("data", readiness.stages)

    def test_operational_state_aggregate_delegates(self) -> None:
        with patch.object(
            self.service.operational_state_service,
            "build_operational_state",
            wraps=self.service.operational_state_service.build_operational_state,
        ) as build_mock:
            state = self.service.get_operational_state()
        self.assertGreaterEqual(build_mock.call_count, 1)
        self.assertEqual(state.analysis.current_step, "Datos")


if __name__ == "__main__":
    unittest.main()
