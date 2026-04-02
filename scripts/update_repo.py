"""Safe repository update helper to run outside GUI runtime."""

from __future__ import annotations

import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def run(cmd: list[str]) -> tuple[int, str]:
    result = subprocess.run(cmd, cwd=PROJECT_ROOT, text=True, capture_output=True, check=False)
    output = (result.stdout or result.stderr or "").strip()
    return result.returncode, output


def main() -> int:
    print("[GeoStat] Actualización segura del repositorio (app cerrada).")
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
