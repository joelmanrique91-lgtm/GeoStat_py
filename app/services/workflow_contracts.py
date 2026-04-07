"""Shared workflow/domain contract constants and helper defaults."""

from __future__ import annotations

DOMAIN_ESTIMATION_COLUMN = "domain_estimation"
DOMAINS_MODULE_DISABLED_REASON = "domains_module_disabled"
DOMAINS_MODULE_DISABLED_MESSAGE = "Dominios requiere configuración previa de datos y soporte/compositado."

BLOCKING_REASON_HINTS = {
    "missing_dataset": "Carga un CSV para continuar.",
    "missing_variable_config": "Configura y confirma X/Y/Z/target.",
    "missing_resolved_target_column": "Revisa target/Control de Outliers y confirma la variable activa.",
    "missing_target": "Configura y confirma una variable objetivo válida para variografía.",
    "missing_spatial_columns": "Reconfigura columnas espaciales X/Y/Z.",
    "missing_support_confirmation": "Confirma soporte/compositado en la etapa Soporte.",
    "missing_domain_confirmation": "Define y confirma un dominio estacionario en la etapa Dominios.",
    "domain_bypass_active": "Variografía habilitada en modo excepcional sin dominios confirmados.",
    "missing_domain_column": "Aplica una definición de dominios para habilitar esta etapa.",
    "non_numeric_target_for_domain_stats": "Usa un target numérico para estadísticas de dominios.",
    "invalid_active_domain_filter_column": "Limpia o corrige el filtro de dominio activo.",
    "insufficient_data": "Datos insuficientes para variografía. Amplía muestra o ajusta filtros/dominio.",
    "low_data_after_domain_filter": "El filtro de dominio deja pocos datos; revisa la selección activa.",
    "domain_not_defined_exploratory": "No hay dominio estacionario activo: la lectura es exploratoria.",
    "support_fallback_exploratory": "Soporte fallback aproximado: resultado útil para exploración, no para exportación formal.",
    "variography_low_operational_reliability": "Variografía con baja confiabilidad operativa para modelado.",
    "variography_not_exportable": "Variografía no exportable para kriging por advertencias críticas.",
    DOMAINS_MODULE_DISABLED_REASON: "Etapa Dominios no disponible en el estado actual.",
}


def default_domain_ui_filters() -> dict[str, str]:
    return {"lithology": "", "alteration": "", "mine": ""}


def resolve_active_domain_column(dataframe, configured_domain_column: str) -> str:
    candidate = str(configured_domain_column or "").strip()
    if candidate and candidate in dataframe.columns:
        return candidate
    if DOMAIN_ESTIMATION_COLUMN in dataframe.columns:
        return DOMAIN_ESTIMATION_COLUMN
    return ""
