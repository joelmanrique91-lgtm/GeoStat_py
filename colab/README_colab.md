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
4. Si todo pasa, quedas listo para trabajar temporalmente con el motor analítico.

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
