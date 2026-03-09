# GeoStat_py

Workspace local en Python para construir una **aplicación de escritorio geostatística** sobre la base de **GeostatsPy**.

> Objetivo de esta etapa: dejar una base limpia, reproducible y mantenible para evolucionar una GUI local (no web) en Windows + Anaconda.

## Estado actual del proyecto

- `geostatspy/` se mantiene como **submódulo Git** (fuente upstream de GeostatsPy).
- `app/` contiene la arquitectura inicial de la aplicación de escritorio con CustomTkinter.
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

La aplicación abre una ventana de escritorio con:
- encabezado del proyecto
- panel principal
- botones placeholder para:
  - Cargar CSV
  - Análisis variográfico
  - Kriging
  - Simulación SGS
  - Visualización

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
├─ tests/                      # smoke tests iniciales
├─ environment.yml             # entorno reproducible (Conda)
└─ README.md
```

## Prueba rápida (smoke test)

```bash
python -m unittest tests/test_imports.py
```

## Roadmap técnico sugerido

1. **Carga CSV real**
   - Selector de archivo en UI.
   - Validación de columnas y tipos.
   - Creación de `DatasetModel` desde `pandas.DataFrame`.
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
