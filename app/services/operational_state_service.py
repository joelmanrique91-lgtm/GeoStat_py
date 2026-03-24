"""Typed operational-state builder service for GeostatService facade."""

from __future__ import annotations

from pandas.api.types import is_numeric_dtype

from app.models.operational_state import (
    AnalysisContextState,
    CutoffState,
    DomainState,
    GeostatOperationalState,
    StageReadiness,
    VariableSelectionState,
    WorkflowReadinessState,
)

DOMAIN_ESTIMATION_COLUMN = "domain_estimation"
BLOCKING_REASON_HINTS = {
    "missing_dataset": "Carga un CSV para continuar.",
    "missing_variable_config": "Configura y confirma X/Y/Z/target.",
    "missing_resolved_target_column": "Revisa target/Control de Outliers y confirma la variable activa.",
    "missing_target": "Configura y confirma una variable objetivo válida para variografía.",
    "missing_spatial_columns": "Reconfigura columnas espaciales X/Y/Z.",
    "missing_domain_column": "Aplica una definición de dominios para habilitar esta etapa.",
    "non_numeric_target_for_domain_stats": "Usa un target numérico para estadísticas de dominios.",
    "invalid_active_domain_filter_column": "Limpia o corrige el filtro de dominio activo.",
    "insufficient_data": "Datos insuficientes para variografía. Amplía muestra o ajusta filtros/dominio.",
    "low_data_after_domain_filter": "El filtro de dominio deja pocos datos; revisa la selección activa.",
}


def _resolve_active_domain_column(dataframe, configured_domain_column: str) -> str:
    candidate = str(configured_domain_column or "").strip()
    if candidate and candidate in dataframe.columns:
        return candidate
    if DOMAIN_ESTIMATION_COLUMN in dataframe.columns:
        return DOMAIN_ESTIMATION_COLUMN
    return ""


def _default_domain_ui_filters() -> dict[str, str]:
    return {"lithology": "", "alteration": "", "mine": ""}


class OperationalStateService:
    """Centralizes snapshot/readiness/cutoff/domain typed-state construction."""

    def __init__(self, host_service) -> None:
        self.host = host_service

    def build_analysis_context_state(self) -> AnalysisContextState:
        base_target_column = self.host.variable_config.target_column if self.host.variable_config else ""
        effective_target_column = self.host._get_effective_target_column()
        resolved_target_column = effective_target_column or base_target_column
        active_domain_column = ""
        active_domain_filter = ""
        if self.host.current_dataset is not None:
            if self.host._domain_filter_context_enabled:
                active_domain_column = _resolve_active_domain_column(
                    self.host.current_dataset.dataframe,
                    self.host.variable_config.domain_column if self.host.variable_config is not None else "",
                )
            active_domain_filter = str(self.host.workflow_state.active_domain_filter or "").strip()
            if active_domain_filter and not active_domain_column:
                active_domain_filter = ""
                self.host.workflow_state.active_domain_filter = ""
            if active_domain_filter and active_domain_column:
                valid_values = {
                    str(value).strip()
                    for value in self.host.current_dataset.dataframe[active_domain_column].dropna().tolist()
                    if str(value).strip()
                }
                if active_domain_filter not in valid_values:
                    active_domain_filter = ""
                    self.host.workflow_state.active_domain_filter = ""

        readiness = "ready"
        blocking_reason = ""
        if self.host.current_dataset is None:
            readiness = "blocked"
            blocking_reason = "missing_dataset"
        elif self.host.variable_config is None:
            readiness = "blocked"
            blocking_reason = "missing_variable_config"
        elif not resolved_target_column or resolved_target_column not in self.host.current_dataset.dataframe.columns:
            readiness = "blocked"
            blocking_reason = "missing_resolved_target_column"

        resolved_target_type = "unknown"
        if readiness == "ready" and self.host.current_dataset is not None and resolved_target_column in self.host.current_dataset.dataframe.columns:
            resolved_target_type = "numeric" if is_numeric_dtype(self.host.current_dataset.dataframe[resolved_target_column]) else "categorical"

        dataset_name = self.host.current_dataset.file_name if self.host.current_dataset is not None else "No cargado"
        return AnalysisContextState(
            dataset_name=dataset_name,
            base_target_column=base_target_column,
            effective_target_column=effective_target_column,
            resolved_target_column=resolved_target_column,
            resolved_target_type=resolved_target_type,
            active_domain_column=active_domain_column,
            active_domain_filter=active_domain_filter,
            current_step=self.host.workflow_state.current_step,
            readiness=readiness,
            blocking_reason=blocking_reason,
        )

    def build_stage_hint(self, stage: StageReadiness) -> str:
        if stage.ready:
            if stage.warnings:
                return "Advertencia: hay filtros activos que reducen resultados."
            return "Etapa lista."
        if not stage.blocking_reasons:
            return "Etapa no lista."
        return BLOCKING_REASON_HINTS.get(stage.blocking_reasons[0], "Completa la configuración requerida para desbloquear esta etapa.")

    def build_workflow_readiness_state(self) -> WorkflowReadinessState:
        snapshot = self.build_analysis_context_state()
        has_dataset = bool(self.host.current_dataset is not None)
        has_variable_config = bool(self.host.variable_config is not None)
        dataframe = self.host.current_dataset.dataframe if self.host.current_dataset is not None else None
        resolved_target_exists = bool(dataframe is not None and snapshot.resolved_target_column and snapshot.resolved_target_column in dataframe.columns)

        def _stage(ready: bool, blocking_reasons: list[str], warnings: list[str] | None = None) -> StageReadiness:
            stage = StageReadiness(
                ready=bool(ready),
                blocking_reasons=tuple(blocking_reasons),
                warnings=tuple(warnings or []),
            )
            return StageReadiness(
                ready=stage.ready,
                blocking_reasons=stage.blocking_reasons,
                warnings=stage.warnings,
                hint=self.build_stage_hint(stage),
            )

        data_reasons: list[str] = []
        if not has_dataset:
            data_reasons.append("missing_dataset")

        eda_reasons: list[str] = []
        if not has_dataset:
            eda_reasons.append("missing_dataset")
        if not has_variable_config:
            eda_reasons.append("missing_variable_config")
        if has_dataset and has_variable_config and not resolved_target_exists:
            eda_reasons.append("missing_resolved_target_column")

        cutoffs_reasons: list[str] = []
        if not has_dataset:
            cutoffs_reasons.append("missing_dataset")
        if not has_variable_config:
            cutoffs_reasons.append("missing_variable_config")
        if has_dataset and has_variable_config and self.host.variable_config.target_column not in self.host.current_dataset.dataframe.columns:
            cutoffs_reasons.append("missing_base_target_column")

        spatial_reasons: list[str] = []
        if not has_dataset:
            spatial_reasons.append("missing_dataset")
        if not has_variable_config:
            spatial_reasons.append("missing_variable_config")
        if has_dataset and has_variable_config:
            missing_xyz = [
                col
                for col in [self.host.variable_config.x_column, self.host.variable_config.y_column, self.host.variable_config.z_column]
                if col not in self.host.current_dataset.dataframe.columns
            ]
            if missing_xyz:
                spatial_reasons.append("missing_spatial_columns")
        if has_dataset and has_variable_config and not resolved_target_exists:
            spatial_reasons.append("missing_resolved_target_column")

        domains_reasons: list[str] = []
        domain_warnings: list[str] = []
        variography_reasons: list[str] = []
        variography_warnings: list[str] = []
        if not has_dataset:
            variography_reasons.append("missing_dataset")
        if not has_variable_config:
            variography_reasons.append("missing_variable_config")
        if has_dataset and has_variable_config:
            missing_xyz = [
                col
                for col in [self.host.variable_config.x_column, self.host.variable_config.y_column, self.host.variable_config.z_column]
                if col not in self.host.current_dataset.dataframe.columns
            ]
            if missing_xyz:
                variography_reasons.append("missing_spatial_columns")
        if has_dataset and has_variable_config and not resolved_target_exists:
            variography_reasons.append("missing_target")
        if has_dataset and has_variable_config and resolved_target_exists:
            filtered_for_variography = self.host._get_filtered_dataframe(snapshot.as_dict())
            if filtered_for_variography is None:
                variography_reasons.append("missing_dataset")
            else:
                active_rows = int(len(filtered_for_variography))
                if active_rows < 30:
                    variography_warnings.append("insufficient_data")
                if snapshot.active_domain_filter.strip() and active_rows < 50:
                    variography_warnings.append("low_data_after_domain_filter")

        return WorkflowReadinessState(
            current_step=self.host.workflow_state.current_step,
            analysis_context=snapshot,
            has_dataset=has_dataset,
            has_variable_config=has_variable_config,
            stages={
                "data": _stage(not data_reasons, data_reasons),
                "eda": _stage(not eda_reasons, eda_reasons),
                "cutoffs": _stage(not cutoffs_reasons, cutoffs_reasons),
                "spatial": _stage(not spatial_reasons, spatial_reasons),
                "domains": _stage(not domains_reasons, domains_reasons, warnings=domain_warnings),
                "variography": _stage(not variography_reasons, variography_reasons, warnings=variography_warnings),
            },
        )

    def build_cutoff_state(self) -> CutoffState:
        snapshot = self.host.get_analysis_context_snapshot()
        default_target = str(snapshot["base_target_column"])
        return CutoffState(
            enabled=bool(self.host.workflow_state.cutoffs_enabled),
            target_column=self.host.workflow_state.cutoff_target_column or default_target,
            limits=tuple(float(v) for v in self.host.workflow_state.cutoff_limits),
            labels=tuple(self.host.workflow_state.cutoff_labels),
            output_column=self.host.workflow_state.cutoff_output_column,
            effective_target_column=str(snapshot["resolved_target_column"]),
            dynamic_enabled=bool(self.host.workflow_state.dynamic_cutoff_enabled),
            dynamic_target_column=self.host.workflow_state.dynamic_cutoff_target_column or default_target,
            dynamic_mode=self.host.workflow_state.dynamic_cutoff_mode,
            dynamic_percent=float(self.host.workflow_state.dynamic_cutoff_percent),
            dynamic_cutoff_value=float(self.host.workflow_state.dynamic_cutoff_value),
            dynamic_output_column=self.host.workflow_state.dynamic_cutoff_output_column,
            dynamic_category_column=self.host.workflow_state.dynamic_cutoff_category_column,
        )

    def build_domain_state(self) -> DomainState:
        snapshot_payload = self.host.get_analysis_context_snapshot()
        return DomainState(
            ordered_layers=(),
            active_layers=(),
            output_column="",
            min_samples=1,
            include_missing=False,
            effective_target_column=str(snapshot_payload["resolved_target_column"]),
            capping_confirmed=bool(self.host.has_confirmed_dynamic_capping()),
            domain_definition={},
            active_domain_filter="",
            domain_estimation_values=(),
            domains_ready=True,
            ui_filters=_default_domain_ui_filters(),
            filter_columns=_default_domain_ui_filters(),
            assignment_history=(),
        )

    def build_operational_state(self) -> GeostatOperationalState:
        analysis = self.build_analysis_context_state()
        readiness = self.build_workflow_readiness_state()
        cutoff = self.build_cutoff_state()
        domain = self.build_domain_state()
        config = self.host.variable_config
        selection = VariableSelectionState(
            x_column=config.x_column if config is not None else "",
            y_column=config.y_column if config is not None else "",
            z_column=config.z_column if config is not None else "",
            target_column=config.target_column if config is not None else "",
            hole_id_column=config.hole_id_column if config is not None and config.hole_id_column else "",
            domain_column=config.domain_column if config is not None and config.domain_column else "",
        )
        return GeostatOperationalState(
            analysis=analysis,
            readiness=readiness,
            cutoff=cutoff,
            domain=domain,
            selection=selection,
        )
