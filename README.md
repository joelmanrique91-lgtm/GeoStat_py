# GeoStat_py

Aplicación de escritorio local (Python + CustomTkinter) para un flujo geoestadístico guiado por etapas: **Datos → EDA → Espacial**.

## 1) Alcance actual

El proyecto hoy cubre principalmente:

- carga de CSV locales;
- configuración de columnas X/Y/Z/Target (+ HoleID y Dominio opcionales);
- análisis exploratorio univariado (estadísticos, histograma, boxplot, probability plot);
- visualización espacial 2D (XY / XZ / YZ);
- logging de actividad por sesión en `logs/session_*.jsonl`.

Entrypoint principal:

```bash
python -m app.main
```

## 2) Estructura real del repositorio

```text
GeoStat_py/
├─ app/
│  ├─ adapters/     # Integración con GeostatsPy
│  ├─ models/       # Modelos de dominio y contratos
│  ├─ services/     # Lógica de aplicación
│  ├─ ui/           # Ventana, paneles y renderers
│  ├─ utils/        # Utilidades compartidas
│  └─ main.py
├─ tests/           # Suite de pruebas (unittest)
├─ tests/fixtures/  # Datos de prueba
├─ scripts/         # Helpers operativos (update/launcher)
├─ docs/            # Auditorías y documentación técnica
├─ workflows/       # Notas de workflows
├─ data/            # Datos locales del usuario (si aplica)
├─ notebooks/       # Notebooks locales (si aplica)
├─ logs/            # Logs de ejecución
├─ geostatspy/      # Submódulo aguas abajo
├─ environment.yml
├─ requirements.txt
└─ README.md
```

## 3) Instalación

### Opción A (recomendada): conda

```bash
conda env update --file environment.yml --prune
conda activate geostat-py
```

### Opción B: pip

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
# source .venv/bin/activate

pip install -r requirements.txt
```

## 4) Ejecución

```bash
python -m app.main
```

En Windows también se puede usar:

- `scripts/launch_app.cmd` (activa conda + actualiza + ejecuta)
- `scripts/update_and_run.py`

## 5) Pruebas

El proyecto usa `unittest`.

```bash
python -m unittest discover -s tests -p "test_*.py"
```

Prueba puntual:

```bash
python -m unittest tests.test_imports
```

## 6) Actualización segura del repositorio

Con la app cerrada:

```bash
python scripts/update_repo.py
```

Para permitir actualización en runtime GUI (no recomendado):

```bash
# Windows (cmd)
set GEOSTAT_ENABLE_RUNTIME_GIT_UPDATE=1
python -m app.main
```

## 7) Documentación técnica

- Punto de entrada recomendado: `docs/README.md`.
- Auditorías y reportes históricos se mantienen en `docs/` para trazabilidad.

## 8) Mantenimiento / contribución

- Mantener cambios acotados por capa (`models`, `services`, `ui`).
- Preferir pruebas unitarias o de contrato cuando se toquen servicios.
- Evitar acoplar lógica de negocio dentro de componentes UI.
- Si se modifica un flujo, actualizar README y documentación técnica relacionada.
