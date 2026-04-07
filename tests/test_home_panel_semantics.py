"""UI semantics helper tests for workflow/readiness communication."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from app.models.operational_state import AnalysisContextState, CutoffState, DomainState, GeostatOperationalState, StageReadiness, VariableSelectionState, WorkflowReadinessState
from app.ui.panels.home_panel import (
    _build_active_step_hint,
    _build_context_chip_texts,
    _build_visual_context_line,
    _build_workflow_stage_label,
    _should_expand_stage_actions,
)
from app.ui.panels.spatial_3d_view import is_3d_backend_available


class HomePanelSemanticsTests(unittest.TestCase):
    def _build_state(self, stages: dict[str, StageReadiness]) -> GeostatOperationalState:
        analysis = AnalysisContextState(
            dataset_name="demo.csv",
            base_target_column="target",
            effective_target_column="target",
            resolved_target_column="target",
            resolved_target_type="numeric",
            active_domain_column="domain_estimation",
            active_domain_filter="A",
            current_step="Datos",
            readiness="ready",
            blocking_reason="",
        )
        readiness = WorkflowReadinessState(
            current_step="Datos",
            analysis_context=analysis,
            has_dataset=True,
            has_variable_config=True,
            stages=stages,
        )
        cutoff = CutoffState(False, "", "", (), (), "", "target", False, "", "", "percentile", 95.0, 0.0, "", "")
        domain = DomainState(effective_target_column="target")
        selection = VariableSelectionState(target_column="target")
        return GeostatOperationalState(analysis=analysis, readiness=readiness, cutoff=cutoff, domain=domain, selection=selection)

    def test_workflow_stage_label_reflects_readiness_state(self) -> None:
        readiness = WorkflowReadinessState(
            current_step="Datos",
            analysis_context=self._build_state({}).analysis,
            has_dataset=True,
            has_variable_config=True,
            stages={
                "data": StageReadiness(ready=True),
                "eda": StageReadiness(ready=False),
                "cutoffs": StageReadiness(ready=False),
                "spatial": StageReadiness(ready=False),
                "domains": StageReadiness(ready=False),
                "variography": StageReadiness(ready=False),
            },
        )
        label_data = _build_workflow_stage_label("Datos", "Datos", readiness)
        label_eda = _build_workflow_stage_label("EDA", "Datos", readiness)
        self.assertIn("✓", label_data)
        self.assertIn("!", label_eda)
        self.assertTrue(label_data.startswith("●"))
        self.assertTrue(label_eda.startswith("○"))

    def test_active_step_hint_uses_blocking_reason_mapping(self) -> None:
        state = self._build_state(
            {
                "data": StageReadiness(True),
                "eda": StageReadiness(True),
                "cutoffs": StageReadiness(True),
                "spatial": StageReadiness(False, ("missing_spatial_columns",), (), "Reconfigura columnas espaciales X/Y/Z."),
                "domains": StageReadiness(False),
                "variography": StageReadiness(False),
            }
        )
        hint = _build_active_step_hint("Espacial", state)
        self.assertIn("Reconfigura columnas espaciales", hint)

    def test_active_step_hint_uses_warning_message_when_ready_with_warnings(self) -> None:
        state = self._build_state(
            {
                "data": StageReadiness(True),
                "eda": StageReadiness(True),
                "cutoffs": StageReadiness(True),
                "spatial": StageReadiness(True),
                "domains": StageReadiness(True, (), ("active_domain_filter_empty_result",), "Advertencia: hay filtros activos que reducen resultados."),
                "variography": StageReadiness(True),
            }
        )
        hint = _build_active_step_hint("Dominios", state)
        self.assertIn("Advertencia", hint)

    def test_workflow_stage_label_prioritizes_warning_marker_when_ready_with_warning(self) -> None:
        readiness = WorkflowReadinessState(
            current_step="Datos",
            analysis_context=self._build_state({}).analysis,
            has_dataset=True,
            has_variable_config=True,
            stages={
                "data": StageReadiness(ready=True),
                "eda": StageReadiness(ready=True),
                "cutoffs": StageReadiness(ready=True),
                "spatial": StageReadiness(ready=True),
                "domains": StageReadiness(ready=True, warnings=("low_data_after_domain_filter",)),
                "variography": StageReadiness(ready=True),
            },
        )
        label_domains = _build_workflow_stage_label("Dominios", "Datos", readiness)
        self.assertIn("⚠ ALERTA", label_domains)
        self.assertNotIn("✓ LISTO", label_domains)

    def test_context_chip_texts_prioritize_global_context_microcopy(self) -> None:
        state = self._build_state(
            {
                "data": StageReadiness(True),
                "eda": StageReadiness(False),
                "cutoffs": StageReadiness(True),
                "spatial": StageReadiness(True),
                "domains": StageReadiness(True),
                "variography": StageReadiness(True),
            }
        )
        texts = _build_context_chip_texts(state)
        self.assertEqual(texts["dataset"], "Dataset: demo.csv")
        self.assertIn("Target activo: target", texts["target"])
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
        readiness = WorkflowReadinessState(
            current_step="Datos",
            analysis_context=self._build_state({}).analysis,
            has_dataset=False,
            has_variable_config=False,
            stages={
                "data": StageReadiness(False, ("missing_dataset",)),
                "eda": StageReadiness(False),
                "cutoffs": StageReadiness(False),
                "spatial": StageReadiness(False),
                "domains": StageReadiness(False),
                "variography": StageReadiness(False),
            },
        )
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

    def test_home_panel_has_explicit_feedback_for_same_step_navigation(self) -> None:
        from pathlib import Path

        source = Path("app/ui/panels/home_panel.py").read_text(encoding="utf-8")
        self.assertIn("Ya estás en la etapa", source)
        self.assertIn("same_step_ignored", source)


if __name__ == "__main__":
    unittest.main()
