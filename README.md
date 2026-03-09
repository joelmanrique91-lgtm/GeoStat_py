# GeoStat_py

App de escritorio local (CustomTkinter) para workflow geoestadístico con foco en **exploración visual**.

## Arranque estándar (Windows + Anaconda)

```bash
conda activate geostat-py
cd C:\repos\GeoStat_py
python -m app.main
```

## Qué cambió en esta iteración

La app dejó de priorizar texto y ahora prioriza panel visual:
- Sidebar izquierda: workflow por etapas.
- Centro: controles del paso actual.
- Derecha (dominante): panel visual con tabs EDA.
- Log técnico: secundario y colapsable.

## Workflow visible

1. Datos (funcional)
2. QA/QC (parcial)
3. EDA (funcional)
4. Espacial (funcional inicial)
5. Variografía (futuro)
6. Kriging (futuro)
7. Simulación (futuro)
8. Validación (futuro)
9. Exportación (parcial)

## Feedback visual automático

Después de:
1) cargar CSV,
2) seleccionar X/Y/Z/target,
3) aplicar configuración,

la app renderiza automáticamente:
- Histograma del target
- Boxplot del target
- Scatter XY coloreado por target

Si target no es numérico o faltan datos válidos, se muestra mensaje claro y se registra en JSONL.

## EDA visual por tabs

- **Resumen**: resumen textual compacto + tabla corta de estadísticas (n, mean, std, min, p10, p25, p50, p75, p90, max, skewness).
- **Univariado**: histograma + boxplot.
- **Espacial**: scatter XY con color por target.

## Tarjetas compactas (parte superior del panel visual)

- Dataset
- Muestras
- Columnas
- Target
- Estado
- Dominio
- Soporte
- Mean / Std / CV (si target numérico)

## Botones globales

- **Actualizar repo**: `git pull` + `git submodule update --init --recursive`.
- **Exportar log**: exporta log JSONL de sesión.

## Logging JSONL

- Carpeta: `logs/`
- Archivo por sesión: `session_YYYYMMDD_HHMMSS.jsonl`
- Eventos relevantes incluyen:
  - `visuals_auto_rendered`
  - `histogram_rendered`
  - `boxplot_rendered`
  - `spatial_view_rendered`
  - `visual_render_failed`
  - `workflow_step_changed`
  - `csv_load_*`, `repo_update_*`, `export_log_requested`

## Tests

```bash
python -m unittest tests/test_activity_log.py tests/test_workflow_state.py tests/test_visual_preparation.py tests/test_module_placeholders.py tests/test_imports.py tests/test_csv_loading.py tests/test_service_features.py
```

## Próxima iteración sugerida

- selector de vista espacial XY/XZ/YZ
- probability plot en Univariado
- secciones y swath plots
- variografía experimental
