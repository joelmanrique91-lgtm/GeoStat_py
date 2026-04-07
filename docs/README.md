# Índice de documentación técnica

Este directorio contiene documentos operativos y reportes históricos. Esta guía define una estructura canónica sin mover archivos de forma riesgosa.

## 0) Fuente canónica y vigencia (leer primero)

- **Fuente canónica vigente del estado actual**: `STRUCTURE_SUMMARY_AUDIT_2026-04-07.md`
- Convención de vigencia usada en `docs/`:
  - **VIGENTE**: referencia primaria del estado actual.
  - **HISTÓRICO**: trazabilidad; no usar como fuente primaria de estado actual.

## 1) Prioridad de lectura (onboarding/auditoría)

1. `STRUCTURE_SUMMARY_AUDIT_2026-04-07.md` (**canónico; estado actual**)
2. Documentos vigentes temáticos (estrategia/operación puntual)
3. Históricos (solo contexto y trazabilidad)

## 2) Vigente temático (no canónico de estado global)

- `STRUCTURE_SUMMARY_AUDIT_2026-04-07.md` (**canónico**)
- `SAFE_OPTIMIZATION_PLAN.md`
- `VARIOGRAPHY_TEST_STRATEGY.md`
- `VARIOGRAPHY_REAL_DATA_TEST_GUIDE.md`

## 3) Operación (uso de la aplicación y soporte)

- `WINDOWS_DESKTOP_LAUNCHER.md`
- `UI_RENDER_FIX_2026-03-23.md`

## 4) Histórico (diagnóstico/auditorías previas)

- `PROJECT_AUDIT.md`
- `GUI_UX_TECHNICAL_AUDIT.md`
- `TECHNICAL_AUDIT_2026-03-22.md`
- `CODEBASE_AUTOAUDIT.md` (**histórico; usar solo como antecedente**)

## 5) Histórico (planes/reportes de ejecución)

- `IMPLEMENTATION_PHASE1_REPORT.md`
- `IMPLEMENTATION_PHASE2_REPORT.md`
- `VARIOGRAPHY_EXECUTION_SEQUENCE.md`
- `VARIOGRAPHY_IMPLEMENTATION_TICKETS.md`
- `VARIOGRAPHY_INTEGRATION_PLAN.md`
- `VARIOGRAPHY_TAB_SPEC.md`
- `VARIOGRAPHY_TARGET_ARCHITECTURE.md`
- `VARIOGRAPHY_TECHNICAL_BACKLOG.md`
- `PYVISTA_PHASE2_PLAN.md`
- `VARIOGRAPHY_*` restantes vinculados a planificación

> Regla de lectura: si hay contradicción entre documentos, priorizar **STRUCTURE_SUMMARY_AUDIT_2026-04-07.md** y luego el estado real del código.
