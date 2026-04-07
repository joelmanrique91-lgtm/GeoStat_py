from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.adapters.geostatspy_adapter import GeostatSpyAdapter
from app.services.activity_log_service import ActivityLogService
from app.services.geostat_service import GeostatService
from app.ui.controllers.workflow_actions_controller import WorkflowActionsController


class WorkflowActionsRegressionTests(unittest.TestCase):
    def test_domain_config_bypass_actions_still_work(self) -> None:
        service = GeostatService(adapter=GeostatSpyAdapter(), activity_log=ActivityLogService())
        controller = WorkflowActionsController(service)
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "workflow.csv"
            csv_path.write_text("x,y,z,target,dom\n0,0,0,1,a\n1,1,1,2,a\n2,2,2,3,b\n", encoding="utf-8")
            self.assertTrue(service.load_csv(str(csv_path)).success)
            cfg = controller.apply_variable_config(
                x_column="x",
                y_column="y",
                z_column="z",
                target_column="target",
                hole_id_column=None,
                selected_domain="dom",
            )
            self.assertTrue(cfg.success)
            domain_result = service.configure_domains(["dom"], ["dom"], min_samples=1, include_missing=False)
            self.assertTrue(domain_result.success)
            bypass = controller.toggle_variography_bypass(enabled=True, reason="regression")
            self.assertTrue(bypass.success)
            self.assertTrue(service.workflow_state.allow_variography_without_domain)
            self.assertEqual(service.workflow_state.variography_domain_bypass_reason, "regression")


if __name__ == "__main__":
    unittest.main()
