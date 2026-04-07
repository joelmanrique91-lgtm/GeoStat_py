# Diagnóstico técnico e implementación geoestadística (2026-04-07)

## 1) Auditoría inicial del repositorio

### Módulos relevantes encontrados
- `app/services/visualization_service.py`
  - `compute_experimental_variogram`: cálculo explícito por pares, binning por lag, `pair_counts`, filtro direccional 3D y tolerancias.
- `app/services/variography_geometry.py`
  - `DirectionalConfig` y `pair_matches_direction`: geometría direccional 3D (azimuth/dip/tolerancias/bandwidth).
- `app/services/variogram_modeling_service.py`
  - modelos teóricos (esférico/exponencial/gaussiano), evaluación de calidad y `auto_fit_wls` con pesos por `npairs`.
- `app/services/dataset_context_service.py`
  - ingesta de CSV y ciclo de configuración de columnas.
- `app/services/geostat_service.py`
  - EDA univariado, estadísticas de target, payloads para UI y coordinación de flujo.

### Funciones reutilizables (rutina madre)
Se adopta como base madre:
1. `compute_experimental_variogram` (cálculo experimental Matheron por pares).
2. `pair_matches_direction` (selección direccional 3D explícita).
3. `auto_fit_wls` + `evaluate_model` + `evaluate_quality` (fitting WLS y control de calidad).

### Riesgos de duplicación detectados
- EDA repartido entre `geostat_service` y payloads de UI.
- Validaciones de entrada dispersas entre `dataset_context_service` y `variography_application_service`.
- No existía un pipeline único end-to-end técnico (independiente de UI) con exportación práctica tipo Leapfrog.

### Debilidades matemáticas/técnicas detectadas
- No había una salida compacta “copy/paste” para Leapfrog.
- No existía un contrato operativo único para QA/QC + EDA + variograma + fitting + exportación en un solo flujo reproducible de backend.

## 2) Arquitectura objetivo aplicada
Se implementa una capa técnica backend adicional reutilizando la base existente:
- `app/services/geostat_pipeline_service.py`
  - `validate_geological_data`
  - `build_eda_report`
  - `fit_directional_variogram_wls`
  - `export_leapfrog_parameters`
  - `run_pipeline`

No se reemplaza la lógica madre existente; se encapsula y orquesta para trazabilidad reproducible y uso científico directo.

## 3) Implementación realizada
- QA/QC robusto de ingesta sobre DataFrame geológico (`X`,`Y`,`Z`,target), con nulos, duplicados, porcentaje utilizable y advertencias.
- EDA descriptivo con media/mediana/std/var/cv/min/max + percentiles + outliers IQR + sugerencia top-cut (P98).
- Variografía experimental direccional 3D usando la rutina madre existente (pares + bins + `npairs`).
- Fitting WLS reutilizando solver actual, restringiendo a modelos requeridos (esférico/exponencial/gaussiano) y chequeando parámetros físicos.
- Exportación tipo Leapfrog en formato textual claro y no ambiguo.
- Ejemplo reproducible end-to-end con dataset sintético anisotrópico.

## 4) Supuestos geoestadísticos explícitos
- Hipótesis intrínseca local para estimación de semivarianza.
- Estacionariedad débil implícita en ventana de análisis (evaluación exploratoria).
- Selección direccional axial (v y -v equivalentes) según convención de variografía.
- Ajuste por WLS ponderado por `npairs` (mayor soporte estadístico => mayor peso efectivo).

## 5) Validaciones incorporadas
- Bloqueo por datos insuficientes (`valid_rows < 20`).
- Bloqueo por baja confiabilidad de ajuste (`npairs_total < 100`, `valid_lags < 4`, RMSE no finito).
- Verificación de parámetros físicos (`nugget>=0`, `sill>=0`, ranges > 0).

## 6) Limitaciones actuales
- Pipeline operativo usa estructura simple de una sola estructura teórica (exportación básica tipo Leapfrog).
- No incluye aún optimización multi-estructura automática con selección de mejor modelo por criterio global entre múltiples direcciones simultáneas.
