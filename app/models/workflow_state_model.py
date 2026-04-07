"""Model for workflow navigation state."""

from dataclasses import dataclass, field


@dataclass
class WorkflowStateModel:
    """Tracks persisted workflow internals.

    This model stores mutable internal state. Public consumers should prefer
    service-level contracts such as `get_analysis_context_snapshot()` and
    `get_workflow_readiness()` for read access.
    """

    current_step: str = "Datos"
    active_domain: str = "No definido"
    active_support: str = "No definido"
    cutoffs_enabled: bool = False
    cutoff_target_column: str = ""
    cutoff_limits: list[float] = field(default_factory=list)
    cutoff_labels: list[str] = field(default_factory=list)
    cutoff_output_column: str = ""
    cutoff_source_column: str = ""
    effective_target_column: str = ""
    dynamic_cutoff_enabled: bool = False
    dynamic_cutoff_target_column: str = ""
    dynamic_cutoff_mode: str = "percentile"
    dynamic_cutoff_percent: float = 95.0
    dynamic_cutoff_value: float = 0.0
    dynamic_cutoff_output_column: str = ""
    dynamic_cutoff_category_column: str = ""
    dynamic_cutoff_source_column: str = ""
    domain_layers_order: list[str] = field(default_factory=list)
    domain_active_layers: list[str] = field(default_factory=list)
    domain_output_column: str = ""
    domain_min_samples: int = 1
    domain_include_missing: bool = False
    domain_definition: dict = field(default_factory=dict)
    active_domain_filter: str = ""
    domain_ui_filters: dict[str, str] = field(default_factory=lambda: {"lithology": "", "alteration": "", "mine": ""})
    domain_filter_columns: dict[str, str] = field(default_factory=lambda: {"lithology": "", "alteration": "", "mine": ""})
    domain_assignment_history: list[dict[str, object]] = field(default_factory=list)
    domain_assignment_sequence: int = 0
    support_composite_enabled: bool = False
    support_composite_length: float = 0.0
    support_source_target_column: str = ""
    support_output_target_column: str = ""
    support_pre_count: int = 0
    support_post_count: int = 0
    support_confirmed: bool = False
    allow_variography_without_domain: bool = False
