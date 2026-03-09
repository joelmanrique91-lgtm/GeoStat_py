# GeoStat_py

Aplicación de escritorio local para workflows geostatísticos en Python, construida sobre GeostatsPy, pensada para uso diario en **Windows + Anaconda**.

## Arranque estándar (Windows + Anaconda)

```bash
conda activate geostat-py
cd C:\repos\GeoStat_py
python -m app.main
```

## Qué incluye esta versión

- UI reorganizada en paneles funcionales:
  1. Header / toolbar
  2. Dataset
  3. Configuración espacial (X/Y/Z/target)
  4. EDA inicial
  5. Workflows no implementados + actividad reciente
- Botón **Actualizar repo** (`git pull` + `git submodule update --init --recursive`).
- Botón **Exportar log** para guardar la sesión en `.jsonl`.
- Logging persistente de actividad y errores en JSONL por sesión.

## Flujo de uso recomendado

1. Iniciar app (`python -m app.main`).
2. (Opcional) Presionar **Actualizar repo**.
3. Presionar **Cargar CSV**.
4. Revisar resumen del dataset (archivo, ruta, filas, columnas, preview).
5. Seleccionar **X / Y / Z / target** y presionar **Aplicar configuración**.
6. Revisar EDA inicial:
   - columnas
   - dtypes
   - nulos
   - columnas numéricas
   - estadísticos del target (si es numérico)

## Módulos no implementados

Los módulos de:
- Análisis variográfico
- Kriging
- Simulación SGS
- Visualización

se muestran como **Próximamente**. Si haces clic, la app muestra un mensaje claro y registra el evento en el log.

## Logs de actividad (JSONL)

- Carpeta: `logs/`
- Formato: 1 evento JSON por línea (`.jsonl`)
- Se genera un archivo por sesión (`session_YYYYMMDD_HHMMSS.jsonl`)
- Eventos mínimos registrados:
  - `app_started`
  - `repo_update_started`
  - `repo_update_finished`
  - `csv_load_started`
  - `csv_load_cancelled`
  - `csv_load_succeeded`
  - `csv_load_failed`
  - `variable_config_applied`
  - `placeholder_module_clicked`
  - `export_log_requested`
  - `app_error`

Esto permite adjuntar el `.jsonl` en ChatGPT para diagnóstico post-sesión.

## Botón Exportar log

- Abre selector de ubicación.
- Copia el log de la sesión actual a la ruta elegida.
- Fuerza extensión `.jsonl` si no se especifica.

## Tests

```bash
python -m unittest tests/test_activity_log.py tests/test_service_features.py tests/test_csv_loading.py tests/test_imports.py
```

## Notas de arquitectura

- Se mantiene separación por capas: `ui/`, `services/`, `models/`, `utils/`.
- `geostatspy/` se mantiene intacto como submódulo base.
- No se usa web/streamlit ni Qt.
