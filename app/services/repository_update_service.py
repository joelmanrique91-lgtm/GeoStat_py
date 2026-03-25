"""Repository update service isolated from geostat workflow logic."""

from __future__ import annotations

from dataclasses import dataclass
import os
import subprocess

from app.utils.paths import PROJECT_ROOT


@dataclass
class RepoUpdateResult:
    success: bool
    message: str
    details: str
    restart_recommended: bool = False


class RepositoryUpdateService:
    """Handles runtime-safe git update flow."""

    def __init__(self, host_service) -> None:
        self.host = host_service

    def update_repository(self) -> RepoUpdateResult:
        if getattr(self.host, "_repo_update_running", False):
            return RepoUpdateResult(False, "Ya hay una actualización en curso.", "Espera a que finalice el proceso actual.", False)
        if self.host.workflow_state.current_step == "Datos" and self.host.dataframe_write_in_progress():
            return RepoUpdateResult(False, "Actualización no permitida durante escritura activa.", "Espera a que termine el proceso crítico y vuelve a intentar.", False)
        if os.getenv("GEOSTAT_ENABLE_RUNTIME_GIT_UPDATE", "0") != "1":
            message = "Actualización de repositorio deshabilitada en runtime por seguridad."
            details = "Cierra la app y ejecuta `python scripts/update_repo.py` desde terminal."
            self.host.activity_log.log("repo_update_blocked", "warning", message, {"recommended_command": "python scripts/update_repo.py"})
            return RepoUpdateResult(False, message, details, False)

        self.host._repo_update_running = True
        self.host.activity_log.log("repo_update_started", "info", "Iniciando actualización de repositorio.", {})
        try:
            pull_result = subprocess.run(["git", "pull"], cwd=PROJECT_ROOT, capture_output=True, text=True, check=False, timeout=120)
            if pull_result.returncode != 0:
                error_output = (pull_result.stderr or pull_result.stdout).strip()
                return RepoUpdateResult(False, "Falló `git pull`.", error_output or "Error desconocido de git.")

            submodule_result = subprocess.run(
                ["git", "submodule", "update", "--init", "--recursive"],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                check=False,
                timeout=120,
            )
            output = (pull_result.stdout or pull_result.stderr).strip()
            submodule_output = (submodule_result.stdout or submodule_result.stderr).strip()
            if submodule_result.returncode != 0:
                self.host.activity_log.log(
                    "repo_update_failed",
                    "error",
                    "Falló actualización de submódulos.",
                    {"command": "git submodule update --init --recursive", "details": submodule_output},
                )
                return RepoUpdateResult(False, "Falló actualización de submódulos.", submodule_output or "Error desconocido de submódulos.")
            combined = f"git pull:\n{output or '(sin salida)'}\n\nsubmodules:\n{submodule_output or '(sin cambios)'}"
            up_to_date = "Already up to date" in output or "Ya está actualizado" in output
            message = "Repositorio ya estaba actualizado." if up_to_date else "Repositorio actualizado correctamente. Reinicia la app para aplicar cambios."
            self.host.activity_log.log("repo_update_finished", "success", message, {"restart_recommended": not up_to_date})
            return RepoUpdateResult(True, message, combined, not up_to_date)
        except Exception as exc:
            return RepoUpdateResult(False, "No se pudo ejecutar la actualización del repositorio.", f"Detalle técnico: {exc}")
        finally:
            self.host._repo_update_running = False
