from __future__ import annotations

import unittest

from app.adapters.geostatspy_adapter import GeostatSpyAdapter
from app.services.activity_log_service import ActivityLogService
from app.services.geostat_service import GeostatService
from app.services.workflow_coordinator_service import WorkflowCoordinatorService


class WorkflowCoordinatorServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = GeostatService(adapter=GeostatSpyAdapter(), activity_log=ActivityLogService())
        self.coordinator = WorkflowCoordinatorService(self.service)

    def test_change_step_same_step_is_noop(self) -> None:
        self.service.workflow_state.current_step = "Datos"
        result = self.coordinator.change_step("Datos")
        self.assertFalse(result.changed)
        self.assertEqual(result.current_step, "Datos")

    def test_change_step_updates_workflow_state(self) -> None:
        self.service.workflow_state.current_step = "Datos"
        result = self.coordinator.change_step("EDA")
        self.assertTrue(result.changed)
        self.assertEqual(result.current_step, "EDA")
        self.assertEqual(self.service.workflow_state.current_step, "EDA")


if __name__ == "__main__":
    unittest.main()
