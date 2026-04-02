"""Safe repository update helper to run outside GUI runtime."""

from __future__ import annotations

from pathlib import Path
import sys

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.append(str(CURRENT_DIR))

from repo_ops import git_path, is_git_repo, run_capture


def run(cmd: list[str]) -> tuple[int, str]:
    return run_capture(cmd)


def main() -> int:
    print("[GeoStat] Actualización segura del repositorio (app cerrada).")

    detected_git = git_path()
    if detected_git is None:
        print("\nError: Git no encontrado en PATH.")
        return 1

    if not is_git_repo():
        print("\nError: el directorio actual no es un repositorio Git válido.")
        return 1

    code, out = run(["git", "pull", "--ff-only"])
    print("\n$ git pull --ff-only")
    print(out or "(sin salida)")
    if code != 0:
        print("\nError: falló git pull.")
        return code

    code, out = run(["git", "submodule", "update", "--init", "--recursive"])
    print("\n$ git submodule update --init --recursive")
    print(out or "(sin salida)")
    if code != 0:
        print("\nError: falló actualización de submódulos.")
        return code

    print("\nActualización finalizada. Reinicia la app.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
