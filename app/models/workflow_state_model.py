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
