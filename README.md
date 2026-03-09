# GeoStat_py

Aplicación de escritorio local (CustomTkinter) orientada a workflow geoestadístico real:

**preparar datos → QA/QC → EDA → dominios/compositado → espacial → variografía → kriging → simulación → validación → exportación**.

## Arranque estándar (Windows + Anaconda)

```bash
conda activate geostat-py
cd C:\repos\GeoStat_py
python -m app.main
```

## Nuevo diseño por workflow

La interfaz quedó organizada en 3 zonas permanentes:

1. **Izquierda**: navegación por etapas del workflow.
2. **Centro**: parámetros y acción principal del paso actual.
3. **Derecha**: resultados, resumen y vista previa.

Además:
- Encabezado con contexto persistente: dataset, target, dominio activo, soporte activo, paso actual.
- Log técnico secundario y colapsable.

## Etapas del workflow y estado actual

1. **Datos** → funcional
   - Cargar CSV
   - mapping de X/Y/Z/target + Hole ID + Dominio/Litología
   - resumen de dataset
2. **QA/QC** → parcial
   - quality gate inicial
   - semáforo verde/amarillo/rojo
   - duplicados, nulos, coordenadas faltantes, columnas numéricas
   - tratamiento de extremos (top-cut/capping) visible como siguiente paso
3. **EDA** → funcional
   - resumen estructurado (univariado/bivariado base)
   - estadísticas del target
4. **Dominios y compositado** → futuro
5. **Espacial** → parcial (estructura lista, implementación detallada futura)
6. **Variografía** → futuro
7. **Kriging** → futuro
8. **Simulación** → futuro
9. **Validación** → futuro
10. **Exportación** → parcial

## Botones globales

- **Actualizar repo**: ejecuta `git pull` + `git submodule update --init --recursive`.
- **Exportar log**: copia el log de la sesión actual a un `.jsonl` elegido por el usuario.

## Logging JSONL de actividad

- Carpeta: `logs/`
- Archivo por sesión: `session_YYYYMMDD_HHMMSS.jsonl`
- Formato: 1 evento JSON por línea
- Eventos relevantes incluyen:
  - `app_started`
  - `workflow_step_changed`
  - `data_quality_evaluated`
  - `csv_load_*`
  - `variable_config_applied`
  - `placeholder_module_clicked`
  - `repo_update_*`
  - `export_log_requested`
  - `app_error`

Esto permite análisis posterior en ChatGPT o scripts.

## Tests

```bash
python -m unittest tests/test_activity_log.py tests/test_workflow_state.py tests/test_module_placeholders.py tests/test_imports.py tests/test_csv_loading.py tests/test_service_features.py
```

## Evolución esperada

Próximas iteraciones recomendadas:
- EDA visual embebida (histograma target + scatter XY coloreado por target)
- módulo espacial 2D (planta + secciones)
- dominios/compositado con soporte activo real
- variografía y estimación/simulación reales
