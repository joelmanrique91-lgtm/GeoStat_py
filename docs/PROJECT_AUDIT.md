# PROJECT AUDIT - GeoStat_py

Fecha: 2026-03-20  
Alcance: auditoría técnica + remediación aplicada en código, tests, estructura y documentación.

---

## 1) Resumen ejecutivo

El repositorio presenta una base arquitectónica sólida para app desktop por capas (`ui`, `services`, `models`, `adapters`), pero tenía una falla crítica en el servicio univariado (`GeostatService`) que rompía contratos entre backend y UI.

En esta intervención se aplicó remediación directa:

- corrección del flujo `prepare_univariate_data`,
- separación real con `prepare_swath_data`,
- mitigación del riesgo de actualización de repo desde GUI,
- ajuste/fortalecimiento de tests,
- renovación completa de README,
- incorporación de `requirements.txt` y script seguro de actualización.

---

## 2) Arquitectura detectada

### Capas principales

- **UI**: `app/ui/` (CustomTkinter + paneles y dashboard matplotlib).
- **Servicios**: `app/services/` (carga CSV, EDA, visualización espacial, logging, update controlado).
- **Modelos**: `app/models/` (dataset, configuración de variables, estado de workflow).
- **Adapters**: `app/adapters/` (acceso encapsulado a GeostatsPy).

### Entry point

- `python -m app.main`

### Testing

- `unittest` en `tests/`.

---

## 3) Hallazgos críticos

1. **Defecto en flujo univariado**: retorno prematuro y lógica desplazada en `geostat_service.py`.
2. **Código inalcanzable**: bloque de payload univariado dentro de método incorrecto.
3. **Riesgo runtime**: `git pull` desde GUI sin control operativo por defecto.
4. **Documentación incompleta**: README insuficiente para onboarding reproducible.
5. **Reproducibilidad parcial**: solo `environment.yml` sin `requirements.txt`.

---

## 4) Decisiones de corrección aplicadas

### 4.1 Servicio univariado y swath

- Se rehízo `prepare_univariate_data()` para retornar **dict de contrato estable** consumido por UI/tests.
- Se creó `prepare_swath_data()` funcional y separado, usando `compute_swath_series`.
- Se removió código inalcanzable y inconsistencias de retorno.

### 4.2 Riesgo de update en GUI

- `update_repository()` queda bloqueado por defecto salvo variable de entorno explícita:
  - `GEOSTAT_ENABLE_RUNTIME_GIT_UPDATE=1`
- Se agrega `scripts/update_repo.py` para actualización segura fuera de runtime GUI.

### 4.3 Testing

- Se ajustan tests de `update_repository` para nuevo comportamiento por defecto seguro.
- Se agrega verificación de contrato de `prepare_univariate_data`.
- Se agrega test de salida de `prepare_swath_data`.

### 4.4 Documentación y entorno

- Se reescribe completamente `README.md`.
- Se crea este documento (`docs/PROJECT_AUDIT.md`).
- Se agrega `requirements.txt` coherente con dependencias del entorno conda.

---

## 5) Deuda técnica remanente

1. Placeholders funcionales para variografía/kriging/SGS.
2. Falta integración avanzada real con `geostatspy` en flujos productivos.
3. Falta cubrir más escenarios de UI real (tests de integración end-to-end).
4. No hay lockfile estricto cross-platform.

---

## 6) Riesgos remanentes

- Dependencia de entorno gráfico local para la UI desktop.
- Diferencias entre entornos conda/pip si se desalinean manualmente dependencias.
- Submódulo `geostatspy` puede no estar inicializado en clones nuevos.

---

## 7) Backlog priorizado

### P0

- Añadir tests de integración de flujo completo usuario (cargar CSV → configurar → EDA → espacial).

### P1

- Implementar workflows avanzados (variografía/kriging/SGS) sobre adapter.
- Proveer datos de ejemplo curados en `data/examples`.

### P2

- Evaluar empaquetado de app para distribución (installer ejecutable).

---

## 8) Estado final luego de esta intervención

El proyecto queda en un estado significativamente más consistente para crecimiento:

- contrato servicio/UI reparado en univariado,
- swath separado y funcional,
- riesgo de auto-update runtime mitigado,
- documentación de uso local (Windows + Anaconda) completa,
- trazabilidad de auditoría y decisiones registrada en `docs/PROJECT_AUDIT.md`.
