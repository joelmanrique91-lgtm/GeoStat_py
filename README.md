# GeoStat_py

Aplicación de escritorio local (Python + CustomTkinter) para flujo geoestadístico guiado por etapas: **Datos → EDA → Espacial**.

## 1) ¿Qué es este proyecto?

`GeoStat_py` es una base de trabajo para análisis geoestadístico visual sobre CSVs locales. El foco actual está en:

- carga de datos y configuración de columnas,
- análisis exploratorio (resumen + univariado),
- visualización espacial 2D (XY/XZ/YZ),
- trazabilidad mediante logs JSONL por sesión.

El entrypoint principal se mantiene en:

```bash
python -m app.main
```

---

## 2) Estado actual del proyecto

### Funciona hoy

- UI de escritorio con navegación por etapas (`Datos`, `EDA`, `Espacial`).
- Carga de CSV y autodetección de columnas relevantes (X/Y/Z/Target/HoleID/Dominio).
- Configuración manual de variables con validaciones básicas.
- EDA:
  - tabla de estadísticas del target,
  - histograma,
  - boxplot general,
  - probability plot,
  - boxplot por dominio (con simplificación top-N).
- Espacial 2D: secciones XY, XZ, YZ.
- Logging de actividad a `logs/session_*.jsonl`.

### Corregido en esta intervención

- Se reparó la separación lógica entre `prepare_univariate_data()` y `prepare_swath_data()`.
- Se removió código inalcanzable y retornos inconsistentes en `GeostatService`.
- Se reforzaron tests del contrato univariado y del flujo swath.
- Se mitigó el riesgo de `git pull` en runtime de GUI: ahora está bloqueado por defecto y documentado.

### En desarrollo / pendiente

- Integración funcional profunda con submódulo `GeostatsPy` en workflows avanzados.
- Módulos de variografía/kriging/simulación aún como placeholders en UI/servicio.
- Falta ampliar cobertura con pruebas de integración UI end-to-end.

### Limitaciones actuales

- La app requiere entorno gráfico local (desktop).
- Para actualización del repo se recomienda flujo por terminal con app cerrada.
- Si no está inicializado el submódulo `geostatspy`, algunas capacidades futuras no estarán disponibles.

---

## 3) ¿Qué contiene hoy el proyecto?

- `app/main.py`: arranque de la aplicación.
- `app/ui/`: ventana principal y paneles de interfaz.
- `app/services/`: lógica de negocio (carga, EDA, visualización, logging, actualización controlada).
- `app/models/`: modelos de datos y estado de workflow.
- `app/adapters/`: adaptación hacia `GeostatsPy`.
- `tests/`: pruebas unitarias y regresión.
- `scripts/update_repo.py`: actualización segura del repositorio desde terminal.
- `workflows/examples.md`: notas de workflows planificados.
- `environment.yml` + `requirements.txt`: instalación de dependencias.

---

## 4) Estructura del repositorio

```text
GeoStat_py/
├─ app/
│  ├─ adapters/
│  ├─ models/
│  ├─ services/
│  ├─ ui/
│  └─ main.py
├─ tests/
├─ docs/
│  └─ PROJECT_AUDIT.md
├─ scripts/
│  └─ update_repo.py
├─ workflows/
├─ data/
├─ notebooks/
├─ logs/
├─ environment.yml
├─ requirements.txt
└─ README.md
```

---

## 5) Tutorial de arranque (Windows + Anaconda Prompt)

## Prerrequisitos

- Windows con Anaconda o Miniconda instalado.
- Git instalado.
- Repo clonado localmente.

### Paso a paso (copiar/pegar)

1. Abrí **Anaconda Prompt**.
2. Navegá al repo:

```bat
cd C:\ruta\a\GeoStat_py
```

3. Crear (primera vez) o actualizar entorno:

```bat
conda env update --file environment.yml --prune
```

4. Activar entorno:

```bat
conda activate geostat-py
```

5. (Opcional) instalar con pip desde `requirements.txt`:

```bat
pip install -r requirements.txt
```

6. Ejecutar app:

```bat
python -m app.main
```

7. Ejecutar tests:

```bat
python -m unittest
```

### Validar que arrancó bien

- Se abre una ventana titulada `GeoStat Py - Geostatistics Desktop`.
- Se ven etapas `Datos / EDA / Espacial`.
- Al cargar un CSV válido, se completan cards de resumen y selector de columnas.

### Troubleshooting rápido

- **`ModuleNotFoundError`**: verificar `conda activate geostat-py`.
- **No abre ventana**: ejecutar en sesión con escritorio activo (no headless).
- **`geostatspy` no importable**: inicializar submódulo:

```bat
git submodule update --init --recursive
```

- **Actualizar repo** (recomendado fuera de GUI):

```bat
python scripts\update_repo.py
```

---

## 6) Flujo recomendado de uso

1. Iniciar app.
2. Etapa **Datos**: cargar CSV y aplicar configuración X/Y/Z/Target (+ dominio opcional).
3. Etapa **EDA**:
   - revisar tabla de estadísticos,
   - analizar gráficos univariados y mensajes de disponibilidad.
4. Etapa **Espacial**: revisar secciones XY/XZ/YZ.
5. Exportar log si necesitás trazabilidad de sesión.

---

## 7) Próximos pasos sugeridos (priorizados)

1. **P0**: ampliar tests de integración de UI/servicio para flujos completos de usuario.
2. **P1**: integrar workflows geoestadísticos avanzados con `GeostatsPy` (variografía/kriging/SGS).
3. **P1**: agregar ejemplos de datos mínimos reproducibles en `data/examples/`.
4. **P2**: preparar empaquetado/distribución de app desktop.

---

## Nota sobre actualización de repositorio desde GUI

Por seguridad operativa, la actualización de repo desde runtime GUI está **bloqueada por defecto**.

- Si realmente necesitás habilitarla (no recomendado):

```bat
set GEOSTAT_ENABLE_RUNTIME_GIT_UPDATE=1
python -m app.main
```

- Flujo recomendado: cerrar app y usar `python scripts\update_repo.py`.
