"""Shared repository operation helpers for maintenance scripts."""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def normalize_output(stdout: str | None, stderr: str | None) -> str:
    """Return combined non-empty process output."""
    return "\n".join(part for part in [(stdout or "").strip(), (stderr or "").strip()] if part).strip()


def run_capture(command: list[str], *, timeout: int = 180) -> tuple[int, str]:
    """Run a command at project root and return status code + combined output."""
    result = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=timeout,
    )
    return result.returncode, normalize_output(result.stdout, result.stderr)


def git_path() -> str | None:
    """Return git executable path when available in PATH."""
    return shutil.which("git")


def is_git_repo() -> bool:
    """Return whether project root is inside a valid git work tree."""
    code, _ = run_capture(["git", "rev-parse", "--is-inside-work-tree"])
    return code == 0
