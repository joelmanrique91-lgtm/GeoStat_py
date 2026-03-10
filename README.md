# GeoStat_py

App de escritorio local (CustomTkinter) para análisis geoestadístico visual con separación clara por etapa.

## Arranque estándar (Windows + Anaconda)

```bash
conda activate geostat-py
cd C:\repos\GeoStat_py
python -m app.main
```

## Flujo visible actual

1. **Datos**
2. **EDA**
3. **Espacial**

## Separación de lógica visual por etapa

### Datos
- Carga de CSV.
- Autodetección de columnas (X/Y/Z/target/Hole ID/Dominio).
- Configuración editable y panel colapsable.
- Resumen compacto de configuración activa.

### EDA
- Subtabs: **Resumen** y **Univariado**.
- **Resumen**: tabla de estadísticos completos del target.
- **Univariado**:
  - histograma,
  - boxplot general,
  - probability plot,
  - boxplot por dominio/categoría (si hay dominio válido).

Univariado ahora intenta renderizar cada gráfico de forma independiente; si uno falla, los demás siguen visibles y se informa en pantalla/log (sin panel vacío silencioso).

Cuando hay muchas categorías en dominio, la vista se simplifica a top-N por frecuencia y se informa en actividad/log.

### Espacial
- Vista principal centrada en secciones 2D útiles:
  - XY (planta),
  - XZ (sección),
  - YZ (sección).
- La vista 3D deja de ser el foco principal en esta iteración.

## Logging JSONL relevante

Se mantiene logging por sesión en `logs/` con eventos como:
- `workflow_step_data_opened`
- `workflow_step_eda_opened`
- `workflow_step_spatial_opened`
- `eda_univariate_render_started`
- `eda_target_coerced_numeric`
- `eda_target_valid_count_computed`
- `eda_domain_valid_count_computed`
- `eda_univariate_payload_prepared`
- `eda_univariate_payload_empty`
- `univariate_payload_built`
- `univariate_payload_empty`
- `univariate_histogram_available`
- `univariate_boxplot_available`
- `univariate_probability_available`
- `univariate_domain_boxplot_available`
- `univariate_component_unavailable`
- `eda_univariate_render_partial`
- `eda_univariate_render_finished`
- `eda_univariate_render_failed`
- `domain_boxplot_rendered`
- `domain_boxplot_simplified`
- `domain_boxplot_failed`
- `probability_plot_rendered`
- `probability_plot_failed`
- `spatial_2d_rendered`
- `spatial_3d_disabled_or_hidden`
- `empty_state_shown`

## Tests

```bash
python -m unittest
```
