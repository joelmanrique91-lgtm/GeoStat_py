# Auditoría activa de dependencias e importaciones (2026-04-18)

## Importaciones externas detectadas (código productivo)
- Núcleo numérico/ciencia de datos: `numpy`, `pandas`, `scipy`.
- UI/visualización: `customtkinter`, `matplotlib`, `plotly`.
- Geoestadística opcional: `skgstat` (scikit-gstat), `pykrige`.
- 3D opcional: `pyvista`, `vtk`.
- Aceleración opcional: `numba`.

## Mapeo módulo → librería
- `app/main.py`, `app/ui/*`: `customtkinter`, `matplotlib`.
- `app/services/visualization_service.py`: `numpy`, `pandas`, `numba` (opcional), backend variográfico.
- `src/mining_geostat/variography_backend.py`: `numpy`, `scipy.spatial.cKDTree`, `numba` (opcional), `skgstat` (opcional).
- `src/mining_geostat/kriging.py`: `numpy`, `pykrige` (opcional).
- `app/ui/renderers/pyvista_spatial3d_renderer.py`: `pyvista`/`vtk` (preferido), `plotly` fallback.

## Dependencias detectadas como muertas en core
- `scikit-learn` (declarada, no usada en imports productivos).
- `jupyter` (declarada en runtime, no requerida por ejecución app/CLI).
- `gstools` (declarada, no usada).
- `seaborn`, `dask` no aparecen en imports ni requerimientos actuales del código.

## Rutas críticas verificadas
- Backend de variografía: `src/mining_geostat/variography_backend.py`.
- Servicio de visualización/variografía app: `app/services/visualization_service.py`.
- Renderizado 3D: `app/ui/renderers/base.py`, `app/ui/renderers/pyvista_spatial3d_renderer.py`, `app/ui/renderers/mpl_spatial3d_renderer.py`.

## Cambios concretos planificados
1. Unificar dependencias tomando `environment.yml` como fuente principal y alinear `requirements.txt` + `pyproject.toml`.
2. Eliminar mutaciones `sys.path` de runtime (app/cli/tests) y usar import de paquete.
3. Integrar `lag_tolerance` al binning variográfico (eliminar cálculo muerto).
4. Optimizar variografía para datasets medianos/grandes con selección de pares por `cKDTree` + chunking.
5. Formalizar contrato de capacidades para renderers 3D con fallback explícito.
