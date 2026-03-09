# GeoStat_py

App de escritorio local (CustomTkinter) para workflow geoestadístico con foco en visualización y exploración espacial.

## Arranque estándar (Windows + Anaconda)

```bash
conda activate geostat-py
cd C:\repos\GeoStat_py
python -m app.main
```

## Qué incluye esta iteración

- Dashboard reutilizable de gráficos embebidos (layouts 1x1, 1x2, 2x2, 3x1).
- Etapa Espacial con secciones **XY, XZ, YZ** + panel auxiliar de histograma.
- Módulo de **Swath plots** en X, Y y Z con media por bin y conteo de muestras.
- Primer módulo de **Variograma experimental omnidireccional** con parámetros configurables.
- Sidebar de workflow mantenida con foco visual en EDA/Espacial/Variografía.

## Workflow visible

1. Datos (funcional)
2. QA/QC (parcial)
3. EDA (funcional)
4. Espacial (funcional)
5. Variografía (funcional inicial)
6. Kriging (futuro)
7. Simulación (futuro)
8. Validación (futuro)
9. Exportación (parcial)

## Cómo usar X/Y/Z/target

1. Cargar CSV desde **Datos > Cargar CSV**.
2. Seleccionar columnas X, Y, Z y target.
3. Aplicar configuración.
4. Ir a EDA/Espacial/Variografía y pulsar **Actualizar dashboards**.

> Todas las visualizaciones usan la configuración activa X/Y/Z/target y gestionan NaN descartando filas incompletas.

## Módulo Espacial

En el tab **Espacial** se renderiza un dashboard 2x2:
- Scatter XY coloreado por target.
- Scatter XZ coloreado por target.
- Scatter YZ coloreado por target.
- Histograma de target (panel auxiliar).

Cada sección incluye ejes rotulados y colorbar.

## Swath plots

En el tab **Swath** se muestra un layout 3x1:
- Swath X, Swath Y y Swath Z.
- Línea = media de target por bin.
- Barras secundarias = número de muestras por bin.

Control principal:
- `Swath bins` (default 20).

## Variografía experimental

En el tab **Variografía**:
- Parámetros: `lag`, `# lags`, `dist máx`, `modo` (omnidireccional en esta iteración).
- Salida: curva del variograma experimental + tabla Lag/Gamma/Pares.
- Si no hay pares suficientes, se informa claramente en la UI y en log.

## Logging JSONL (eventos nuevos)

Se mantienen logs por sesión en `logs/` y se agregan eventos:
- `eda_dashboard_rendered`
- `spatial_dashboard_rendered`
- `section_view_rendered`
- `swath_rendered`
- `variogram_started`
- `variogram_rendered`
- `variogram_failed`
- `graph_render_failed`

## Tests

```bash
python -m unittest
```

## Pendiente para próxima iteración

- Variografía direccional (azimut, tolerancia angular, bandwidth).
- Ajuste de modelos variográficos.
- Integración de soporte compositado y dominios avanzados en vistas.
- Kriging/Simulación/Validación operativos.
