"""Workflow coordinator that centralizes desktop step-transition decisions."""

from __future__ import annotations

from dataclasses import dataclass

from app.services.geostat_service import GeostatService


@dataclass(frozen=True)
class StepTransitionResult:
    changed: bool
    message: str
    current_step: str


class WorkflowCoordinatorService:
    """Keeps workflow transition rules out of UI widgets."""

    def __init__(self, service: GeostatService) -> None:
        self.service = service

    def change_step(self, requested_step: str) -> StepTransitionResult:
        current_step = str(self.service.workflow_state.current_step)
        target = str(requested_step)
        if current_step == target:
            return StepTransitionResult(changed=False, message=f"Ya estás en la etapa {target}.", current_step=current_step)
        message = self.service.set_workflow_step(target)
        return StepTransitionResult(changed=True, message=message, current_step=target)
