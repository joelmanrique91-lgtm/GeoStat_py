"""Tests for repository update, workflow, autodetection and variable selection logic."""

from __future__ import annotations

import tempfile
import unittest
import os

try:
    import pandas  # noqa: F401

    HAS_PANDAS = True
except ModuleNotFoundError:
    HAS_PANDAS = False
from pathlib import Path
from unittest.mock import patch

from app.adapters.geostatspy_adapter import GeostatSpyAdapter
from app.services.geostat_service import GeostatService


@unittest.skipUnless(HAS_PANDAS, "pandas no disponible en este entorno")
class ServiceFeatureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = GeostatService(adapter=GeostatSpyAdapter())

    def _load_sample_dataset(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "sample.csv"
            csv_path.write_text("Easting,Northing,RL,Au,HoleID,Lithology\n1,2,3,10,DH01,A\n3,4,5,20,DH02,B\n", encoding="utf-8")
            result = self.service.load_csv(str(csv_path))
            self.assertTrue(result.success)

    def test_eda_summary_contains_expected_sections(self) -> None:
        self._load_sample_dataset()
        summary = self.service.build_eda_summary()
        self.assertIn("MÓDULO EDA", summary)
        self.assertIn("Resumen | Univariado", summary)

    def test_autodetect_columns(self) -> None:
        self._load_sample_dataset()
        detected = self.service.get_autodetected_columns()
        self.assertEqual(detected["x"], "Easting")
        self.assertEqual(detected["y"], "Northing")
        self.assertEqual(detected["z"], "RL")
        self.assertEqual(detected["hole_id"], "HoleID")
        self.assertEqual(detected["domain"], "Lithology")

    def test_set_variable_config_success(self) -> None:
        self._load_sample_dataset()
        result = self.service.set_variable_config("Easting", "Northing", "RL", "Au", "HoleID", "Lithology")

        self.assertTrue(result.success)
        self.assertIn("Configuración de variables guardada", result.message)
        self.assertIsNotNone(self.service.variable_config)
        self.assertEqual(self.service.workflow_state.active_support, "Muestra original")

    def test_set_variable_config_rejects_duplicate_xyz_columns(self) -> None:
        self._load_sample_dataset()
        result = self.service.set_variable_config("Easting", "Easting", "RL", "Au", "HoleID", "Lithology")
        self.assertFalse(result.success)
        self.assertIn("diferentes", result.message.lower())

    def test_set_variable_config_rejects_non_numeric_xyz_columns(self) -> None:
        self._load_sample_dataset()
        result = self.service.set_variable_config("Lithology", "Northing", "RL", "Au", "HoleID", "Lithology")
        self.assertFalse(result.success)
        self.assertIn("numéricas", result.message.lower())

    @patch("app.services.geostat_service.subprocess.run")
    def test_update_repository_success_when_enabled(self, mock_run) -> None:
        mock_run.side_effect = [
            type("Result", (), {"returncode": 0, "stdout": "Already up to date.", "stderr": ""})(),
            type("Result", (), {"returncode": 0, "stdout": "", "stderr": ""})(),
        ]
        with patch.dict(os.environ, {"GEOSTAT_ENABLE_RUNTIME_GIT_UPDATE": "1"}):
            result = self.service.update_repository()

        self.assertTrue(result.success)
        self.assertIn("actualizado", result.message.lower())
        self.assertFalse(result.restart_recommended)

    @patch("app.services.geostat_service.subprocess.run")
    def test_update_repository_fails_when_submodule_update_fails(self, mock_run) -> None:
        mock_run.side_effect = [
            type("Result", (), {"returncode": 0, "stdout": "Already up to date.", "stderr": ""})(),
            type("Result", (), {"returncode": 1, "stdout": "", "stderr": "submodule boom"})(),
        ]
        with patch.dict(os.environ, {"GEOSTAT_ENABLE_RUNTIME_GIT_UPDATE": "1"}):
            result = self.service.update_repository()

        self.assertFalse(result.success)
        self.assertIn("submódulos", result.message.lower())
        self.assertIn("submodule boom", result.details)

    def test_update_repository_blocked_by_default(self) -> None:
        result = self.service.update_repository()
        self.assertFalse(result.success)
        self.assertIn("deshabilitada", result.message.lower())

    def test_build_eda_summary_uses_effective_target_statistics_when_requested(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "capping_case.csv"
            csv_path.write_text("x,y,z,target\n0,0,0,10\n1,1,1,100\n", encoding="utf-8")
            result = self.service.load_csv(str(csv_path))
            self.assertTrue(result.success)
            cfg = self.service.set_variable_config("x", "y", "z", "target")
            self.assertTrue(cfg.success)

            capping = self.service.apply_dynamic_cutoff(
                enabled=True,
                target_column="target",
                mode="percentile",
                slider_percent=50.0,
                output_column="target_capped",
                keep_category_column=False,
            )
            self.assertTrue(capping.success)

            summary = self.service.build_eda_summary(use_effective_target=True)
            self.assertIn("Target target_capped", summary)

            expected_mean = float(self.service.current_dataset.dataframe["target_capped"].dropna().astype(float).mean())
            self.assertIn(f"mean={expected_mean:.4g}", summary)

    def test_prepare_univariate_returns_expected_contract(self) -> None:
        self._load_sample_dataset()
        self.service.set_variable_config("Easting", "Northing", "RL", "Au", "HoleID", "Lithology")
        payload = self.service.prepare_univariate_data()
        self.assertIsInstance(payload, dict)
        self.assertIn("target_values", payload)
        self.assertIn("availability", payload)
        self.assertIn("diagnostics", payload)
        self.assertTrue(payload["availability"]["histogram"]["available"])

    def test_prepare_univariate_uses_snapshot_resolution_for_effective_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "univariate_snapshot_effective.csv"
            csv_path.write_text("x,y,z,target\n0,0,0,1\n1,1,1,100\n2,2,2,3\n", encoding="utf-8")
            self.assertTrue(self.service.load_csv(str(csv_path)).success)
            self.assertTrue(self.service.set_variable_config("x", "y", "z", "target").success)
            self.assertTrue(
                self.service.apply_dynamic_cutoff(
                    enabled=True,
                    target_column="target",
                    mode="percentile",
                    slider_percent=50.0,
                    output_column="target_capped",
                    keep_category_column=False,
                ).success
            )
            expected = self.service.get_analysis_context_snapshot()["resolved_target_column"]

            with patch.object(self.service, "get_analysis_context_snapshot", wraps=self.service.get_analysis_context_snapshot) as snapshot_mock:
                payload = self.service.prepare_univariate_data(use_effective_target=True)

            self.assertGreaterEqual(snapshot_mock.call_count, 1)
            self.assertEqual(payload["diagnostics"]["target"], expected)

    def test_prepare_univariate_fails_without_dataset_or_variable_config(self) -> None:
        with self.assertRaisesRegex(ValueError, "No hay dataset/configuración suficiente para EDA."):
            self.service.prepare_univariate_data()

        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "univariate_no_config.csv"
            csv_path.write_text("x,y,z,target\n0,0,0,1\n", encoding="utf-8")
            self.assertTrue(self.service.load_csv(str(csv_path)).success)
            with self.assertRaisesRegex(ValueError, "No hay dataset/configuración suficiente para EDA."):
                self.service.prepare_univariate_data()

    def test_prepare_univariate_fails_when_resolved_target_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "univariate_missing_resolved.csv"
            csv_path.write_text("x,y,z,target\n0,0,0,1\n1,1,1,2\n", encoding="utf-8")
            self.assertTrue(self.service.load_csv(str(csv_path)).success)
            self.assertTrue(self.service.set_variable_config("x", "y", "z", "target").success)
            self.assertTrue(
                self.service.apply_dynamic_cutoff(
                    enabled=True,
                    target_column="target",
                    mode="percentile",
                    slider_percent=50.0,
                    output_column="target_capped_missing",
                    keep_category_column=False,
                ).success
            )
            self.service.current_dataset.dataframe.drop(columns=["target_capped_missing"], inplace=True)

            snapshot = self.service.get_analysis_context_snapshot()
            self.assertEqual(snapshot["blocking_reason"], "missing_resolved_target_column")
            with self.assertRaisesRegex(ValueError, "Target no válido para EDA univariado"):
                self.service.prepare_univariate_data(use_effective_target=True)

    def test_prepare_univariate_blocks_non_numeric_resolved_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "univariate_non_numeric_resolved.csv"
            csv_path.write_text("x,y,z,target\n0,0,0,1\n1,1,1,3\n2,2,2,5\n", encoding="utf-8")
            self.assertTrue(self.service.load_csv(str(csv_path)).success)
            self.assertTrue(self.service.set_variable_config("x", "y", "z", "target").success)
            self.assertTrue(
                self.service.apply_cutoffs(
                    enabled=True,
                    target_column="target",
                    limits_text="2,4",
                    output_column="target_cutoff_manual",
                ).success
            )

            snapshot = self.service.get_analysis_context_snapshot()
            self.assertEqual(snapshot["resolved_target_type"], "categorical")
            with self.assertRaisesRegex(ValueError, "Target no numérico para EDA univariado"):
                self.service.prepare_univariate_data(use_effective_target=True)

    def test_prepare_univariate_base_target_regression_still_ok(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "univariate_base_regression.csv"
            csv_path.write_text("x,y,z,target\n0,0,0,1\n1,1,1,2\n2,2,2,3\n", encoding="utf-8")
            self.assertTrue(self.service.load_csv(str(csv_path)).success)
            self.assertTrue(self.service.set_variable_config("x", "y", "z", "target").success)

            payload = self.service.prepare_univariate_data(use_effective_target=False)
            self.assertEqual(payload["diagnostics"]["target"], "target")
            self.assertEqual(payload["diagnostics"]["target_valid_count"], 3)

    def test_prepare_univariate_effective_dynamic_target_regression_still_ok(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "univariate_effective_regression.csv"
            csv_path.write_text("x,y,z,target\n0,0,0,10\n1,1,1,100\n2,2,2,30\n", encoding="utf-8")
            self.assertTrue(self.service.load_csv(str(csv_path)).success)
            self.assertTrue(self.service.set_variable_config("x", "y", "z", "target").success)
            self.assertTrue(
                self.service.apply_dynamic_cutoff(
                    enabled=True,
                    target_column="target",
                    mode="percentile",
                    slider_percent=50.0,
                    output_column="target_capped",
                    keep_category_column=False,
                ).success
            )

            payload = self.service.prepare_univariate_data(use_effective_target=True)
            self.assertEqual(payload["diagnostics"]["target"], "target_capped")
            self.assertGreater(payload["diagnostics"]["target_valid_count"], 0)

    def test_statistics_table_safe_when_target_numeric_without_valid_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "nan_target.csv"
            csv_path.write_text("x,y,z,target\n1,2,3,\n4,5,6,\n", encoding="utf-8")
            result = self.service.load_csv(str(csv_path))
            self.assertTrue(result.success)
            cfg = self.service.set_variable_config("x", "y", "z", "target")
            self.assertTrue(cfg.success)

            table = dict(self.service.get_target_statistics_table())
            self.assertEqual(table["valid_count"], "0")
            self.assertEqual(table["null_pct"], "100")
            self.assertEqual(table["mean"], "nan")

    def test_prepare_univariate_contract_keys_and_types(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "univariate_contract.csv"
            csv_path.write_text(
                "x,y,z,target,dom\n0,0,0,10,a\n1,1,1,12,b\n2,2,2,foo,b\n3,3,3,13,a\n",
                encoding="utf-8",
            )
            self.assertTrue(self.service.load_csv(str(csv_path)).success)
            self.assertTrue(self.service.set_variable_config("x", "y", "z", "target", domain_column="dom").success)

            payload = self.service.prepare_univariate_data(max_domain_categories=5)

            expected_top_keys = {
                "target_values",
                "probplot_x",
                "probplot_y",
                "probability_failed",
                "domain_boxplot",
                "availability",
                "diagnostics",
            }
            self.assertEqual(set(payload.keys()), expected_top_keys)
            self.assertIsInstance(payload["target_values"], list)
            self.assertIsInstance(payload["probplot_x"], list)
            self.assertIsInstance(payload["probplot_y"], list)
            self.assertIsInstance(payload["probability_failed"], bool)
            self.assertIsInstance(payload["domain_boxplot"], dict)
            self.assertIsInstance(payload["availability"], dict)
            self.assertIsInstance(payload["diagnostics"], dict)

            self.assertEqual(
                set(payload["availability"].keys()),
                {"histogram", "boxplot", "probability"},
            )
            for comp in ("histogram", "boxplot", "probability"):
                self.assertIn("available", payload["availability"][comp])
                self.assertIn("message", payload["availability"][comp])
                self.assertIsInstance(payload["availability"][comp]["available"], bool)
                self.assertIsInstance(payload["availability"][comp]["message"], str)

            self.assertEqual(
                set(payload["domain_boxplot"].keys()),
                {"enabled", "labels", "values", "message", "valid_rows", "valid_categories"},
            )
            self.assertIsInstance(payload["domain_boxplot"]["enabled"], bool)
            self.assertIsInstance(payload["domain_boxplot"]["labels"], list)
            self.assertIsInstance(payload["domain_boxplot"]["values"], list)
            self.assertIsInstance(payload["domain_boxplot"]["message"], str)
            self.assertIsInstance(payload["domain_boxplot"]["valid_rows"], int)
            self.assertIsInstance(payload["domain_boxplot"]["valid_categories"], int)

            self.assertEqual(
                set(payload["diagnostics"].keys()),
                {
                    "target",
                    "domain",
                    "total_rows",
                    "target_valid_count",
                    "target_nan_count",
                    "domain_valid_rows",
                    "domain_valid_categories",
                },
            )
            self.assertIsInstance(payload["diagnostics"]["target"], str)
            self.assertIsInstance(payload["diagnostics"]["domain"], str)
            self.assertIsInstance(payload["diagnostics"]["total_rows"], int)
            self.assertIsInstance(payload["diagnostics"]["target_valid_count"], int)
            self.assertIsInstance(payload["diagnostics"]["target_nan_count"], int)
            self.assertIsInstance(payload["diagnostics"]["domain_valid_rows"], int)
            self.assertIsInstance(payload["diagnostics"]["domain_valid_categories"], int)

    def test_prepare_univariate_contract_preserved_when_domain_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "univariate_no_domain.csv"
            csv_path.write_text("x,y,z,target\n0,0,0,1\n1,1,1,2\n2,2,2,3\n", encoding="utf-8")
            self.assertTrue(self.service.load_csv(str(csv_path)).success)
            self.assertTrue(self.service.set_variable_config("x", "y", "z", "target", domain_column="dom").success)

            payload = self.service.prepare_univariate_data()
            self.assertIn("domain_boxplot", payload)
            self.assertEqual(
                set(payload["domain_boxplot"].keys()),
                {"enabled", "labels", "values", "message", "valid_rows", "valid_categories"},
            )
            self.assertFalse(payload["domain_boxplot"]["enabled"])
            self.assertIsInstance(payload["domain_boxplot"]["message"], str)
            self.assertGreaterEqual(payload["domain_boxplot"]["valid_rows"], 0)
            self.assertGreaterEqual(payload["domain_boxplot"]["valid_categories"], 0)

    def test_get_cutoff_state_contract_without_cutoffs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "cutoff_state_base.csv"
            csv_path.write_text("x,y,z,target\n0,0,0,1\n1,1,1,2\n", encoding="utf-8")
            self.assertTrue(self.service.load_csv(str(csv_path)).success)
            self.assertTrue(self.service.set_variable_config("x", "y", "z", "target").success)

            state = self.service.get_cutoff_state()
            expected_keys = {
                "enabled",
                "target_column",
                "limits",
                "labels",
                "output_column",
                "effective_target_column",
                "dynamic_enabled",
                "dynamic_target_column",
                "dynamic_mode",
                "dynamic_percent",
                "dynamic_cutoff_value",
                "dynamic_output_column",
                "dynamic_category_column",
            }
            self.assertEqual(set(state.keys()), expected_keys)
            self.assertFalse(state["enabled"])
            self.assertEqual(state["target_column"], "target")
            self.assertEqual(state["limits"], [])
            self.assertEqual(state["labels"], [])
            self.assertEqual(state["output_column"], "")
            self.assertEqual(state["effective_target_column"], "target")
            self.assertFalse(state["dynamic_enabled"])
            self.assertEqual(state["dynamic_target_column"], "target")
            self.assertEqual(state["dynamic_mode"], "percentile")
            self.assertEqual(state["dynamic_percent"], 95.0)
            self.assertEqual(state["dynamic_cutoff_value"], 0.0)
            self.assertEqual(state["dynamic_output_column"], "")
            self.assertEqual(state["dynamic_category_column"], "")

    def test_get_cutoff_state_contract_with_manual_cutoff(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "cutoff_state_manual.csv"
            csv_path.write_text("x,y,z,target\n0,0,0,1\n1,1,1,3\n2,2,2,5\n", encoding="utf-8")
            self.assertTrue(self.service.load_csv(str(csv_path)).success)
            self.assertTrue(self.service.set_variable_config("x", "y", "z", "target").success)
            result = self.service.apply_cutoffs(
                enabled=True,
                target_column="target",
                limits_text="2,4",
                output_column="target_cutoff_manual",
            )
            self.assertTrue(result.success)

            state = self.service.get_cutoff_state()
            self.assertTrue(state["enabled"])
            self.assertEqual(state["target_column"], "target")
            self.assertEqual(state["limits"], [2.0, 4.0])
            self.assertEqual(state["labels"], ["< 2", "[2, 4)", ">= 4"])
            self.assertEqual(state["output_column"], "target_cutoff_manual")
            self.assertEqual(state["effective_target_column"], "target_cutoff_manual")
            self.assertFalse(state["dynamic_enabled"])

    def test_get_cutoff_state_contract_with_dynamic_cutoff(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "cutoff_state_dynamic.csv"
            csv_path.write_text("x,y,z,target\n0,0,0,1\n1,1,1,100\n2,2,2,3\n3,3,3,4\n", encoding="utf-8")
            self.assertTrue(self.service.load_csv(str(csv_path)).success)
            self.assertTrue(self.service.set_variable_config("x", "y", "z", "target").success)

            result = self.service.apply_dynamic_cutoff(
                enabled=True,
                target_column="target",
                mode="percentile",
                slider_percent=50.0,
                output_column="target_capped_p50",
                keep_category_column=True,
            )
            self.assertTrue(result.success)

            state = self.service.get_cutoff_state()
            self.assertTrue(state["dynamic_enabled"])
            self.assertEqual(state["dynamic_target_column"], "target")
            self.assertEqual(state["dynamic_mode"], "percentile")
            self.assertEqual(state["dynamic_percent"], 50.0)
            self.assertGreater(state["dynamic_cutoff_value"], 0.0)
            self.assertEqual(state["dynamic_output_column"], "target_capped_p50")
            self.assertEqual(state["dynamic_category_column"], "target_capped_p50_class")
            self.assertEqual(state["effective_target_column"], "target_capped_p50")

    def test_analysis_context_snapshot_contract_without_dataset(self) -> None:
        context = self.service.get_analysis_context_snapshot()
        self.assertEqual(
            set(context.keys()),
            {
                "base_target_column",
                "effective_target_column",
                "resolved_target_column",
                "resolved_target_type",
                "active_domain_column",
                "active_domain_filter",
                "current_step",
                "readiness",
                "blocking_reason",
            },
        )
        self.assertEqual(context["readiness"], "blocked")
        self.assertEqual(context["blocking_reason"], "missing_dataset")
        self.assertEqual(context["current_step"], "Datos")

    def test_analysis_context_snapshot_base_effective_consistency(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "snapshot_consistency.csv"
            csv_path.write_text("x,y,z,target\n0,0,0,1\n1,1,1,100\n2,2,2,3\n", encoding="utf-8")
            self.assertTrue(self.service.load_csv(str(csv_path)).success)
            self.assertTrue(self.service.set_variable_config("x", "y", "z", "target").success)

            base_context = self.service.get_analysis_context_snapshot()
            self.assertEqual(base_context["base_target_column"], "target")
            self.assertEqual(base_context["effective_target_column"], "target")
            self.assertEqual(base_context["resolved_target_column"], "target")
            self.assertEqual(base_context["resolved_target_type"], "numeric")
            self.assertEqual(base_context["readiness"], "ready")
            self.assertEqual(base_context["blocking_reason"], "")

            self.assertTrue(
                self.service.apply_dynamic_cutoff(
                    enabled=True,
                    target_column="target",
                    mode="percentile",
                    slider_percent=50.0,
                    output_column="target_capped",
                    keep_category_column=False,
                ).success
            )
            capped_context = self.service.get_analysis_context_snapshot()
            self.assertEqual(capped_context["base_target_column"], "target")
            self.assertEqual(capped_context["effective_target_column"], "target_capped")
            self.assertEqual(capped_context["resolved_target_column"], "target_capped")
            self.assertEqual(capped_context["resolved_target_type"], "numeric")

    def test_analysis_context_snapshot_persists_domain_filter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "snapshot_domain_filter.csv"
            csv_path.write_text("x,y,z,target,dom\n0,0,0,1,a\n1,1,1,2,b\n2,2,2,3,a\n", encoding="utf-8")
            self.assertTrue(self.service.load_csv(str(csv_path)).success)
            self.assertTrue(self.service.set_variable_config("x", "y", "z", "target", domain_column="dom").success)
            applied = self.service.apply_domain_definition({"variable_base": "dom", "domains": {"A": ["a"], "B": ["b"]}})
            self.assertTrue(applied.success)
            self.assertTrue(self.service.set_active_domain("A").success)

            context = self.service.get_analysis_context_snapshot()
            self.assertEqual(context["active_domain_filter"], "A")
            self.assertEqual(context["active_domain_column"], "domain_estimation")

    def test_summary_cards_target_matches_context_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "summary_context_regression.csv"
            csv_path.write_text("x,y,z,target\n0,0,0,1\n1,1,1,3\n2,2,2,5\n", encoding="utf-8")
            self.assertTrue(self.service.load_csv(str(csv_path)).success)
            self.assertTrue(self.service.set_variable_config("x", "y", "z", "target").success)
            self.assertTrue(
                self.service.apply_cutoffs(
                    enabled=True,
                    target_column="target",
                    limits_text="2,4",
                    output_column="target_cutoff_manual",
                ).success
            )

            context = self.service.get_analysis_context_snapshot()
            cards = self.service.get_summary_cards()
            self.assertEqual(cards["Target"], context["resolved_target_column"])
            self.assertEqual(cards["Dataset"], self.service.current_dataset.file_name)
            self.assertEqual(cards["Muestras"], str(self.service.current_dataset.row_count))

    def test_prepare_domain_statistics_contract_without_active_layers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "domain_stats_empty.csv"
            csv_path.write_text("x,y,z,target,dom\n0,0,0,1,a\n1,1,1,2,b\n", encoding="utf-8")
            self.assertTrue(self.service.load_csv(str(csv_path)).success)
            self.assertTrue(self.service.set_variable_config("x", "y", "z", "target", domain_column="dom").success)

            payload = self.service.prepare_domain_statistics()
            self.assertEqual(set(payload.keys()), {"items", "selection_column", "active_layers"})
            self.assertEqual(payload["items"], [])
            self.assertEqual(payload["selection_column"], "")
            self.assertEqual(payload["active_layers"], [])

    def test_prepare_domain_statistics_uses_snapshot_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "domain_stats_snapshot.csv"
            csv_path.write_text("x,y,z,target,dom\n0,0,0,1,a\n1,1,1,2,b\n", encoding="utf-8")
            self.assertTrue(self.service.load_csv(str(csv_path)).success)
            self.assertTrue(self.service.set_variable_config("x", "y", "z", "target", domain_column="dom").success)
            self.assertTrue(
                self.service.apply_domain_definition({"variable_base": "dom", "domains": {"A": ["a"], "B": ["b"]}}).success
            )

            with patch.object(self.service, "get_analysis_context_snapshot", wraps=self.service.get_analysis_context_snapshot) as snapshot_mock:
                payload = self.service.prepare_domain_statistics()
            self.assertGreaterEqual(snapshot_mock.call_count, 1)
            self.assertEqual(payload["selection_column"], "domain_estimation")

    def test_prepare_domain_statistics_respects_active_domain_filter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "domain_stats_filter.csv"
            csv_path.write_text("x,y,z,target,dom\n0,0,0,1,a\n1,1,1,2,a\n2,2,2,4,b\n", encoding="utf-8")
            self.assertTrue(self.service.load_csv(str(csv_path)).success)
            self.assertTrue(self.service.set_variable_config("x", "y", "z", "target", domain_column="dom").success)
            self.assertTrue(
                self.service.apply_domain_definition({"variable_base": "dom", "domains": {"A": ["a"], "B": ["b"]}}).success
            )
            self.assertTrue(self.service.set_active_domain("A").success)

            payload = self.service.prepare_domain_statistics()
            self.assertEqual(payload["selection_column"], "domain_estimation")
            self.assertEqual(payload["total_rows"], 2)
            self.assertEqual([item["domain"] for item in payload["items"]], ["A"])

    def test_prepare_domain_statistics_empty_when_filter_column_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "domain_stats_missing_filter_column.csv"
            csv_path.write_text("x,y,z,target,dom\n0,0,0,1,a\n1,1,1,2,b\n", encoding="utf-8")
            self.assertTrue(self.service.load_csv(str(csv_path)).success)
            self.assertTrue(self.service.set_variable_config("x", "y", "z", "target", domain_column="dom").success)
            self.service.workflow_state.active_domain_filter = "A"
            self.service.variable_config.domain_column = "missing_filter_col"

            payload = self.service.prepare_domain_statistics()
            self.assertEqual(payload, {"items": [], "selection_column": "", "active_layers": []})

    def test_prepare_domain_statistics_empty_when_resolved_target_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "domain_stats_missing_target.csv"
            csv_path.write_text("x,y,z,target,dom\n0,0,0,1,a\n1,1,1,2,b\n", encoding="utf-8")
            self.assertTrue(self.service.load_csv(str(csv_path)).success)
            self.assertTrue(self.service.set_variable_config("x", "y", "z", "target", domain_column="dom").success)
            self.assertTrue(
                self.service.apply_dynamic_cutoff(
                    enabled=True,
                    target_column="target",
                    mode="percentile",
                    slider_percent=50.0,
                    output_column="target_capped_missing",
                    keep_category_column=False,
                ).success
            )
            self.service.current_dataset.dataframe.drop(columns=["target_capped_missing"], inplace=True)

            payload = self.service.prepare_domain_statistics()
            self.assertEqual(payload["items"], [])
            self.assertEqual(payload["selection_column"], "")

    def test_prepare_domain_statistics_empty_when_dataframe_filtered_to_zero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "domain_stats_empty_after_filter.csv"
            csv_path.write_text("x,y,z,target,dom\n0,0,0,1,a\n1,1,1,2,b\n", encoding="utf-8")
            self.assertTrue(self.service.load_csv(str(csv_path)).success)
            self.assertTrue(self.service.set_variable_config("x", "y", "z", "target", domain_column="dom").success)
            self.assertTrue(
                self.service.apply_domain_definition({"variable_base": "dom", "domains": {"A": ["a"], "B": ["b"]}}).success
            )
            self.service.workflow_state.active_domain_filter = "ZZZ"

            payload = self.service.prepare_domain_statistics()
            self.assertEqual(payload, {"items": [], "selection_column": "domain_estimation", "active_layers": []})

    def test_prepare_domain_statistics_with_effective_target_regression(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "domain_stats_effective_target.csv"
            csv_path.write_text("x,y,z,target,dom\n0,0,0,1,a\n1,1,1,3,a\n2,2,2,5,b\n", encoding="utf-8")
            self.assertTrue(self.service.load_csv(str(csv_path)).success)
            self.assertTrue(self.service.set_variable_config("x", "y", "z", "target", domain_column="dom").success)
            self.assertTrue(
                self.service.apply_domain_definition({"variable_base": "dom", "domains": {"A": ["a"], "B": ["b"]}}).success
            )
            self.assertTrue(
                self.service.apply_dynamic_cutoff(
                    enabled=True,
                    target_column="target",
                    mode="percentile",
                    slider_percent=50.0,
                    output_column="target_capped",
                    keep_category_column=False,
                ).success
            )

            payload = self.service.prepare_domain_statistics()
            self.assertEqual(payload["target_column"], "target_capped")
            self.assertGreater(payload["total_rows"], 0)

    def test_prepare_domain_statistics_legacy_domain_composite_still_supported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "domain_stats_legacy_composite.csv"
            csv_path.write_text(
                "x,y,z,target,dom,zone\n0,0,0,1,a,z1\n1,1,1,2,a,z1\n2,2,2,4,b,z2\n3,3,3,6,b,z2\n",
                encoding="utf-8",
            )
            self.assertTrue(self.service.load_csv(str(csv_path)).success)
            self.assertTrue(self.service.set_variable_config("x", "y", "z", "target", domain_column="dom").success)
            self.assertTrue(
                self.service.configure_domains(
                    ordered_layers=["dom", "zone"],
                    active_layers=["dom", "zone"],
                    min_samples=1,
                    include_missing=False,
                ).success
            )

            payload = self.service.prepare_domain_statistics()
            self.assertEqual(payload["selection_column"], "domain_composite")
            self.assertGreater(len(payload["items"]), 0)

    def test_prepare_domain_statistics_contract_with_configured_domains(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "domain_stats_full.csv"
            csv_path.write_text(
                "x,y,z,target,dom,zone\n0,0,0,1,a,z1\n1,1,1,2,a,z1\n2,2,2,4,b,z2\n3,3,3,6,b,z2\n",
                encoding="utf-8",
            )
            self.assertTrue(self.service.load_csv(str(csv_path)).success)
            self.assertTrue(self.service.set_variable_config("x", "y", "z", "target", domain_column="dom").success)
            applied = self.service.configure_domains(
                ordered_layers=["dom", "zone"],
                active_layers=["dom", "zone"],
                min_samples=1,
                include_missing=False,
            )
            self.assertTrue(applied.success)

            payload = self.service.prepare_domain_statistics()
            self.assertEqual(
                set(payload.keys()),
                {"items", "selection_column", "active_layers", "target_column", "total_rows", "min_samples"},
            )
            self.assertEqual(payload["selection_column"], "domain_composite")
            self.assertEqual(payload["active_layers"], ["dom", "zone"])
            self.assertEqual(payload["target_column"], "target")
            self.assertEqual(payload["total_rows"], 4)
            self.assertEqual(payload["min_samples"], 1)
            self.assertIsInstance(payload["items"], list)
            self.assertGreater(len(payload["items"]), 0)

            required_item_keys = {"domain", "count", "mean", "std", "cv", "pct_total", "indexes", "primary_group"}
            for item in payload["items"]:
                self.assertEqual(set(item.keys()), required_item_keys)
                self.assertIsInstance(item["domain"], str)
                self.assertIsInstance(item["count"], int)
                self.assertIsInstance(item["mean"], float)
                self.assertIsInstance(item["std"], float)
                self.assertIsInstance(item["cv"], float)
                self.assertIsInstance(item["pct_total"], float)
                self.assertIsInstance(item["indexes"], list)
                self.assertIsInstance(item["primary_group"], str)


if __name__ == "__main__":
    unittest.main()
