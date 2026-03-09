"""Model for workflow navigation state."""

from dataclasses import dataclass


@dataclass
class WorkflowStateModel:
    """Tracks current workflow step and context labels."""

    current_step: str = "Datos"
    active_domain: str = "No definido"
    active_support: str = "No definido"
