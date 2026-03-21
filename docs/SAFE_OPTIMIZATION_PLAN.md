# SAFE OPTIMIZATION PLAN

Estado de actualización: 2026-03-21 (Phase 2 conservative cleanup)

## A. Cambios seguros e inmediatos

- [x] **Alinear contrato de `update_repository()` con política de seguridad por defecto**
  - Resultado: resuelto en `app/services/geostat_service.py`.
  - Estado: **completado**.

- [x] **Blindar `_target_statistics()` para target numérico sin valores válidos**
  - Resultado: guard clause incorporado con retorno consistente y no explosivo.
  - Estado: **completado**.

- [x] **Eliminar fragilidad del test UI basado en strings legacy**
  - Resultado: `tests/test_ui_geometry_manager.py` migrado a validación estructural AST.
  - Estado: **completado**.

## B. Cambios seguros pero que requieren revisión manual

- [x] **Extraer helpers puros locales en `GeostatService`** (sin cambiar API pública)
  - Resultado: extracción interna aplicada (`_normalize_identifier`, `_build_univariate_availability`, `_empty_domain_payload`, `_compute_target_statistics`).
  - Estado: **completado**.

- [x] **Reducir duplicación local de guard clauses** en métodos de preparación de datos.
  - Resultado: consolidación de disponibilidad univariada y estadísticas en helpers puros.
  - Estado: **completado**.

## C. Cambios que requieren tests primero

- [ ] **Tipado fuerte de payloads EDA/cutoff/domain** manteniendo compatibilidad.
  - Estado: pendiente.
  - Prioridad actual: **alta**.

- [ ] **Refactor incremental interno de `GeostatService`** por capacidades, con fachada estable.
  - Estado: pendiente.
  - Prioridad actual: media-alta.

## D. Cambios que no conviene hacer aún

- [ ] Dividir arquitectura en subservicios/mover módulos en esta etapa.
- [ ] Refactorizar `HomePanel` de forma amplia.
- [ ] Cambiar contratos públicos o navegación UI.

Estado: se mantienen **postergados** por riesgo de ruptura en módulos críticos.
