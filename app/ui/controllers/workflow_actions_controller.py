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

    def apply_manual_cutoff(self, *, enabled: bool, target_column: str, limits_text: str, output_column: str | None) -> WorkflowActionResult:
        result = self.service.apply_cutoffs(enabled=enabled, target_column=target_column, limits_text=limits_text, output_column=output_column)
        return WorkflowActionResult(result.success, result.message, {"target_column": target_column, "output_column": output_column or ""})

    def apply_dynamic_cutoff(
        self,
        *,
        enabled: bool,
        target_column: str,
        mode: str,
        slider_percent: float,
        output_column: str | None,
        keep_category_column: bool,
    ) -> WorkflowActionResult:
        result = self.service.apply_dynamic_cutoff(
            enabled=enabled,
            target_column=target_column,
            mode=mode,
            slider_percent=slider_percent,
            output_column=output_column,
            keep_category_column=keep_category_column,
        )
        return WorkflowActionResult(result.success, result.message, {"cutoff_value": float(result.cutoff_value), "target_column": target_column})

    def apply_support_composite(self, *, composite_length: float, target_column: str, output_column: str | None) -> WorkflowActionResult:
        result = self.service.apply_basic_compositing(composite_length=composite_length, target_column=target_column, output_column=output_column)
        payload = {"support_state": self.service.get_support_state()} if result.success else {}
        return WorkflowActionResult(result.success, result.message, payload)

    @staticmethod
    def _series_p90(values: list[float]) -> float | None:
        if not values:
            return None
        ordered = sorted(float(v) for v in values)
        rank = max(0, min(len(ordered) - 1, int(round(0.9 * (len(ordered) - 1)))))
        return float(ordered[rank])

    @staticmethod
    def _series_cv(values: list[float]) -> float | None:
        if not values:
            return None
        mean_val = sum(values) / len(values)
        if abs(mean_val) < 1e-12:
            return None
        variance = sum((v - mean_val) ** 2 for v in values) / len(values)
        return float((variance**0.5) / abs(mean_val))

    @staticmethod
    def _delta(current: float | None, base: float | None, *, percent: bool = False) -> str:
        if current is None or base is None:
            return "-"
        d = current - base
        return f"{d * 100:+.2f}%" if percent else f"{d:+.4g}"

    def build_cutoff_preview_payload(self, *, target_column: str, mode: str, slider_percent: float) -> dict[str, object]:
        preview = self.service.prepare_dynamic_cutoff_preview(target_column, mode, slider_percent)
        original = [float(v) for v in preview.get("values", [])]
        capped = [float(v) for v in preview.get("capped_values", [])]
        mean_original = (sum(original) / len(original)) if original else None
        mean_capped = (sum(capped) / len(capped)) if capped else None
        p90_original = self._series_p90(original)
        p90_capped = self._series_p90(capped)
        cv_original = self._series_cv(original)
        cv_capped = self._series_cv(capped)
        affected_pct = float(preview.get("affected_pct", 0.0))
        if affected_pct > 20.0:
            decision = "El ajuste afecta una proporción alta de muestras; revisar antes de aplicar."
        elif (cv_original is not None and cv_capped is not None and cv_capped < cv_original) and affected_pct <= 20.0:
            decision = "El ajuste propuesto mejora estabilidad con intervención acotada."
        else:
            decision = "El ajuste reduce la cola extrema con impacto moderado sobre la distribución."
        return {
            "preview": preview,
            "metrics": {
                "affected_pct": f"{affected_pct:.2f}%",
                "delta_cv": self._delta(cv_capped, cv_original, percent=True),
                "delta_mean": self._delta(mean_capped, mean_original),
                "delta_p90": self._delta(p90_capped, p90_original),
                "max_before_after": f"{float(preview.get('max_original', 0.0)):.6g} → {float(preview.get('max_truncated', 0.0)):.6g}",
                "decision_message": decision,
            },
        }
