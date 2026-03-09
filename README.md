# GeoStat_py

Workspace local en Python para construir una **aplicación de escritorio geostatística** sobre la base de **GeostatsPy**.

> Objetivo de esta etapa: dejar una base limpia, reproducible y mantenible para evolucionar una GUI local (no web) en Windows + Anaconda.

## Estado actual del proyecto

- `geostatspy/` se mantiene como **submódulo Git** (fuente upstream de GeostatsPy).
- `app/` contiene la arquitectura inicial de la aplicación de escritorio con CustomTkinter.
- Ya está implementado el primer caso de uso real: **carga de CSV end-to-end** desde la GUI.
- Existe una separación explícita entre:
  - UI (`app/ui`)
  - lógica de aplicación (`app/services`)
  - integración externa (`app/adapters`)

## Requisitos

- Windows con Anaconda o Miniconda
- Git

## Inicializar el repositorio y submódulos

Desde la raíz del proyecto:

```bash
git clone <TU_URL_DEL_REPO>
cd GeoStat_py
git submodule update --init --recursive
```

Si el submódulo ya existe pero está vacío, corre nuevamente:

```bash
git submodule sync --recursive
git submodule update --init --recursive
```

## Crear entorno local (Anaconda)

```bash
conda env create -f environment.yml
conda activate geostat-py
```

## Lanzar la GUI local

Con el entorno activado y desde la raíz del repo:

```bash
python -m app.main
```

## Probar la carga de CSV en la GUI

1. Ejecuta `python -m app.main`.
2. Haz clic en **Cargar CSV**.
3. Selecciona un archivo `.csv` local.
4. Verás en pantalla:
   - estado de carga
   - nombre y ruta del archivo
   - filas y columnas
   - nombres de columnas
   - preview de las primeras 5 filas

Si cancelas el diálogo o hay error de lectura, la app no se cierra y muestra un mensaje amigable.

## Estructura del proyecto

```text
GeoStat_py/
├─ geostatspy/                 # submódulo GeostatsPy (upstream)
├─ app/
│  ├─ main.py                  # entry point GUI
│  ├─ ui/                      # componentes visuales
│  ├─ services/                # lógica de aplicación
│  ├─ adapters/                # integración con geostatspy
│  ├─ models/                  # modelos de datos
│  └─ utils/                   # utilidades comunes
├─ workflows/                  # documentación/guías de flujos geostatísticos
├─ data/                       # datasets locales de trabajo
├─ notebooks/                  # notebooks exploratorios
├─ tests/                      # tests mínimos y smoke tests
├─ environment.yml             # entorno reproducible (Conda)
└─ README.md
```

## Correr tests

```bash
python -m unittest tests/test_imports.py tests/test_csv_loading.py
```

## Roadmap técnico sugerido

1. **Validación de schema CSV**
   - Validar columnas requeridas por workflow geostatístico.
2. **Variografía inicial**
   - Implementar métodos en `GeostatSpyAdapter` para llamadas concretas a GeostatsPy.
   - Exponer casos de uso en `GeostatService`.
3. **Kriging y SGS**
   - Encapsular parámetros y resultados en modelos (`app/models`).
   - Mantener UI desacoplada de la API cruda.
4. **Visualización local**
   - Integrar gráficas con `matplotlib` embebidas en CustomTkinter.
5. **Calidad y trazabilidad**
   - Expandir tests por capas (adapter/service/ui smoke).
   - Definir convención de configuración y logging.

## Principios de diseño adoptados

- Mantener `geostatspy` como dependencia base sin alterar innecesariamente su código.
- Evitar mezclar UI con llamadas directas a librerías externas.
- Priorizar claridad para iteración incremental, sin sobreingeniería.
