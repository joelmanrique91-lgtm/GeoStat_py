"""UI semantics helper tests for workflow/readiness communication."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from app.ui.panels.home_panel import (
    _build_active_step_hint,
    _build_context_chip_texts,
    _build_visual_context_line,
    _build_workflow_stage_label,
    _should_expand_stage_actions,
)
from app.ui.panels.spatial_3d_view import is_3d_backend_available


class HomePanelSemanticsTests(unittest.TestCase):
    def test_workflow_stage_label_reflects_readiness_state(self) -> None:
        readiness = {
            "stages": {
                "data": {"ready": True, "warnings": []},
                "eda": {"ready": False, "warnings": []},
            }
        }
        label_data = _build_workflow_stage_label("Datos", "Datos", readiness)
        label_eda = _build_workflow_stage_label("EDA", "Datos", readiness)
        self.assertIn("✓", label_data)
        self.assertIn("!", label_eda)
        self.assertTrue(label_data.startswith("●"))
        self.assertTrue(label_eda.startswith("○"))

    def test_active_step_hint_uses_blocking_reason_mapping(self) -> None:
        readiness = {
            "stages": {
                "spatial": {
                    "ready": False,
                    "blocking_reasons": ["missing_spatial_columns"],
                    "warnings": [],
                }
            }
        }
        hint = _build_active_step_hint("Espacial", readiness)
        self.assertIn("Reconfigura columnas espaciales", hint)

    def test_active_step_hint_uses_warning_message_when_ready_with_warnings(self) -> None:
        readiness = {
            "stages": {
                "domains": {
                    "ready": True,
                    "blocking_reasons": [],
                    "warnings": ["active_domain_filter_empty_result"],
                }
            }
        }
        hint = _build_active_step_hint("Dominios", readiness)
        self.assertIn("Advertencia", hint)

    def test_context_chip_texts_prioritize_global_context_microcopy(self) -> None:
        snapshot = {
            "resolved_target_column": "target_capped",
            "active_domain_column": "domain_estimation",
            "active_domain_filter": "A",
        }
        readiness = {"stages": {"data": {"ready": True}, "eda": {"ready": False}}}
        texts = _build_context_chip_texts(snapshot, readiness, "demo.csv")
        self.assertEqual(texts["dataset"], "Dataset: demo.csv")
        self.assertIn("Target activo: target_capped", texts["target"])
        self.assertIn("Dominio/filtro: domain_estimation · A", texts["domain"])
        self.assertIn("Bloqueos: 1", texts["status"])

    def test_visual_context_line_includes_global_and_local_context(self) -> None:
        snapshot = {
            "resolved_target_column": "target_capped",
            "active_domain_column": "domain_estimation",
            "active_domain_filter": "A",
        }
        line = _build_visual_context_line(snapshot, local_override="dom")
        self.assertIn("Target global: target_capped", line)
        self.assertIn("Override local: dom", line)
        self.assertIn("Dominio/filtro: domain_estimation · A", line)

    def test_stage_actions_expand_for_data_step_when_dataset_missing(self) -> None:
        readiness = {
            "stages": {
                "data": {
                    "ready": False,
                    "blocking_reasons": ["missing_dataset"],
                }
            }
        }
        self.assertTrue(_should_expand_stage_actions("Datos", readiness))
        self.assertFalse(_should_expand_stage_actions("EDA", readiness))

    def test_3d_backend_availability_helper_success(self) -> None:
        available, reason = is_3d_backend_available()
        self.assertTrue(available)
        self.assertEqual(reason, "ok")

    def test_3d_backend_availability_helper_failure(self) -> None:
        import builtins

        original_import = builtins.__import__

        def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name.startswith("mpl_toolkits.mplot3d"):
                raise ImportError("blocked for test")
            return original_import(name, globals, locals, fromlist, level)

        with patch("builtins.__import__", side_effect=fake_import):
            available, reason = is_3d_backend_available()

        self.assertFalse(available)
        self.assertIn("Backend 3D no disponible", reason)


if __name__ == "__main__":
    unittest.main()
