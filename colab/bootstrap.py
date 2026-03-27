"""Utilities for temporary Google Colab bootstrap of GeoStat_py.

This module is intentionally isolated under `colab/` so it can be removed
without affecting desktop/local workflows.
"""

from __future__ import annotations

from dataclasses import dataclass
import importlib
import os
from pathlib import Path
import subprocess
import sys
from typing import Any


@dataclass
class BootstrapConfig:
    repo_url: str
    repo_dir: Path
    branch: str = ""
    mount_drive: bool = False
    drive_mount_point: str = "/content/drive"


@dataclass
class ImportValidationResult:
    module_name: str
    ok: bool
    origin: str
    error: str = ""


def _run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    print(f"$ {' '.join(cmd)}")
    return subprocess.run(cmd, cwd=str(cwd) if cwd else None, text=True, capture_output=True, check=False)


def _print_process_result(result: subprocess.CompletedProcess[str]) -> None:
    if result.stdout.strip():
        print(result.stdout.strip())
    if result.stderr.strip():
        print(result.stderr.strip())
    if result.returncode != 0:
        raise RuntimeError(f"Command failed with code {result.returncode}.")


def mount_drive_if_requested(mount_drive: bool, mount_point: str = "/content/drive") -> bool:
    """Mount Google Drive only when requested."""
    if not mount_drive:
        print("Drive mount skipped (mount_drive=False).")
        return False

    try:
        from google.colab import drive  # type: ignore
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Google Colab drive module unavailable: {exc}") from exc

    print(f"Mounting Google Drive at: {mount_point}")
    drive.mount(mount_point, force_remount=False)
    print("Drive mounted.")
    return True


def clone_or_update_repo(repo_url: str, repo_dir: str | Path, branch: str = "") -> Path:
    """Clone repository if missing; otherwise fetch and pull latest branch."""
    repo_path = Path(repo_dir).expanduser().resolve()
    repo_path.parent.mkdir(parents=True, exist_ok=True)

    if (repo_path / ".git").exists():
        print(f"Repository already exists at {repo_path}; updating.")
        _print_process_result(_run(["git", "fetch", "--all", "--prune"], cwd=repo_path))
        if branch.strip():
            _print_process_result(_run(["git", "checkout", branch.strip()], cwd=repo_path))
            _print_process_result(_run(["git", "pull", "--ff-only", "origin", branch.strip()], cwd=repo_path))
        else:
            _print_process_result(_run(["git", "pull", "--ff-only"], cwd=repo_path))
    else:
        print(f"Cloning repository into {repo_path}")
        clone_cmd = ["git", "clone", repo_url, str(repo_path)]
        if branch.strip():
            clone_cmd = ["git", "clone", "--branch", branch.strip(), repo_url, str(repo_path)]
        _print_process_result(_run(clone_cmd))

    return repo_path


def install_requirements(requirements_path: str | Path) -> None:
    """Install pip requirements for Colab analytical mode."""
    requirements = Path(requirements_path).expanduser().resolve()
    if not requirements.exists():
        raise FileNotFoundError(f"requirements file not found: {requirements}")

    cmd = [sys.executable, "-m", "pip", "install", "-q", "-r", str(requirements)]
    _print_process_result(_run(cmd))
    print("Dependencies installed.")


def configure_sys_path(repo_root: str | Path) -> Path:
    """Ensure repo root is first in sys.path for deterministic imports."""
    root = Path(repo_root).expanduser().resolve()
    if not root.exists():
        raise FileNotFoundError(f"Repo root not found: {root}")

    root_str = str(root)
    if root_str in sys.path:
        sys.path.remove(root_str)
    sys.path.insert(0, root_str)
    os.environ["GEOSTAT_REPO_ROOT"] = root_str
    print(f"sys.path[0] set to: {root_str}")
    return root


def validate_imports(module_names: list[str]) -> list[ImportValidationResult]:
    """Import modules and return their origin paths for visual confirmation."""
    results: list[ImportValidationResult] = []
    for module_name in module_names:
        try:
            module = importlib.import_module(module_name)
            origin = str(getattr(module, "__file__", "<built-in>"))
            results.append(ImportValidationResult(module_name=module_name, ok=True, origin=origin))
        except Exception as exc:  # noqa: BLE001
            results.append(ImportValidationResult(module_name=module_name, ok=False, origin="", error=str(exc)))
    return results


def create_service() -> Any:
    """Create GeostatService without invoking any desktop UI layer."""
    from app.adapters.geostatspy_adapter import GeostatSpyAdapter
    from app.services.geostat_service import GeostatService

    service = GeostatService(adapter=GeostatSpyAdapter())
    return service


def optional_csv_smoke_check(service: Any, csv_path: str = "") -> dict[str, Any]:
    """Run an optional safe smoke flow if csv_path is provided and valid.

    The flow intentionally avoids UI calls and keeps all operations in service layer.
    """
    cleaned = str(csv_path or "").strip()
    if not cleaned:
        return {
            "executed": False,
            "ok": True,
            "message": "CSV smoke check skipped (no csv_path provided).",
        }

    path = Path(cleaned)
    if not path.exists():
        return {
            "executed": True,
            "ok": False,
            "message": f"CSV path not found: {path}",
        }

    load_result = service.load_csv(str(path))
    response: dict[str, Any] = {
        "executed": True,
        "ok": bool(load_result.success),
        "load_message": load_result.message,
        "load_details": load_result.details,
    }
    if not load_result.success:
        return response

    cols = service.get_available_columns()
    guesses = service.get_autodetected_columns()
    x_col = guesses.get("x", "")
    y_col = guesses.get("y", "")
    z_col = guesses.get("z", "")
    target_col = guesses.get("target", "")

    if all([x_col, y_col, z_col, target_col]):
        cfg = service.set_variable_config(x_column=x_col, y_column=y_col, z_column=z_col, target_column=target_col)
        response["autoconfig_attempted"] = True
        response["autoconfig_ok"] = bool(cfg.success)
        response["autoconfig_message"] = cfg.message
    else:
        response["autoconfig_attempted"] = False
        response["autoconfig_ok"] = False
        response["autoconfig_message"] = "No se pudieron inferir X/Y/Z/target automáticamente."

    response["available_columns"] = cols
    response["autodetected_columns"] = guesses

    if response.get("autoconfig_ok"):
        try:
            stats = service.get_target_statistics_table()
            response["target_stats_preview"] = stats[:5]
            response["analysis_smoke_ok"] = True
        except Exception as exc:  # noqa: BLE001
            response["analysis_smoke_ok"] = False
            response["analysis_smoke_error"] = str(exc)
    return response


def environment_snapshot(repo_root: str | Path = "") -> dict[str, str]:
    """Return visible environment diagnostics for notebook output."""
    root = str(Path(repo_root).resolve()) if repo_root else ""
    return {
        "python_version": sys.version.replace("\n", " "),
        "python_executable": sys.executable,
        "cwd": str(Path.cwd()),
        "repo_root": root,
        "sys_path_0": sys.path[0] if sys.path else "",
    }
