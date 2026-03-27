# GeoStat_py en Colab (capa temporal)

Esta carpeta agrega una capa **temporal, aislada y reversible** para usar el motor analítico de `GeoStat_py` en Google Colab.

## Qué sí hace
- Bootstrap de entorno Colab (clone/pull + instalación mínima + `sys.path`).
- Validación de imports del motor (`app.services`, `app.models`).
- Smoke check opcional con CSV vía `GeostatService` (sin UI desktop).
- Preparación para trabajo analítico en notebook (EDA/cálculo/variografía desde servicios).

## Qué NO hace
- No ejecuta la app desktop completa.
- No porta `CustomTkinter`, `MainWindow`, `HomePanel`, `filedialog`, `messagebox` ni `FigureCanvasTkAgg` a Colab.

## Uso rápido
1. Abre `colab/00_bootstrap.ipynb` en Google Colab.
2. Ajusta parámetros iniciales (repo URL, branch opcional, mount Drive opcional, CSV opcional).
3. Ejecuta **Run all**.
4. Si todo pasa, abre `colab/01_workbench_geostat.ipynb` para flujo analítico (upload CSV local -> configuración -> EDA -> variografía).

## Reversibilidad
- Esta capa vive solo en `colab/`.
- Al volver a tu entorno local desktop, puedes ignorarla o eliminarla sin afectar el proyecto principal.


## Configuración por defecto
`colab/00_bootstrap.ipynb` ya viene preconfigurado para este repo con:
- `REPO_URL = "https://github.com/joelmanrique91-lgtm/GeoStat_py.git"`
- `BRANCH = "main"`
- `BASE_DIR = "/content"`
- `REPO_DIR_NAME = "GeoStat_py"`

Puedes editar estos valores si necesitas apuntar a otro fork/branch temporalmente.


## Etapa analítica en notebook
- `colab/01_workbench_geostat.ipynb` usa `google.colab.files.upload()` para cargar CSV desde memoria local.
- Reutiliza APIs reales del servicio (`load_csv`, autodetección, `set_variable_config`, EDA y variografía).
- Visualiza resultados solo inline con Matplotlib (sin UI desktop).
- Si `01_workbench_geostat.ipynb` no encuentra el módulo `app`, intenta autorecuperar ruta del repo (`/content/GeoStat_py`) y continuar.
