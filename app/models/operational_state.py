"""Typed operational state contracts for global workflow orchestration."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal

StageKey = Literal["data", "eda", "cutoffs", "spatial", "domains", "variography"]


@dataclass(frozen=True)
class StageReadiness:
    ready: bool
    blocking_reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    hint: str = ""
    status: str = "incomplete"

    def as_dict(self) -> dict[str, object]:
        return {
            "ready": bool(self.ready),
            "blocking_reasons": list(self.blocking_reasons),
            "warnings": list(self.warnings),
            "hint": self.hint,
            "status": self.status,
        }


@dataclass(frozen=True)
class AnalysisContextState:
    dataset_name: str
    base_target_column: str
    effective_target_column: str
    resolved_target_column: str
    resolved_target_type: str
    active_domain_column: str
    active_domain_filter: str
    current_step: str
    readiness: str
    blocking_reason: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class WorkflowReadinessState:
    current_step: str
    analysis_context: AnalysisContextState
    has_dataset: bool
    has_variable_config: bool
    stages: dict[StageKey, StageReadiness]

    def stage(self, key: StageKey) -> StageReadiness:
        return self.stages[key]

    def as_dict(self) -> dict[str, object]:
        return {
            "current_step": self.current_step,
            "analysis_context": self.analysis_context.as_dict(),
            "base_state": {
                "has_dataset": self.has_dataset,
                "has_variable_config": self.has_variable_config,
                "resolved_target_column": self.analysis_context.resolved_target_column,
                "resolved_target_type": self.analysis_context.resolved_target_type,
                "active_domain_column": self.analysis_context.active_domain_column,
                "active_domain_filter": self.analysis_context.active_domain_filter,
            },
            "stages": {key: stage.as_dict() for key, stage in self.stages.items()},
        }


@dataclass(frozen=True)
class CutoffState:
    enabled: bool
    target_column: str
    source_column: str
    limits: tuple[float, ...]
    labels: tuple[str, ...]
    output_column: str
    effective_target_column: str
    dynamic_enabled: bool
    dynamic_target_column: str
    dynamic_source_column: str
    dynamic_mode: str
    dynamic_percent: float
    dynamic_cutoff_value: float
    dynamic_output_column: str
    dynamic_category_column: str

    def as_dict(self) -> dict[str, object]:
        return {
            "enabled": self.enabled,
            "target_column": self.target_column,
            "source_column": self.source_column,
            "limits": list(self.limits),
            "labels": list(self.labels),
            "output_column": self.output_column,
            "effective_target_column": self.effective_target_column,
            "dynamic_enabled": self.dynamic_enabled,
            "dynamic_target_column": self.dynamic_target_column,
            "dynamic_source_column": self.dynamic_source_column,
            "dynamic_mode": self.dynamic_mode,
            "dynamic_percent": self.dynamic_percent,
            "dynamic_cutoff_value": self.dynamic_cutoff_value,
            "dynamic_output_column": self.dynamic_output_column,
            "dynamic_category_column": self.dynamic_category_column,
        }


@dataclass(frozen=True)
class DomainState:
    ordered_layers: tuple[str, ...] = ()
    active_layers: tuple[str, ...] = ()
    output_column: str = ""
    min_samples: int = 1
    include_missing: bool = False
    effective_target_column: str = ""
    capping_confirmed: bool = False
    domain_definition: dict[str, object] = field(default_factory=dict)
    active_domain_filter: str = ""
    domain_estimation_values: tuple[str, ...] = ()
    domains_ready: bool = True
    ui_filters: dict[str, str] = field(default_factory=dict)
    filter_columns: dict[str, str] = field(default_factory=dict)
    assignment_history: tuple[dict[str, object], ...] = ()

    def as_dict(self) -> dict[str, object]:
        return {
            "ordered_layers": list(self.ordered_layers),
            "active_layers": list(self.active_layers),
            "output_column": self.output_column,
            "min_samples": self.min_samples,
            "include_missing": self.include_missing,
            "effective_target_column": self.effective_target_column,
            "capping_confirmed": self.capping_confirmed,
            "domain_definition": dict(self.domain_definition),
            "active_domain_filter": self.active_domain_filter,
            "domain_estimation_values": list(self.domain_estimation_values),
            "domains_ready": self.domains_ready,
            "ui_filters": dict(self.ui_filters),
            "filter_columns": dict(self.filter_columns),
            "assignment_history": list(self.assignment_history),
        }


@dataclass(frozen=True)
class VariableSelectionState:
    x_column: str = ""
    y_column: str = ""
    z_column: str = ""
    target_column: str = ""
    hole_id_column: str = ""
    domain_column: str = ""


@dataclass(frozen=True)
class GeostatOperationalState:
    analysis: AnalysisContextState
    readiness: WorkflowReadinessState
    cutoff: CutoffState
    domain: DomainState
    selection: VariableSelectionState

    def as_dict(self) -> dict[str, object]:
        return {
            "analysis": self.analysis.as_dict(),
            "readiness": self.readiness.as_dict(),
            "cutoff": self.cutoff.as_dict(),
            "domain": self.domain.as_dict(),
            "selection": asdict(self.selection),
        }
