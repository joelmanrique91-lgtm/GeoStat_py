# Windows Desktop Launcher

## Uso rápido
1. Asegúrate de tener Git y Conda instalados.
2. Asegúrate de tener el environment `geostat-py` creado.
3. Ejecuta con doble clic: `scripts\\launch_app.cmd`.

El launcher hace este flujo:
1. Intenta `git pull --ff-only` (no destructivo).
2. Si `git pull` falla, avisa y continúa con la versión local.
3. Construye `PYTHONPATH` runtime incluyendo:
   - raíz del repo
   - `repo\\src`
4. Ejecuta la app con `python -m app.main` usando ese `env` explícito.
4. Guarda logs en `logs/launcher.log`.

> Esto evita depender de `pip install -e .` o de exportar `PYTHONPATH` manualmente en consola.

## Crear acceso directo en el escritorio
1. Abre `C:\ruta\a\GeoStat_py\scripts`.
2. Clic derecho sobre `launch_app.cmd` → **Enviar a > Escritorio (crear acceso directo)**.
3. (Opcional) Renombra el acceso directo a `GeoStat Py`.
4. Usa doble clic en ese acceso directo para abrir la app.

## Problemas comunes

### Git no encontrado
- Síntoma: en logs aparece que no se detecta Git.
- Acción: instala Git for Windows y marca opción para agregarlo a PATH.
- Comprobación: `git --version`.

### Conda no encontrado
- Síntoma: `launch_app.cmd` muestra error de `conda.bat` no encontrado.
- Acción: verifica instalación de Anaconda/Miniconda.
- Rutas típicas:
  - `%USERPROFILE%\\anaconda3\\condabin\\conda.bat`
  - `%USERPROFILE%\\miniconda3\\condabin\\conda.bat`

### Environment no existe
- Síntoma: falla `conda activate geostat-py`.
- Acción: desde Anaconda Prompt en el repo:
  - `conda env update --file environment.yml --prune`
- Comprobación: `conda env list`.

## Logs
- Archivo: `logs/launcher.log`
- Incluye comandos ejecutados, resultados de actualización y estado de arranque de app.
- Si la app falla al iniciar, el launcher registra:
  - stdout/stderr completos del proceso `python -m app.main`
  - traceback completo
  - diagnóstico rápido (dependencia faltante requerida/opcional, error de inicialización UI Tk).
