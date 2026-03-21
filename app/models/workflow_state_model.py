"""Model for workflow navigation state."""

from dataclasses import dataclass, field


@dataclass
class WorkflowStateModel:
    """Tracks current workflow step and context labels."""

    current_step: str = "Datos"
    active_domain: str = "No definido"
    active_support: str = "No definido"
    cutoffs_enabled: bool = False
    cutoff_target_column: str = ""
    cutoff_limits: list[float] = field(default_factory=list)
    cutoff_labels: list[str] = field(default_factory=list)
    cutoff_output_column: str = ""
    effective_target_column: str = ""
    dynamic_cutoff_enabled: bool = False
    dynamic_cutoff_target_column: str = ""
    dynamic_cutoff_mode: str = "percentile"
    dynamic_cutoff_percent: float = 95.0
    dynamic_cutoff_value: float = 0.0
    dynamic_cutoff_output_column: str = ""
    dynamic_cutoff_category_column: str = ""
    domain_layers_order: list[str] = field(default_factory=list)
    domain_active_layers: list[str] = field(default_factory=list)
    domain_output_column: str = ""
    domain_min_samples: int = 1
    domain_include_missing: bool = False
    domain_definition: dict = field(default_factory=dict)
    active_domain_filter: str = ""
