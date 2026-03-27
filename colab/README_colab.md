# GeoStat_py en Colab (capa temporal)

Esta carpeta agrega una capa **temporal, aislada y reversible** para usar el motor analítico de `GeoStat_py` en Google Colab.

## Notebook principal (único flujo de uso real)
- **Principal:** `colab/01_workbench_geostat.ipynb`
- Está diseñado para correr desde una sesión fresca de Colab y **no depende** de ejecutar otro notebook antes.
- Incluye bootstrap al inicio: clone/update repo, instalación mínima, `sys.path`, validación de imports y creación de `service`.
- Luego ejecuta flujo analítico: upload CSV local (`google.colab.files.upload()`), `load_csv`, autodetección, configuración X/Y/Z/target, EDA inline y variografía inline.

## Notebook técnico/opcional
- `colab/00_bootstrap.ipynb` queda como notebook técnico de soporte/diagnóstico.
- No es requisito funcional para usar el workbench principal.

## Qué NO hace
- No ejecuta la app desktop completa.
- No porta `CustomTkinter`, `MainWindow`, `HomePanel`, `filedialog`, `messagebox` ni `FigureCanvasTkAgg` a Colab.

## Reversibilidad
- Toda la capa vive dentro de `colab/`.
- Al volver al entorno local desktop, puedes ignorarla o eliminarla sin afectar el proyecto principal.


## Interactividad notebook (sin UI desktop)
- El notebook principal expone `ANALYTICS_PARAMS` como bloque central de parámetros.
- Incluye `recalculate_analysis(...)` para recalcular filtros, EDA y variografía inline al cambiar parámetros.
- Flujo principal por celdas (estable); no depende de widgets.

- Incluye una capa opcional `Interactive Workbench (ipywidgets)`; si falla, el flujo manual por celdas sigue funcionando.
