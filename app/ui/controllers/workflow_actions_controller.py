"""Workflow action controller: business-facing operations for HomePanel."""

from __future__ import annotations

from dataclasses import dataclass

from app.services.geostat_service import GeostatService


@dataclass(frozen=True)
class WorkflowActionResult:
    success: bool
    message: str
    payload: dict[str, object]


class WorkflowActionsController:
    def __init__(self, service: GeostatService) -> None:
        self.service = service

    def apply_variable_config(
        self,
        *,
        x_column: str,
        y_column: str,
        z_column: str,
        target_column: str,
        hole_id_column: str | None,
        selected_domain: str | None,
    ) -> WorkflowActionResult:
        result = self.service.set_variable_config(x_column, y_column, z_column, target_column, hole_id_column, selected_domain)
        return WorkflowActionResult(result.success, result.message, {"domain": selected_domain or ""})

    def apply_domain_filter(self, domain_value: str) -> WorkflowActionResult:
        result = self.service.set_active_domain(domain_value)
        return WorkflowActionResult(result.success, result.message, {"domain_filter": domain_value})

    def confirm_domain_assignment(self, selected_domain: str) -> WorkflowActionResult:
        result = self.service.confirm_domain_assignment(selected_domain)
        return WorkflowActionResult(result.success, result.message, {"confirmed_domain": selected_domain})

    def apply_domains(self, *, variable_base: str, domains: dict[str, list[str]]) -> WorkflowActionResult:
        if not domains:
            return WorkflowActionResult(False, "Define al menos un dominio para comenzar", {})
        definition = {"variable_base": variable_base.strip(), "domains": dict(domains)}
        result = self.service.apply_domain_definition(definition)
        return WorkflowActionResult(result.success, result.message, {"variable_base": variable_base.strip(), "domain_count": len(domains)})

    def toggle_variography_bypass(self, *, enabled: bool, reason: str) -> WorkflowActionResult:
        result = self.service.set_variography_domain_bypass(enabled, reason=reason if enabled else "")
        return WorkflowActionResult(result.success, result.message, {"enabled": enabled, "reason": reason if enabled else ""})
