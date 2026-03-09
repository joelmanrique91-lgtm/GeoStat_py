# GeoStat_py

Workspace local en Python para construir una **aplicación de escritorio geostatística** sobre la base de **GeostatsPy**.

> Objetivo de esta etapa: mantener una base limpia, reproducible y usable para trabajo diario en Windows + Anaconda.

## Estado actual del proyecto

- `geostatspy/` se mantiene como **submódulo Git** (fuente upstream de GeostatsPy).
- GUI local con **CustomTkinter**.
- Funcionalidades ya operativas:
  - carga de CSV end-to-end
  - botón **Actualizar repo** desde la GUI (`git pull` + actualización de submódulos)
  - configuración de columnas **X / Y / Z / target**
  - EDA inicial del dataset y de la variable objetivo seleccionada

## Requisitos

- Windows con Anaconda o Miniconda
- Git

## Inicializar el repositorio y submódulos

```bash
git clone <TU_URL_DEL_REPO>
cd GeoStat_py
git submodule update --init --recursive
```

Si el submódulo aparece vacío:

```bash
git submodule sync --recursive
git submodule update --init --recursive
```

## Crear entorno local (Anaconda)

```bash
conda env create -f environment.yml
conda activate geostat-py
```

## Comando estándar de arranque

```bash
python -m app.main
```

## Flujo de uso recomendado

1. Abrir la app con `python -m app.main`.
2. (Opcional) Presionar **Actualizar repo**.
   - Ejecuta `git pull` en la raíz del repo.
   - Ejecuta `git submodule update --init --recursive`.
   - Muestra salida en pantalla.
   - Si hubo cambios, la app sugiere reiniciar.
3. Presionar **Cargar CSV** y seleccionar archivo `.csv`.
4. Revisar resumen del dataset:
   - nombre/ruta
   - filas/columnas
   - columnas
   - preview inicial
5. Configurar columnas:
   - **X**
   - **Y**
   - **Z**
   - **Target**
6. Presionar **Aplicar configuración** para obtener EDA inicial.

## Qué muestra la EDA inicial

- filas y columnas
- nombres de columnas
- tipo de dato por columna
- nulos por columna
- columnas numéricas detectadas
- configuración actual X/Y/Z/target
- estadísticos de target (si es numérico):
  - count, mean, std, min, 25%, 50%, 75%, max

Si target no es numérico, la app lo informa de forma amigable.

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
├─ tests/                      # tests mínimos y smoke tests
├─ workflows/
├─ data/
├─ notebooks/
├─ environment.yml
└─ README.md
```

## Correr tests

```bash
python -m unittest tests/test_imports.py tests/test_csv_loading.py tests/test_service_features.py
```

## Principios de diseño

- No mezclar UI con lógica pesada.
- Mantener `geostatspy` intacto como dependencia base.
- Evolucionar por iteraciones simples, útiles y mantenibles.
