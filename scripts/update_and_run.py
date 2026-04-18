"""Windows launcher helper: update repository and run desktop app."""

from __future__ import annotations

from datetime import datetime, timezone
import logging
import os
from pathlib import Path
import subprocess
import sys

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.append(str(CURRENT_DIR))

from repo_ops import PROJECT_ROOT, git_path, is_git_repo, run_capture

LOGS_DIR = PROJECT_ROOT / "logs"
LOG_FILE = LOGS_DIR / "launcher.log"


def configure_logger() -> logging.Logger:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("geostat_launcher")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


def run_command(command: list[str], logger: logging.Logger, *, timeout: int = 180) -> tuple[int, str]:
    logger.info("$ %s", " ".join(command))
    code, output = run_capture(command, timeout=timeout)
    if output:
        logger.info(output)
    return code, output


def _build_runtime_env() -> dict[str, str]:
    """Build subprocess environment so `python -m app.main` can import src packages.

    Contract:
    - Keep current process env untouched.
    - Prepend `<repo_root>` and `<repo_root>/src` to PYTHONPATH for the app process.
    """
    env = os.environ.copy()
    repo_root = str(PROJECT_ROOT)
    repo_src = str(PROJECT_ROOT / "src")
    current = env.get("PYTHONPATH", "")
    parts = [repo_root, repo_src]
    if current:
        parts.append(current)
    env["PYTHONPATH"] = os.pathsep.join(parts)
    return env


def update_repository(logger: logging.Logger) -> None:
    detected_git = git_path()
    if detected_git is None:
        logger.warning("Git no encontrado en PATH. Se omite actualización y se continúa con versión local.")
        return

    logger.info("Git detectado: %s", detected_git)
    if not is_git_repo():
        logger.warning("Directorio actual no es repo git válido. Se omite actualización.")
        return

    run_command(["git", "rev-parse", "--abbrev-ref", "HEAD"], logger)

    try:
        code, _ = run_command(["git", "pull", "--ff-only"], logger, timeout=240)
    except subprocess.TimeoutExpired:
        logger.warning("Timeout durante git pull. Se continúa con la versión local.")
        return

    if code != 0:
        logger.warning("git pull falló. Se continuará con la última versión local disponible.")
        return

    logger.info("Actualización de repositorio finalizada.")


def run_app(logger: logging.Logger) -> int:
    command = [sys.executable, "-m", "app.main"]
    runtime_env = _build_runtime_env()
    logger.info("Iniciando aplicación con intérprete activo: %s", sys.executable)
    logger.info("PYTHONPATH runtime: %s", runtime_env.get("PYTHONPATH", ""))
    logger.info("$ %s", " ".join(command))

    try:
        process = subprocess.run(command, cwd=PROJECT_ROOT, env=runtime_env, check=False)
    except Exception as exc:  # noqa: BLE001
        logger.error("Error al iniciar la app: %s", exc)
        return 1

    if process.returncode != 0:
        logger.error("La app finalizó con código de error: %s", process.returncode)
    else:
        logger.info("La app finalizó correctamente.")
    return int(process.returncode)


def main() -> int:
    logger = configure_logger()
    logger.info("=" * 72)
    logger.info("Launcher iniciado UTC=%s", datetime.now(timezone.utc).isoformat())
    logger.info("Proyecto: %s", PROJECT_ROOT)

    try:
        update_repository(logger)
        return run_app(logger)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Fallo no controlado del launcher: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
