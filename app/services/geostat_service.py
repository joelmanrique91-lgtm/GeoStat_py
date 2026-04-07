"""Service layer for geostatistical workflows."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import math
import statistics

from app.adapters.geostatspy_adapter import GeostatSpyAdapter
from app.models.dataset_model import DatasetModel
from app.models.operational_state import (
    AnalysisContextState,
    CutoffState,
    DomainState,
    GeostatOperationalState,
    WorkflowReadinessState,
)
from app.models.variable_config_model import VariableConfigModel
from app.models.variography import VariographyComputeResponse, VariographySession
from app.models.workflow_state_model import WorkflowStateModel
from app.services.activity_log_service import ActivityLogService
from app.services.cutoff_service import CutoffService
from app.services.dataset_context_service import DatasetContextService
from app.services.operational_state_service import OperationalStateService
from app.services.repository_update_service import RepoUpdateResult, RepositoryUpdateService
from app.services.variography_application_service import VariographyApplicationService
from app.services.workflow_contracts import (
    DOMAIN_ESTIMATION_COLUMN,
    default_domain_ui_filters,
    resolve_active_domain_column,
)
from app.services.visualization_service import (
    Spatial3DDataBundle,
    SpatialDataBundle,
    SwathSeries,
    compute_swath_series,
    prepare_spatial_3d_cloud,
    prepare_spatial_sections,
)

WORKFLOW_STEPS = ["Datos", "EDA", "Cutoffs", "Espacial", "Dominios", "Variografía"]
FUNCTIONAL_STATUS = {step: "funcional" for step in WORKFLOW_STEPS}
STEP_EVENT_MAP = {
    "Datos": "workflow_step_data_opened",
    "EDA": "workflow_step_eda_opened",
    "Cutoffs": "workflow_step_cutoffs_opened",
    "Espacial": "workflow_step_spatial_opened",
    "Dominios": "workflow_step_domains_opened",
    "Variografía": "workflow_step_variography_opened",
}
STEP_DISPLAY_NAMES = {
    "Cutoffs": "Soporte/Compositado",
}


@dataclass
class LoadCsvResult:
    success: bool
    message: str
    details: str
    dataset: DatasetModel | None = None


@dataclass
class ColumnSelectionResult:
    success: bool
    message: str
    eda_summary: str


@dataclass
class VisualPreparationResult:
    success: bool
    message: str
    spatial_data: SpatialDataBundle | None


@dataclass
class Visual3DPreparationResult:
    success: bool
    message: str
    spatial_3d_data: Spatial3DDataBundle | None


@dataclass
class CutoffResult:
    success: bool
    message: str


@dataclass
class DynamicCutoffResult:
    success: bool
    message: str
    cutoff_value: float = 0.0


def _read_csv(path: Path):
    import pandas as pd

    return pd.read_csv(path)


def _read_csv_with_encoding(path: Path, encoding: str):
    import pandas as pd

    return pd.read_csv(path, encoding=encoding)


def _csv_errors():
    from pandas.errors import EmptyDataError, ParserError

    return EmptyDataError, ParserError


def _is_numeric_dtype(series) -> bool:
    from pandas.api.types import is_numeric_dtype

    return bool(is_numeric_dtype(series))


def _to_numeric(series):
    import pandas as pd

    return pd.to_numeric(series, errors="coerce")


def _is_missing_category(value: object) -> bool:
    if value is None:
        return True
    normalized = str(value).strip().lower()
    if normalized in {"", "na", "n/a", "null", "none", "nan"}:
        return True
    return False


def _normalize_identifier(value: str) -> str:
    """Normalize identifiers for resilient column matching."""
    return value.lower().replace("_", "").replace(" ", "")


def _pick_interval_columns(columns: list[str]) -> tuple[str, str, str]:
    normalized = {_normalize_identifier(col): col for col in columns}
    from_candidates = ["from", "depthfrom", "zfrom", "inicio", "desde"]
    to_candidates = ["to", "depthto", "zto", "fin", "hasta"]
    length_candidates = ["length", "interval", "samplelength", "thickness", "espesor"]

    def pick(candidates: list[str]) -> str:
        for candidate in candidates:
            c_norm = _normalize_identifier(candidate)
            for key, original in normalized.items():
                if key == c_norm or key.startswith(c_norm):
                    return original
        return ""

    return pick(from_candidates), pick(to_candidates), pick(length_candidates)


def _build_univariate_availability(target: str, valid_count: int, probability_min_samples: int = 3) -> dict[str, dict[str, object]]:
    histogram_available = valid_count > 0
    boxplot_available = valid_count > 0
    probability_available = valid_count >= probability_min_samples
    return {
        "histogram": {
            "available": histogram_available,
            "message": ""
            if histogram_available
            else f"Histograma no disponible: target {target} no tiene valores numéricos válidos.",
        },
        "boxplot": {
            "available": boxplot_available,
            "message": ""
            if boxplot_available
            else f"Boxplot general no disponible: target {target} no tiene valores numéricos válidos.",
        },
        "probability": {
            "available": probability_available,
            "message": ""
            if probability_available
            else f"Probability plot no disponible: menos de {probability_min_samples} valores válidos.",
        },
    }


def _empty_domain_payload(message: str = "") -> dict[str, object]:
    return {"enabled": False, "labels": [], "values": [], "message": message, "valid_rows": 0, "valid_categories": 0}


def _compute_target_statistics(clean, total: int) -> dict[str, float]:
    """Compute descriptive target metrics while preserving output contract."""
    if clean.empty:
        null_pct = float(((total - len(clean)) / total) * 100.0) if total else 0.0
        return {
            "valid_count": 0.0,
            "null_pct": null_pct,
            "mean": math.nan,
            "std": math.nan,
            "cv": math.nan,
            "min": math.nan,
            "p10": math.nan,
            "p25": math.nan,
            "p50": math.nan,
            "p75": math.nan,
            "p90": math.nan,
            "max": math.nan,
            "skewness": math.nan,
            "kurtosis": math.nan,
        }
    mean = float(clean.mean())
    std = float(clean.std())
    return {
        "valid_count": float(len(clean)),
        "null_pct": float(((total - len(clean)) / total) * 100.0) if total else 0.0,
        "mean": mean,
        "std": std,
        "cv": float(std / mean) if mean != 0 else 0.0,
        "min": float(clean.min()),
        "p10": float(clean.quantile(0.10)),
        "p25": float(clean.quantile(0.25)),
        "p50": float(clean.quantile(0.50)),
        "p75": float(clean.quantile(0.75)),
        "p90": float(clean.quantile(0.90)),
        "max": float(clean.max()),
        "skewness": float(clean.skew()) if len(clean) > 2 else math.nan,
        "kurtosis": float(clean.kurt()) if len(clean) > 3 else math.nan,
    }


class GeostatService:
    def __init__(self, adapter: GeostatSpyAdapter, activity_log: ActivityLogService | None = None) -> None:
        self.adapter = adapter
        self.activity_log = activity_log or ActivityLogService()
        self.current_dataset: DatasetModel | None = None
        self.variable_config: VariableConfigModel | None = None
        self.workflow_state = WorkflowStateModel()
        self.autodetected_columns: dict[str, str] = {}
        self.variography_service = VariographyApplicationService(host_service=self)
        self.operational_state_service = OperationalStateService(host_service=self)
        self.cutoff_service = CutoffService(host_service=self)
        self.dataset_context_service = DatasetContextService(host_service=self)
        self.repository_update_service = RepositoryUpdateService(host_service=self)
        self._domain_filter_context_enabled = True
        self._domains_module_enabled = True

    def set_workflow_step(self, step_name: str) -> str:
        if step_name not in WORKFLOW_STEPS:
            return "Paso de workflow no válido."
        self.workflow_state.current_step = step_name
        step_display_name = STEP_DISPLAY_NAMES.get(step_name, step_name)
        self.activity_log.log("workflow_step_changed", "info", f"Paso activo: {step_display_name}", {"step": step_name, "step_display": step_display_name})
        self.activity_log.log(STEP_EVENT_MAP[step_name], "info", f"Se abrió el paso {step_display_name}.", {"step": step_name, "step_display": step_display_name})
        return f"Paso activo: {step_display_name} (funcional)."

    def get_workflow_step_status(self) -> list[tuple[str, str]]:
        self.activity_log.log("workflow_simplified_view_loaded", "info", "Workflow simplificado cargado.", {"steps": WORKFLOW_STEPS})
        return [(step, FUNCTIONAL_STATUS[step]) for step in WORKFLOW_STEPS]

    def get_available_columns(self) -> list[str]:
        return self.dataset_context_service.get_available_columns()

    def load_csv(self, file_path: str) -> LoadCsvResult:
        success, message, details, dataset = self.dataset_context_service.load_csv(file_path)
        return LoadCsvResult(success, message, details, dataset)

    def autodetect_columns(self, columns: list[str], dataframe) -> dict[str, str]:
        return self.dataset_context_service.autodetect_columns(columns, dataframe)

    def get_autodetected_columns(self) -> dict[str, str]:
        return self.dataset_context_service.get_autodetected_columns()

    def get_domain_candidate_columns(self) -> list[str]:
        if self.current_dataset is None:
            return []
        domain_columns: list[str] = []
        for column in self.current_dataset.columns:
            if column == DOMAIN_ESTIMATION_COLUMN:
                continue
            if not _is_numeric_dtype(self.current_dataset.dataframe[column]):
                domain_columns.append(column)
        return domain_columns

    def get_domain_layer_candidates(self, max_low_cardinality: int = 20) -> list[str]:
        if self.current_dataset is None:
            return []
        df = self.current_dataset.dataframe
        candidates: list[str] = []
        for column in self.current_dataset.columns:
            series = df[column]
            is_explicit_category = str(series.dtype) == "category"
            distinct = int(series.nunique(dropna=True))
            is_low_cardinality_numeric = _is_numeric_dtype(series) and 1 < distinct <= max_low_cardinality
            if is_explicit_category or (not _is_numeric_dtype(series)) or is_low_cardinality_numeric:
                candidates.append(column)
        return candidates

    def get_domain_filter_candidates(self) -> dict[str, str]:
        """Resolve best-effort columns for iterative domain filters."""
        if self.current_dataset is None:
            return default_domain_ui_filters()
        available = set(self.current_dataset.columns)
        normalized = {_normalize_identifier(column): column for column in self.current_dataset.columns}

        def pick(candidates: list[str]) -> str:
            for candidate in candidates:
                normalized_candidate = _normalize_identifier(candidate)
                for key, original in normalized.items():
                    if key == normalized_candidate or key.startswith(normalized_candidate):
                        return original
            return ""

        guessed = {
            "lithology": pick(["lithology", "lito", "litologia", "litología", "rocktype"]),
            "alteration": pick(["alteration", "alteracion", "alteración", "alt"]),
            "mine": pick(["mine", "mina", "pit"]),
        }
        stored = dict(self.workflow_state.domain_filter_columns or {})
        resolved: dict[str, str] = {}
        for key in ["lithology", "alteration", "mine"]:
            current = str(stored.get(key, "")).strip()
            if current and current in available:
                resolved[key] = current
            else:
                resolved[key] = str(guessed.get(key, "")).strip()
        self.workflow_state.domain_filter_columns = resolved
        return dict(resolved)

    def get_domain_filter_options(self) -> dict[str, list[str]]:
        default_keys = tuple(default_domain_ui_filters().keys())
        if self.current_dataset is None:
            return {key: ["Todos"] for key in default_keys}
        df = self.current_dataset.dataframe
        options: dict[str, list[str]] = {}
        for key, column in self.get_domain_filter_candidates().items():
            if not column or column not in df.columns:
                options[key] = ["Todos"]
                continue
            values = sorted({str(value).strip() for value in df[column].dropna().tolist() if str(value).strip()})
            options[key] = ["Todos", *values]
        for key in default_keys:
            options.setdefault(key, ["Todos"])
        return options

    def set_domain_ui_filters(self, filters: dict[str, str] | None) -> dict[str, str]:
        normalized = default_domain_ui_filters()
        incoming = filters or {}
        for key in normalized:
            value = str(incoming.get(key, "")).strip()
            normalized[key] = value
        self.workflow_state.domain_ui_filters = normalized
        return dict(self.workflow_state.domain_ui_filters)

    def get_domain_ui_filters(self) -> dict[str, str]:
        filters = dict(self.workflow_state.domain_ui_filters or {})
        normalized = default_domain_ui_filters()
        for key in normalized:
            value = str(filters.get(key, "")).strip()
            normalized[key] = value
        return normalized

    def is_domains_module_enabled(self) -> bool:
        return bool(self._domains_module_enabled)

    def configure_domains(self, ordered_layers: list[str], active_layers: list[str], min_samples: int = 1, include_missing: bool = False) -> CutoffResult:
        del ordered_layers, active_layers, min_samples, include_missing
        if self.current_dataset is None or self.variable_config is None:
            return CutoffResult(False, "Configura datos antes de Dominios.")
        self._domains_module_enabled = True
        return CutoffResult(True, "Dominios habilitado para configuración.")

    def apply_domain_definition(self, domain_definition: dict) -> CutoffResult:
        if self.current_dataset is None:
            return CutoffResult(False, "No hay dataset cargado.")
        if self.variable_config is None:
            return CutoffResult(False, "Configura X/Y/Z/target antes de Dominios.")
        if not bool(self.workflow_state.support_confirmed):
            return CutoffResult(False, "Confirma soporte/compositado antes de definir dominios.")
        variable_base = str(domain_definition.get("variable_base", "")).strip()
        domains = domain_definition.get("domains", {})
        if not variable_base or variable_base not in self.current_dataset.dataframe.columns:
            return CutoffResult(False, "Selecciona una columna base válida para construir dominios.")
        if not isinstance(domains, dict) or not domains:
            return CutoffResult(False, "Define al menos un dominio antes de aplicar.")
        df = self.current_dataset.dataframe
        mapped: dict[str, str] = {}
        for domain_name, categories in domains.items():
            normalized_name = str(domain_name).strip()
            if not normalized_name:
                continue
            if not isinstance(categories, list):
                continue
            for category in categories:
                cat = str(category).strip()
                if cat:
                    mapped[cat] = normalized_name
        if not mapped:
            return CutoffResult(False, "No hay categorías válidas para asignar a dominios.")
        source = df[variable_base].astype(str).str.strip()
        df[DOMAIN_ESTIMATION_COLUMN] = source.map(mapped).fillna("Sin dominio")
        if DOMAIN_ESTIMATION_COLUMN not in self.current_dataset.columns:
            self.current_dataset.columns.append(DOMAIN_ESTIMATION_COLUMN)
            self.current_dataset.column_count = len(self.current_dataset.columns)
        self.workflow_state.domain_definition = {
            "variable_base": variable_base,
            "domains": {str(k): list(v) for k, v in domains.items()},
        }
        self.workflow_state.domain_output_column = DOMAIN_ESTIMATION_COLUMN
        if self.variable_config is not None:
            self.variable_config.domain_column = DOMAIN_ESTIMATION_COLUMN
        self.workflow_state.active_domain = "Columna: domain_estimation"
        self.workflow_state.support_confirmed = bool(self.workflow_state.support_confirmed)
        self.activity_log.log(
            "domain_definition_applied",
            "success",
            "Definición de dominios aplicada.",
            {"variable_base": variable_base, "domain_count": len(domains)},
        )
        self.get_variography_session().mark_dirty()
        return CutoffResult(True, "Dominios aplicados al dataset.")

    def set_active_domain(self, domain_name: str | None) -> CutoffResult:
        if self.current_dataset is None:
            return CutoffResult(False, "No hay dataset cargado.")
        snapshot = self.get_analysis_context_snapshot()
        active_domain_column = str(snapshot.get("active_domain_column") or "").strip()
        if not active_domain_column:
            self.workflow_state.active_domain_filter = ""
            self.activity_log.log("domain_filter_applied", "info", "Filtro de dominio ignorado: sin columna de dominio activa.", {})
            return CutoffResult(True, "Filtro de dominio ignorado (sin dominio efectivo configurado).")
        selected = str(domain_name or "").strip()
        if not selected or selected.lower() == "todos":
            self.workflow_state.active_domain_filter = ""
            self.workflow_state.allow_variography_without_domain = True
            self.get_variography_session().mark_dirty()
            self.activity_log.log("domain_filter_applied", "info", "Filtro de dominio limpiado.", {"column": active_domain_column})
            return CutoffResult(True, "Filtro de dominio limpiado.")
        options = set(self.get_domain_estimation_values())
        if selected not in options:
            return CutoffResult(False, f"Dominio no válido: '{selected}'.")
        self.workflow_state.active_domain_filter = selected
        self.workflow_state.allow_variography_without_domain = False
        self.get_variography_session().mark_dirty()
        self.activity_log.log(
            "domain_filter_applied",
            "success",
            "Filtro de dominio aplicado.",
            {"column": active_domain_column, "value": selected},
        )
        return CutoffResult(True, f"Filtro de dominio aplicado: {selected}")

    def get_domain_estimation_values(self) -> list[str]:
        if self.current_dataset is None:
            return []
        dataframe = self.current_dataset.dataframe
        active_domain_column = resolve_active_domain_column(
            dataframe,
            self.variable_config.domain_column if self.variable_config is not None else "",
        )
        if not active_domain_column:
            return []
        values = sorted({str(value).strip() for value in dataframe[active_domain_column].dropna().tolist() if str(value).strip()})
        return values

    def get_domain_state_typed(self) -> DomainState:
        return self.operational_state_service.build_domain_state()

    def get_domain_state(self) -> dict[str, object]:
        return self.get_domain_state_typed().as_dict()

    def _get_domain_ui_filtered_dataframe(self):
        if self.current_dataset is None:
            return None, default_domain_ui_filters(), self.get_domain_filter_candidates()
        df = self.current_dataset.dataframe
        filters = self.get_domain_ui_filters()
        columns = self.get_domain_filter_candidates()
        filtered = df
        for key in ["lithology", "alteration", "mine"]:
            value = str(filters.get(key, "")).strip()
            column = str(columns.get(key, "")).strip()
            if not value or not column or column not in filtered.columns:
                continue
            filtered = filtered[filtered[column].astype(str).str.strip() == value]
        return filtered, filters, columns

    def prepare_iterative_domain_data(self) -> dict[str, object]:
        if self.current_dataset is None:
            return {"ready": False, "message": "No hay dataset cargado."}
        candidates = self.get_domain_candidate_columns()
        return {
            "ready": bool(candidates),
            "message": "Dominios listos para configuración." if candidates else "No hay columnas categóricas para dominios.",
            "candidate_columns": candidates,
            "active_domain_column": self.get_analysis_context_snapshot().get("active_domain_column", ""),
            "active_domain_filter": self.workflow_state.active_domain_filter or "Todos",
        }

    def confirm_domain_assignment(self, domain_name: str) -> CutoffResult:
        if self.current_dataset is None or self.variable_config is None:
            return CutoffResult(False, "Configura datos antes de confirmar dominios.")
        snapshot = self.get_analysis_context_snapshot()
        active_domain_column = str(snapshot.get("active_domain_column") or "").strip()
        if not active_domain_column:
            return CutoffResult(False, "No hay columna de dominio activa.")
        selected = str(domain_name or "").strip()
        if not selected:
            return CutoffResult(False, "Selecciona un dominio para confirmar.")
        values = set(self.get_domain_estimation_values())
        if selected not in values:
            return CutoffResult(False, f"Dominio no válido: '{selected}'.")
        self.workflow_state.active_domain_filter = selected
        self.workflow_state.active_domain = f"{active_domain_column}: {selected}"
        self.workflow_state.allow_variography_without_domain = False
        self.workflow_state.domain_assignment_sequence += 1
        self.workflow_state.domain_assignment_history.append(
            {"sequence": self.workflow_state.domain_assignment_sequence, "domain": selected, "column": active_domain_column}
        )
        self.activity_log.log(
            "domain_assignment_confirmed",
            "success",
            "Dominio confirmado para continuidad y variografía.",
            {"domain_column": active_domain_column, "domain_value": selected},
        )
        self.get_variography_session().mark_dirty()
        return CutoffResult(True, f"Dominio confirmado: {selected}")

    def prepare_domain_statistics(self) -> dict[str, object]:
        return {"items": [], "selection_column": "", "active_layers": []}

    def _resolve_domain_statistics_context(self) -> tuple[dict[str, object], str]:
        base_context: dict[str, object] = {
            "selection_column": self.workflow_state.domain_output_column,
            "active_layers": list(self.workflow_state.domain_active_layers),
            "target_column": "",
            "dataframe": None,
        }
        snapshot = self.get_analysis_context_snapshot()
        if snapshot["readiness"] == "blocked" and snapshot["blocking_reason"] in {"missing_dataset", "missing_variable_config"}:
            return base_context, "No hay dataset/configuración suficiente para Dominios."
        if self.current_dataset is None or self.variable_config is None:
            return base_context, "No hay dataset/configuración suficiente para Dominios."

        dataframe = self.current_dataset.dataframe
        selection_column = str(self.workflow_state.domain_output_column or "")
        active_domain_column = str(snapshot["active_domain_column"] or "").strip()
        if not selection_column:
            if DOMAIN_ESTIMATION_COLUMN in dataframe.columns:
                selection_column = DOMAIN_ESTIMATION_COLUMN

        base_context["selection_column"] = selection_column
        base_context["target_column"] = str(snapshot["resolved_target_column"])
        base_context["dataframe"] = dataframe

        if not selection_column or selection_column not in dataframe.columns:
            return base_context, "domain_column_missing"
        target_column = str(snapshot["resolved_target_column"])
        if not target_column or target_column not in dataframe.columns:
            return base_context, "resolved_target_missing"

        active_filter = str(snapshot["active_domain_filter"]).strip()
        if active_filter:
            filter_column = active_domain_column or selection_column
            if filter_column not in dataframe.columns:
                if DOMAIN_ESTIMATION_COLUMN in dataframe.columns:
                    filter_column = DOMAIN_ESTIMATION_COLUMN
                else:
                    return base_context, f"Filtro de dominio activo sobre columna inexistente: '{filter_column}'."
            dataframe = dataframe[dataframe[filter_column].astype(str) == active_filter]
        if dataframe.empty:
            return base_context, "filtered_dataframe_empty"

        target_series = dataframe[target_column]
        if not _is_numeric_dtype(target_series) and not _to_numeric(target_series).notna().any():
            return base_context, "non_numeric_target_for_domain_stats"

        base_context["dataframe"] = dataframe
        return base_context, ""

    def set_variable_config(
        self,
        x_column: str,
        y_column: str,
        z_column: str,
        target_column: str,
        hole_id_column: str | None = None,
        domain_column: str | None = None,
    ) -> ColumnSelectionResult:
        success, message, details = self.dataset_context_service.set_variable_config(
            x_column=x_column,
            y_column=y_column,
            z_column=z_column,
            target_column=target_column,
            hole_id_column=hole_id_column,
            domain_column=domain_column,
        )
        return ColumnSelectionResult(success, message, details)

    def get_numeric_columns(self) -> list[str]:
        return self.dataset_context_service.get_numeric_columns()

    def get_categorical_columns(self) -> list[str]:
        return self.dataset_context_service.get_categorical_columns()

    def get_cutoff_state_typed(self) -> CutoffState:
        return self.operational_state_service.build_cutoff_state()

    def get_cutoff_state(self) -> dict[str, object]:
        return self.get_cutoff_state_typed().as_dict()

    def has_confirmed_dynamic_capping(self) -> bool:
        return self.cutoff_service.has_confirmed_dynamic_capping()

    def prepare_dynamic_cutoff_preview(self, target_column: str, mode: str, slider_percent: float) -> dict[str, object]:
        return self.cutoff_service.prepare_dynamic_cutoff_preview(target_column, mode, slider_percent)

    def apply_dynamic_cutoff(
        self,
        enabled: bool,
        target_column: str,
        mode: str,
        slider_percent: float,
        output_column: str | None = None,
        keep_category_column: bool = True,
    ) -> DynamicCutoffResult:
        success, message, cutoff = self.cutoff_service.apply_dynamic_cutoff(
            enabled=enabled,
            target_column=target_column,
            mode=mode,
            slider_percent=slider_percent,
            output_column=output_column,
            keep_category_column=keep_category_column,
        )
        return DynamicCutoffResult(success, message, cutoff)

    def apply_cutoffs(self, enabled: bool, target_column: str, limits_text: str, output_column: str | None = None) -> CutoffResult:
        success, message = self.cutoff_service.apply_cutoffs(
            enabled=enabled,
            target_column=target_column,
            limits_text=limits_text,
            output_column=output_column,
        )
        return CutoffResult(success, message)

    def _parse_cutoff_limits(self, limits_text: str) -> tuple[list[float], str]:
        return self.cutoff_service.parse_cutoff_limits(limits_text)

    def _build_cutoff_labels(self, limits: list[float]) -> list[str]:
        return self.cutoff_service.build_cutoff_labels(limits)

    def _format_cutoff_number(self, value: float) -> str:
        return self.cutoff_service.format_cutoff_number(value)

    def _clear_cutoff_state(self) -> None:
        self.cutoff_service.clear_cutoff_state()

    def _clear_dynamic_cutoff_state(self) -> None:
        self.cutoff_service.clear_dynamic_cutoff_state()

    def _clear_domain_state(self) -> None:
        self.workflow_state.domain_layers_order = []
        self.workflow_state.domain_active_layers = []
        self.workflow_state.domain_output_column = ""
        self.workflow_state.domain_min_samples = 1
        self.workflow_state.domain_include_missing = False
        self.workflow_state.domain_definition = {}
        self.workflow_state.active_domain_filter = ""
        self.workflow_state.domain_ui_filters = default_domain_ui_filters()
        self.workflow_state.domain_filter_columns = default_domain_ui_filters()
        self.workflow_state.domain_assignment_history = []
        self.workflow_state.domain_assignment_sequence = 0
        self.workflow_state.allow_variography_without_domain = False
        if self.variable_config is not None and self.variable_config.domain_column == DOMAIN_ESTIMATION_COLUMN:
            self.variable_config.domain_column = None

    def clear_support_state(self) -> None:
        self.workflow_state.support_composite_enabled = False
        self.workflow_state.support_composite_length = 0.0
        self.workflow_state.support_source_target_column = ""
        self.workflow_state.support_output_target_column = ""
        self.workflow_state.support_pre_count = 0
        self.workflow_state.support_post_count = 0
        self.workflow_state.support_confirmed = False
        self.workflow_state.support_mode = "none"
        self.workflow_state.support_details = ""
        self.workflow_state.support_warning = ""

    def get_support_state(self) -> dict[str, object]:
        return {
            "enabled": bool(self.workflow_state.support_composite_enabled),
            "composite_length": float(self.workflow_state.support_composite_length),
            "source_target": str(self.workflow_state.support_source_target_column),
            "output_target": str(self.workflow_state.support_output_target_column),
            "pre_count": int(self.workflow_state.support_pre_count),
            "post_count": int(self.workflow_state.support_post_count),
            "confirmed": bool(self.workflow_state.support_confirmed),
            "mode": str(self.workflow_state.support_mode),
            "details": str(self.workflow_state.support_details),
            "warning": str(self.workflow_state.support_warning),
        }

    def apply_basic_compositing(self, *, composite_length: float, target_column: str, output_column: str | None = None) -> CutoffResult:
        if self.current_dataset is None or self.variable_config is None:
            return CutoffResult(False, "Configura datos antes de compositar.")
        if composite_length <= 0:
            return CutoffResult(False, "La longitud de composite debe ser mayor a 0.")
        if target_column not in self.current_dataset.dataframe.columns:
            return CutoffResult(False, "La variable objetivo para composite no existe.")
        df = self.current_dataset.dataframe
        out_col = str(output_column or f"{target_column}_comp").strip()
        if not out_col:
            return CutoffResult(False, "Nombre de salida de composite inválido.")
        if out_col in {self.variable_config.x_column, self.variable_config.y_column, self.variable_config.z_column}:
            return CutoffResult(False, "El nombre de salida de composite no puede sobrescribir X/Y/Z.")
        if out_col in df.columns and out_col != self.workflow_state.support_output_target_column:
            return CutoffResult(False, f"La columna '{out_col}' ya existe.")

        numeric = _to_numeric(df[target_column])
        x_num = _to_numeric(df[self.variable_config.x_column])
        y_num = _to_numeric(df[self.variable_config.y_column])
        z_num = _to_numeric(df[self.variable_config.z_column])
        valid = numeric.notna() & x_num.notna() & y_num.notna() & z_num.notna()
        if int(valid.sum()) < 2:
            return CutoffResult(False, "No hay suficientes muestras válidas para compositado básico.")
        work = df.loc[valid, :].copy()
        work["_target_num"] = numeric.loc[valid].astype(float)
        work["_z_num"] = z_num.loc[valid].astype(float)
        hole_col = self.variable_config.hole_id_column if self.variable_config.hole_id_column and self.variable_config.hole_id_column in work.columns else None
        if hole_col:
            work["_hole_group"] = work[hole_col].astype(str).fillna("NA")
        else:
            work["_hole_group"] = "__global__"
        from_col, to_col, length_col = _pick_interval_columns(list(df.columns))
        real_support_used = bool(from_col and (to_col or length_col))
        discarded = 0
        if real_support_used:
            from_num = _to_numeric(work[from_col])
            if to_col:
                to_num = _to_numeric(work[to_col])
                sample_len = (to_num - from_num)
            else:
                sample_len = _to_numeric(work[length_col]).abs()
                to_num = from_num + sample_len
            good = from_num.notna() & to_num.notna() & sample_len.notna() & (sample_len > 0)
            discarded = int((~good).sum())
            work = work.loc[good, :].copy()
            from_num = from_num.loc[good].astype(float)
            to_num = to_num.loc[good].astype(float)
            sample_len = sample_len.loc[good].astype(float)
            work["_depth_from"] = from_num.values
            work["_depth_to"] = to_num.values
            work["_sample_len"] = sample_len.values
            if work.empty:
                return CutoffResult(False, "No hay intervalos válidos para compositado real.")
            work = work.sort_values(["_hole_group", "_depth_from", "_depth_to"], kind="mergesort")
            comp_ids: list[tuple[str, int]] = []
            weighted_values: list[float] = []
            for hole, hole_df in work.groupby("_hole_group", sort=False):
                start_depth = float(hole_df["_depth_from"].min())
                comp_index = ((hole_df["_depth_from"] - start_depth) / float(composite_length)).astype(int)
                for idx in comp_index.tolist():
                    comp_ids.append((str(hole), int(idx)))
                grouped = hole_df.assign(_comp_idx=comp_index).groupby("_comp_idx", sort=True)
                weighted_map: dict[int, float] = {}
                for comp_idx, block in grouped:
                    w = block["_sample_len"].astype(float)
                    val = block["_target_num"].astype(float)
                    weight_sum = float(w.sum())
                    weighted_map[int(comp_idx)] = float((val * w).sum() / weight_sum) if weight_sum > 0 else float(val.mean())
                weighted_values.extend([weighted_map[int(idx)] for idx in comp_index.tolist()])
            work["_composite_group"] = [f"{hole}:{idx}" for hole, idx in comp_ids]
            composite_values = weighted_values
            mode = "interval_real"
            details = (
                f"Compositado por intervalos ({from_col} + {to_col or length_col}), "
                f"ponderado por longitud real."
            )
            warning = "" if discarded == 0 else f"Se descartaron {discarded} muestras sin longitud válida."
        else:
            work = work.sort_values(["_hole_group", "_z_num"], kind="mergesort")
            group_size = max(1, int(round(float(composite_length))))
            work["_composite_group"] = work.groupby("_hole_group").cumcount() // group_size
            composite_values = work.groupby(["_hole_group", "_composite_group"])["_target_num"].transform("mean").tolist()
            mode = "fallback_approx"
            details = "Fallback aproximado por orden Z y tamaño de grupo (sin intervalos reales)."
            warning = "No se detectaron columnas de intervalo; el soporte es aproximado."
        df[out_col] = df[target_column]
        df.loc[work.index, out_col] = composite_values

        if out_col not in self.current_dataset.columns:
            self.current_dataset.columns.append(out_col)
            self.current_dataset.column_count = len(self.current_dataset.columns)
        self.workflow_state.support_composite_enabled = True
        self.workflow_state.support_composite_length = float(composite_length)
        self.workflow_state.support_source_target_column = target_column
        self.workflow_state.support_output_target_column = out_col
        self.workflow_state.support_pre_count = int(len(work))
        self.workflow_state.support_post_count = int(work[["_hole_group", "_composite_group"]].drop_duplicates().shape[0])
        self.workflow_state.support_confirmed = True
        self.workflow_state.support_mode = mode
        self.workflow_state.support_details = details
        self.workflow_state.support_warning = warning
        self.workflow_state.effective_target_column = out_col
        self.activity_log.log(
            "support_composite_applied",
            "success",
            "Compositado básico aplicado.",
            {
                "composite_length": float(composite_length),
                "source_target": target_column,
                "output_target": out_col,
                "samples_before": self.workflow_state.support_pre_count,
                "samples_after_groups": self.workflow_state.support_post_count,
                "support_mode": mode,
                "support_details": details,
                "support_warning": warning,
                "discarded_samples": discarded,
            },
        )
        label = "Compositado real por intervalos aplicado." if mode == "interval_real" else "Compositado fallback aproximado aplicado."
        return CutoffResult(True, f"{label} Target efectivo: {out_col}")

    def _get_effective_target_column(self) -> str:
        """Resolve effective target with legacy precedence.

        Precedence is intentionally conservative and mirrors current behavior:
        dynamic cutoff output > manual cutoff output > base target from variable config.

        This helper remains for backward-compatible internal usage.
        New consumers should prefer `get_analysis_context_snapshot()`.
        """
        if self.workflow_state.dynamic_cutoff_enabled and self.workflow_state.dynamic_cutoff_output_column:
            return self.workflow_state.dynamic_cutoff_output_column
        if self.workflow_state.cutoffs_enabled and self.workflow_state.cutoff_output_column:
            return self.workflow_state.cutoff_output_column
        if self.workflow_state.support_composite_enabled and self.workflow_state.support_output_target_column:
            return self.workflow_state.support_output_target_column
        if self.variable_config is None:
            return ""
        return self.variable_config.target_column

    def get_analysis_context_state(self) -> AnalysisContextState:
        self.cutoff_service.ensure_state_integrity()
        return self.operational_state_service.build_analysis_context_state()

    def get_analysis_context_snapshot(self) -> dict[str, object]:
        payload = self.get_analysis_context_state().as_dict()
        payload.pop("dataset_name", None)
        return payload

    def get_workflow_readiness_state(self) -> WorkflowReadinessState:
        return self.operational_state_service.build_workflow_readiness_state()

    def get_workflow_readiness(self) -> dict[str, object]:
        return self.get_workflow_readiness_state().as_dict()

    def get_operational_state(self) -> GeostatOperationalState:
        return self.operational_state_service.build_operational_state()

    def get_effective_workflow_context(self) -> dict[str, object]:
        snapshot = self.get_analysis_context_snapshot()
        support = self.get_support_state()
        domain_column = str(snapshot.get("active_domain_column", ""))
        active_domain = str(snapshot.get("active_domain_filter", ""))
        domain_confirmed = bool(domain_column and active_domain)
        return {
            "target_base": str(snapshot.get("base_target_column", "")),
            "target_effective": str(snapshot.get("resolved_target_column", "")),
            "domain_effective_column": domain_column,
            "active_domain": active_domain,
            "domain_confirmed": domain_confirmed,
            "support_mode": str(support.get("mode", "none")),
            "support_details": str(support.get("details", "")),
            "support_warning": str(support.get("warning", "")),
            "domain_bypass_active": bool(self.workflow_state.allow_variography_without_domain),
            # backward-compat aliases
            "domain_column": domain_column,
            "domain_filter": active_domain,
            "bypass_domain": bool(self.workflow_state.allow_variography_without_domain),
        }

    def _get_filtered_dataframe(self, context_snapshot: dict[str, object] | None = None):
        if self.current_dataset is None:
            return None
        snapshot = context_snapshot or self.get_analysis_context_snapshot()
        dataframe = self.current_dataset.dataframe
        active_filter = str(snapshot.get("active_domain_filter", "")).strip()
        if not active_filter:
            return dataframe
        active_domain_column = str(snapshot.get("active_domain_column", "")).strip() or DOMAIN_ESTIMATION_COLUMN
        if active_domain_column not in dataframe.columns and DOMAIN_ESTIMATION_COLUMN in dataframe.columns:
            active_domain_column = DOMAIN_ESTIMATION_COLUMN
        if active_domain_column not in dataframe.columns:
            return dataframe
        return dataframe[dataframe[active_domain_column].astype(str) == active_filter]

    def _resolve_spatial_visual_context(self, color_by: str | None) -> tuple[object | None, str, bool, str]:
        snapshot = self.get_analysis_context_snapshot()
        if snapshot["readiness"] == "blocked":
            if snapshot["blocking_reason"] == "missing_resolved_target_column":
                missing_target = str(snapshot["resolved_target_column"])
                return None, "", False, f"Target no válido para secciones espaciales: '{missing_target}'."
        readiness_message = self._resolve_dataset_config_readiness_error(snapshot, context="renderizar visuales")
        if readiness_message:
            return None, "", False, readiness_message

        dataframe = self.current_dataset.dataframe
        resolved_target = str(snapshot["resolved_target_column"])
        if not resolved_target or resolved_target not in dataframe.columns:
            return None, "", False, f"Target no válido para secciones espaciales: '{resolved_target}'."

        active_filter = str(snapshot["active_domain_filter"]).strip()
        active_domain_column = str(snapshot["active_domain_column"]).strip() or DOMAIN_ESTIMATION_COLUMN
        if active_filter and active_domain_column not in dataframe.columns:
            if DOMAIN_ESTIMATION_COLUMN in dataframe.columns:
                active_domain_column = DOMAIN_ESTIMATION_COLUMN
            else:
                return None, "", False, f"Filtro de dominio activo sobre columna inexistente: '{active_domain_column}'."

        filtered = self._get_filtered_dataframe(
            {
                "active_domain_filter": active_filter,
                "active_domain_column": active_domain_column,
            }
        )

        color_column = (color_by or "").strip() or resolved_target
        if color_column not in dataframe.columns:
            return None, "", False, f"La columna de color no existe: '{color_column}'."
        allow_categorical = bool(color_column != resolved_target or self.workflow_state.cutoffs_enabled)
        return filtered, color_column, allow_categorical, ""

    def prepare_visual_data(self, color_by: str | None = None) -> VisualPreparationResult:
        self.activity_log.log("dashboard_render_started", "info", "Render espacial iniciado.", {"view": "Espacial"})
        dataframe, color_column, allow_categorical, context_error = self._resolve_spatial_visual_context(color_by)
        if context_error:
            message = context_error
            self.activity_log.log("dashboard_render_failed", "error", message, {"view": "Espacial"})
            return VisualPreparationResult(False, message, None)
        try:
            spatial = prepare_spatial_sections(
                dataframe,
                self.variable_config.x_column,
                self.variable_config.y_column,
                self.variable_config.z_column,
                color_column,
                allow_categorical_target=allow_categorical,
            )
        except ValueError as exc:
            self.activity_log.log("dashboard_render_failed", "error", str(exc), {"view": "Espacial"})
            return VisualPreparationResult(False, str(exc), None)

        self.activity_log.log(
            "spatial_2d_rendered",
            "success",
            "Vistas espaciales 2D preparadas.",
            {"rows": len(spatial.target), "target_column": str(self.get_analysis_context_snapshot()["resolved_target_column"])},
        )
        self.activity_log.log("dashboard_render_finished", "success", "Render espacial finalizado.", {"view": "Espacial"})
        return VisualPreparationResult(True, "Visuales preparados.", spatial)

    def prepare_visual_3d_data(self, color_by: str | None = None, max_points: int = 40000) -> Visual3DPreparationResult:
        self.activity_log.log("dashboard_render_started", "info", "Render espacial 3D iniciado.", {"view": "Espacial 3D"})
        dataframe, color_column, allow_categorical, context_error = self._resolve_spatial_visual_context(color_by)
        if context_error:
            self.activity_log.log("dashboard_render_failed", "error", context_error, {"view": "Espacial 3D"})
            return Visual3DPreparationResult(False, context_error, None)
        try:
            spatial = prepare_spatial_3d_cloud(
                dataframe,
                self.variable_config.x_column,
                self.variable_config.y_column,
                self.variable_config.z_column,
                color_column,
                max_points=max_points,
                allow_categorical_color=allow_categorical,
            )
        except ValueError as exc:
            self.activity_log.log("dashboard_render_failed", "error", str(exc), {"view": "Espacial 3D"})
            return Visual3DPreparationResult(False, str(exc), None)

        self.activity_log.log(
            "spatial_3d_rendered",
            "success",
            "Vista espacial 3D preparada.",
            {
                "rows": spatial.point_count_rendered,
                "source_rows": spatial.point_count_original,
                "color_column": color_column,
                "color_mode": spatial.color_mode,
            },
        )
        self.activity_log.log("dashboard_render_finished", "success", "Render espacial 3D finalizado.", {"view": "Espacial 3D"})
        return Visual3DPreparationResult(True, "Visual 3D preparado.", spatial)

    def prepare_univariate_data(
        self,
        max_domain_categories: int = 10,
        use_effective_target: bool = False,
        domain_filter: str | None = None,
    ) -> dict:
        target, message = self._resolve_eda_target_column(use_effective_target=use_effective_target, require_numeric=True)
        if message:
            self.activity_log.log("eda_univariate_payload_empty", "warning", message, {})
            self.activity_log.log("univariate_payload_empty", "warning", message, {})
            raise ValueError(message)

        snapshot = self.get_analysis_context_snapshot()
        df = self._resolve_univariate_dataframe(snapshot, domain_filter)

        numeric_target = _to_numeric(df[target])
        total_rows = int(len(df))
        valid_count = int(numeric_target.notna().sum())
        nan_count = int(total_rows - valid_count)

        self.activity_log.log(
            "eda_target_coerced_numeric",
            "info",
            "Target convertido a numérico para EDA univariado.",
            {"target": target, "total_rows": total_rows, "valid_count": valid_count, "nan_count": nan_count},
        )
        self.activity_log.log(
            "eda_target_valid_count_computed",
            "info",
            "Conteo de target válido calculado.",
            {"target": target, "valid_count": valid_count, "nan_count": nan_count},
        )

        clean_target = numeric_target.dropna().astype(float)

        probability_min_samples = 3
        availability = _build_univariate_availability(target, valid_count, probability_min_samples=probability_min_samples)
        histogram_available = bool(availability["histogram"]["available"])
        boxplot_available = bool(availability["boxplot"]["available"])
        probability_available = bool(availability["probability"]["available"])

        for key, event_name, detail in [
            ("histogram", "univariate_histogram_available", "histograma"),
            ("boxplot", "univariate_boxplot_available", "boxplot general"),
            ("probability", "univariate_probability_available", "probability plot"),
        ]:
            if availability[key]["available"]:
                self.activity_log.log(event_name, "info", f"{detail.capitalize()} disponible.", {"target": target, "valid_count": valid_count})
            else:
                self.activity_log.log(
                    "univariate_component_unavailable",
                    "warning",
                    availability[key]["message"],
                    {"component": key, "target": target, "valid_count": valid_count},
                )

        if not (histogram_available or boxplot_available or probability_available):
            message = f"No hay valores numéricos válidos para target {target}."
            self.activity_log.log("eda_univariate_payload_empty", "warning", message, {"target": target})
            self.activity_log.log("univariate_payload_empty", "warning", message, {"target": target})
            raise ValueError(message)

        sorted_vals = sorted(clean_target.tolist())
        n = len(sorted_vals)
        qq_x: list[float] = []
        qq_y: list[float] = []
        probability_failed = False
        if probability_available:
            try:
                normal = statistics.NormalDist()
                qq_x = [normal.inv_cdf((idx + 0.5) / n) for idx in range(n)]
                qq_y = sorted_vals
                self.activity_log.log("probability_plot_rendered", "info", "Probability plot preparado.", {"n": n})
            except Exception as exc:
                probability_failed = True
                availability["probability"] = {
                    "available": False,
                    "message": f"Probability plot no disponible: error al calcular cuantiles ({exc}).",
                }
                self.activity_log.log("probability_plot_failed", "error", str(exc), {"n": n})
                self.activity_log.log(
                    "univariate_component_unavailable",
                    "warning",
                    availability["probability"]["message"],
                    {"component": "probability", "target": target, "valid_count": valid_count},
                )

        domain_payload, domain_col = self._build_univariate_domain_payload(df, target, snapshot, max_domain_categories=max_domain_categories)

        payload = {
            "target_values": clean_target.tolist(),
            "probplot_x": qq_x,
            "probplot_y": qq_y,
            "probability_failed": probability_failed,
            "domain_boxplot": domain_payload,
            "availability": availability,
            "diagnostics": {
                "target": target,
                "domain": domain_col or "",
                "total_rows": total_rows,
                "target_valid_count": valid_count,
                "target_nan_count": nan_count,
                "domain_valid_rows": domain_payload.get("valid_rows", 0),
                "domain_valid_categories": domain_payload.get("valid_categories", 0),
            },
        }
        self.activity_log.log("univariate_payload_built", "success", "Payload univariado construido.", payload["diagnostics"])
        self.activity_log.log(
            "eda_univariate_payload_prepared",
            "success",
            "Payload univariado preparado.",
            {
                "rows": len(clean_target),
                "domain_enabled": bool(domain_payload["enabled"]),
                "probability_failed": probability_failed,
            },
        )
        return payload

    def _resolve_univariate_dataframe(self, snapshot: dict[str, object], domain_filter: str | None):
        dataframe = self.current_dataset.dataframe
        requested_filter = (domain_filter or "").strip()
        active_domain_column = str(snapshot.get("active_domain_column") or "").strip()
        if requested_filter:
            if active_domain_column and active_domain_column in dataframe.columns:
                return dataframe[dataframe[active_domain_column].astype(str) == requested_filter]
            return dataframe.iloc[0:0]
        if str(snapshot["active_domain_filter"]).strip():
            return self._get_filtered_dataframe(snapshot)
        return dataframe

    def _build_univariate_domain_payload(
        self,
        dataframe,
        target: str,
        snapshot: dict[str, object],
        *,
        max_domain_categories: int,
    ) -> tuple[dict[str, object], str]:
        domain_payload = _empty_domain_payload()
        domain_col = str(snapshot.get("active_domain_column") or "").strip()
        configured_domain = self.variable_config.domain_column if self.variable_config is not None and self.variable_config.domain_column else ""
        if configured_domain and not domain_col:
            domain_payload["message"] = "Solo hay un dominio disponible tras filtros; se muestra boxplot global."
        if domain_col and domain_col in dataframe.columns:
            grouped: list[tuple[str, list[float]]] = []
            valid_rows = 0
            for label, subset in dataframe.groupby(domain_col, dropna=True):
                label_text = str(label).strip()
                if not label_text:
                    continue
                numeric_values = _to_numeric(subset[target]).dropna().astype(float).tolist()
                if not numeric_values:
                    continue
                grouped.append((label_text, numeric_values))
                valid_rows += len(numeric_values)

            grouped.sort(key=lambda item: len(item[1]), reverse=True)
            if max_domain_categories > 0 and len(grouped) > max_domain_categories:
                grouped = grouped[:max_domain_categories]
                domain_payload["message"] = f"Mostrando top {max_domain_categories} dominios por cantidad de muestras."
            if grouped:
                domain_payload = {
                    "enabled": len(grouped) > 1,
                    "labels": [label for label, _values in grouped],
                    "values": [values for _label, values in grouped],
                    "message": domain_payload.get("message", ""),
                    "valid_rows": int(valid_rows),
                    "valid_categories": len(grouped),
                }
                if len(grouped) <= 1:
                    domain_payload["message"] = "Solo hay un dominio disponible tras filtros; se muestra boxplot global."
        return domain_payload, domain_col

    def prepare_swath_data(self, bins: int = 20) -> dict[str, SwathSeries]:
        if self.current_dataset is None or self.variable_config is None:
            raise ValueError("No hay dataset/configuración suficiente para swath.")

        dataframe = self.current_dataset.dataframe
        target_col = self.variable_config.target_column
        if not target_col or target_col not in dataframe.columns:
            raise ValueError(f"Target no válido para swath: '{target_col}'.")

        payload = {
            "x": compute_swath_series(dataframe, self.variable_config.x_column, target_col, bins=bins),
            "y": compute_swath_series(dataframe, self.variable_config.y_column, target_col, bins=bins),
            "z": compute_swath_series(dataframe, self.variable_config.z_column, target_col, bins=bins),
        }
        self.activity_log.log("swath_payload_prepared", "success", "Series swath preparadas.", {"bins": bins, "target": target_col})
        return payload

    def build_eda_summary(self, use_effective_target: bool = False) -> str:
        if self.current_dataset is None:
            return "No hay dataset cargado para EDA."
        base = (
            "MÓDULO EDA\n"
            "----------\n"
            "Subsecciones: Resumen | Univariado\n"
            f"Filas: {self.current_dataset.row_count} | Columnas: {self.current_dataset.column_count}\n"
        )
        if self.variable_config is None:
            return base + "Selecciona X/Y/Z/target para habilitar estadísticas del target."
        target, _ = self._resolve_eda_target_column(use_effective_target=use_effective_target, require_numeric=False)
        df = self.current_dataset.dataframe
        if target not in df.columns or not _is_numeric_dtype(df[target]):
            return base + "Target no numérico: estadísticas limitadas."
        stats = self._target_statistics(use_effective_target=use_effective_target)
        return base + f"Target {target}: válidos={stats['valid_count']} | nulos={stats['null_pct']:.2f}% | mean={stats['mean']:.4g}"

    def _target_statistics(self, use_effective_target: bool = False) -> dict[str, float]:
        target, message = self._resolve_eda_target_column(use_effective_target=use_effective_target, require_numeric=True)
        if message:
            raise ValueError(message)
        df = self._get_filtered_dataframe()
        total = len(df)
        clean = _to_numeric(df[target]).dropna().astype(float)
        return _compute_target_statistics(clean, total)

    def get_target_statistics_table(self, use_effective_target: bool = False) -> list[tuple[str, str]]:
        if self.current_dataset is None:
            return []
        target, message = self._resolve_eda_target_column(use_effective_target=use_effective_target, require_numeric=True)
        if message:
            return []
        df = self.current_dataset.dataframe
        if target not in df.columns or not _is_numeric_dtype(df[target]):
            return []

        stats = self._target_statistics(use_effective_target=use_effective_target)
        return [
            ("dataset", self.current_dataset.file_name),
            ("samples", str(self.current_dataset.row_count)),
            ("columns", str(self.current_dataset.column_count)),
            ("target", target),
            ("valid_count", str(int(stats["valid_count"]))),
            ("null_pct", f"{stats['null_pct']:.3g}"),
            ("mean", f"{stats['mean']:.5g}"),
            ("std", f"{stats['std']:.5g}"),
            ("cv", f"{stats['cv']:.5g}"),
            ("min", f"{stats['min']:.5g}"),
            ("p10", f"{stats['p10']:.5g}"),
            ("p25", f"{stats['p25']:.5g}"),
            ("p50", f"{stats['p50']:.5g}"),
            ("p75", f"{stats['p75']:.5g}"),
            ("p90", f"{stats['p90']:.5g}"),
            ("max", f"{stats['max']:.5g}"),
            ("skewness", f"{stats['skewness']:.5g}"),
            ("kurtosis", f"{stats['kurtosis']:.5g}"),
        ]

    def _resolve_eda_target_column(self, use_effective_target: bool, require_numeric: bool) -> tuple[str, str]:
        snapshot = self.get_analysis_context_snapshot()
        readiness_message = self._resolve_dataset_config_readiness_error(snapshot, context="EDA")
        if readiness_message:
            return "", readiness_message

        target = str(snapshot["resolved_target_column"] if use_effective_target else snapshot["base_target_column"])
        if not target or target not in self.current_dataset.dataframe.columns:
            return target, f"Target no válido para EDA univariado: '{target}'."
        if require_numeric:
            series = self.current_dataset.dataframe[target]
            if not _is_numeric_dtype(series) and not _to_numeric(series).notna().any():
                return target, f"Target no numérico para EDA univariado: '{target}'."
        return target, ""

    def _resolve_dataset_config_readiness_error(self, snapshot: dict[str, object], *, context: str) -> str:
        if snapshot["readiness"] == "blocked" and snapshot["blocking_reason"] in {"missing_dataset", "missing_variable_config"}:
            return f"No hay dataset/configuración suficiente para {context}."
        if self.current_dataset is None or self.variable_config is None:
            return f"No hay dataset/configuración suficiente para {context}."
        return ""

    def get_summary_cards(self) -> dict[str, str]:
        if self.current_dataset is None:
            return {"Dataset": "No cargado", "Muestras": "0", "Columnas": "0", "Target": "No definido", "Estado": "Pendiente", "Dominio": "No definido"}

        context = self.get_analysis_context_snapshot()
        workflow = self.get_workflow_readiness()
        target = str(context["resolved_target_column"] or "No definido")
        return {
            "Dataset": self.current_dataset.file_name,
            "Muestras": str(self.current_dataset.row_count),
            "Columnas": str(self.current_dataset.column_count),
            "Target": target,
            "Estado": "Listo" if bool(workflow["stages"]["eda"]["ready"]) else "Configurar variables",
            "Dominio": self.workflow_state.active_domain,
        }

    def get_variography_session(self) -> VariographySession:
        return self.variography_service.get_session()

    def compute_experimental_variography(self, params: dict[str, object]) -> VariographyComputeResponse:
        return self.variography_service.compute(params)

    def estimate_variography_defaults(
        self,
        *,
        n_lags: int = 16,
        context_snapshot: dict[str, object] | None = None,
        dataframe=None,
    ) -> dict[str, float | int]:
        """Estimate conservative, data-driven variography defaults.

        Keeps a safe fallback contract when context/data are not ready.
        """
        safe_n_lags = max(int(n_lags or 16), 4)
        fallback = {
            "lag_distance": 10.0,
            "max_distance": 160.0,
            "lag_tolerance": 5.0,
            "n_lags": safe_n_lags,
            "effective_rows": 0,
            "spatial_extent": 0.0,
        }
        snapshot = context_snapshot or self.get_analysis_context_snapshot()
        df = dataframe if dataframe is not None else self._get_filtered_dataframe(snapshot)
        if df is None or self.variable_config is None or df.empty:
            return fallback
        columns = [self.variable_config.x_column, self.variable_config.y_column, self.variable_config.z_column]
        if any((not col) or (col not in df.columns) for col in columns):
            return fallback
        try:
            clean = df[columns].dropna()
            if clean.empty:
                return fallback
            ranges: list[float] = []
            for col in columns:
                series = _to_numeric(clean[col])
                col_min = float(series.min())
                col_max = float(series.max())
                if not math.isfinite(col_min) or not math.isfinite(col_max):
                    return fallback
                ranges.append(max(col_max - col_min, 0.0))
            spatial_extent = math.sqrt(sum(value**2 for value in ranges))
            if not math.isfinite(spatial_extent) or spatial_extent <= 0:
                return fallback
            # Conservative, reproducible defaults:
            # - max_distance at half spatial extent
            # - lag_distance distributed across n_lags
            max_distance = max(spatial_extent * 0.5, spatial_extent / safe_n_lags, 1e-6)
            lag_distance = max(max_distance / safe_n_lags, 1e-6)
            lag_tolerance = max(lag_distance * 0.5, 1e-6)
            return {
                "lag_distance": float(lag_distance),
                "max_distance": float(max_distance),
                "lag_tolerance": float(lag_tolerance),
                "n_lags": safe_n_lags,
                "effective_rows": int(len(clean)),
                "spatial_extent": float(spatial_extent),
            }
        except Exception:
            return fallback

    def update_repository(self) -> RepoUpdateResult:
        return self.repository_update_service.update_repository()

    def dataframe_write_in_progress(self) -> bool:
        return bool(getattr(self, "_dataframe_write_in_progress", False))

    def export_activity_log(self, destination_path: str) -> str:
        exported = self.activity_log.export_log(destination_path)
        self.activity_log.log("export_log_requested", "success", "Log exportado correctamente.", {"destination": str(exported)})
        return str(exported)

    def module_not_implemented(self, module_name: str) -> str:
        message = f"{module_name}: etapa aún no implementada. Esta acción fue registrada."
        self.activity_log.log("placeholder_module_clicked", "info", message, {"module": module_name})
        return message


    def variogram_placeholder(self) -> str:
        return self.module_not_implemented("Variografía")

    def kriging_placeholder(self) -> str:
        return self.module_not_implemented("Kriging")

    def sgs_placeholder(self) -> str:
        return self.module_not_implemented("Simulación")

    def visualization_placeholder(self) -> str:
        return self.module_not_implemented("Espacial")

    def _build_dataset_summary(self, dataset: DatasetModel) -> str:
        dtypes = dataset.dataframe.dtypes.astype(str).to_dict()
        dtypes_text = "\n".join(f"• {k}: {v}" for k, v in dtypes.items())
        preview = dataset.preview_as_text()
        return (
            "ETAPA DATOS\n"
            "-----------\n"
            f"Archivo: {dataset.file_name}\n"
            f"Filas: {dataset.row_count} | Columnas: {dataset.column_count}\n"
            "Tipos de datos:\n"
            f"{dtypes_text}\n\n"
            "Preview:\n"
            f"{preview}"
        )
