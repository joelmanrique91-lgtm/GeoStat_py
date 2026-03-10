# GeoStat_py

App de escritorio local (CustomTkinter) para análisis geoestadístico visual **enfocado y simplificado**.

## Arranque estándar (Windows + Anaconda)

```bash
conda activate geostat-py
cd C:\repos\GeoStat_py
python -m app.main
```

## Flujo visible actual del producto

La GUI muestra solo módulos que hoy aportan valor real:

1. **Datos**
2. **EDA**
3. **Espacial**

> En esta iteración, **Swath** y **Variografía** se mantienen fuera de la interfaz visible para evitar ruido y mantener foco en lo estable.

## Módulo Datos

- Carga CSV.
- Selección de X/Y/Z/target (con edición manual).
- Autodetección de columnas sugeridas al cargar:
  - X: `X`, `Easting`, `East`
  - Y: `Y`, `Northing`, `North`
  - Z: `Z`, `RL`, `Elev`, `Elevation`
  - Hole ID: `HoleID`, `Hole_ID`, `DHID`, `Drillhole`
  - Dominio/litología: `Domain`, `Lito`, `Lithology`, `Zone`
- El panel de configuración es **colapsable** para liberar espacio de visualización.

## EDA

### Resumen
Se muestra una tabla compacta con:
- dataset activo
- muestras
- columnas
- target
- valid_count
- null_pct
- mean, std, cv
- min, p10, p25, p50, p75, p90, max
- skewness

### Univariado
- Histograma
- Boxplot

## Espacial

Vista espacial enfocada en utilidad y estabilidad:
- Scatter **XY** coloreado por target.
- Segundo panel con vista **3D X/Y/Z** (matplotlib) coloreada por target cuando es viable.
- Si no es viable en el entorno, fallback seguro a vista 2D (XZ).
- Downsampling automático para datasets grandes (mensaje visible en actividad).

## Logging JSONL

Se mantiene el log por sesión en `logs/` con eventos de flujo y estabilidad, incluyendo:
- `columns_autodetected`
- `data_panel_collapsed`
- `data_panel_expanded`
- `spatial_3d_rendered`
- `spatial_3d_fallback_rendered`
- `workflow_simplified_view_loaded`

## Tests

```bash
python -m unittest
```
