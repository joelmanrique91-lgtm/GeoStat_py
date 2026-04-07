from __future__ import annotations

import unittest
from pathlib import Path


class HomePanelDecouplingTests(unittest.TestCase):
    def test_home_panel_uses_workflow_actions_controller_for_critical_mutations(self) -> None:
        content = Path("app/ui/panels/home_panel.py").read_text(encoding="utf-8")
        self.assertIn("self.workflow_actions_controller.apply_variable_config", content)
        self.assertIn("self.workflow_actions_controller.apply_domain_filter", content)
        self.assertIn("self.workflow_actions_controller.confirm_domain_assignment", content)
        self.assertIn("self.workflow_actions_controller.apply_domains", content)
        self.assertIn("self.workflow_actions_controller.toggle_variography_bypass", content)
        self.assertIn("self.workflow_actions_controller.apply_manual_cutoff", content)
        self.assertIn("self.workflow_actions_controller.apply_dynamic_cutoff", content)
        self.assertIn("self.workflow_actions_controller.apply_support_composite", content)
        self.assertIn("self.workflow_actions_controller.build_cutoff_preview_payload", content)
        self.assertNotIn("self.service.set_variable_config(", content)
        self.assertNotIn("self.service.apply_domain_definition(", content)
        self.assertNotIn("self.service.confirm_domain_assignment(", content)
        self.assertNotIn("self.service.apply_cutoffs(", content)
        self.assertNotIn("self.service.apply_dynamic_cutoff(", content)
        self.assertNotIn("self.service.apply_basic_compositing(", content)
        self.assertNotIn("self.service.prepare_dynamic_cutoff_preview(", content)


if __name__ == "__main__":
    unittest.main()
