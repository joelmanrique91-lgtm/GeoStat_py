# GeoStat_py

App de escritorio local (CustomTkinter) para análisis geoestadístico visual con etapas separadas por responsabilidad.

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
- Resumen de configuración activa.

### EDA
- Subtabs: **Resumen** y **Univariado**.
- **Resumen**: estadísticas completas del target (incluye nulos y válidos).
- **Univariado**:
  - histograma,
  - boxplot general,
  - probability plot,
  - boxplot por dominio/categoría (si hay dominio seleccionado).

### Espacial
- Vista dedicada a **3D** (X/Y/Z coloreado por target) como gráfico principal.
- Fallback interno a 2D (XZ) sólo si el 3D falla por estabilidad/entorno.

## Uso de Dominio en EDA

Si se selecciona una columna de dominio válida, EDA genera boxplot por categoría.
Si hay demasiadas categorías, se limita a top-N por frecuencia y se informa en actividad/log.

## Logging JSONL relevante

Se mantiene logging por sesión en `logs/` y se incluyen eventos como:
- `workflow_step_data_opened`
- `workflow_step_eda_opened`
- `workflow_step_spatial_opened`
- `eda_domain_boxplot_rendered`
- `probability_plot_rendered`
- `spatial_3d_primary_rendered`

## Tests

```bash
python -m unittest
```
