from __future__ import annotations

import sys

from scripts.update_and_run import PROJECT_ROOT


def pytest_sessionstart(session) -> None:  # pragma: no cover - pytest bootstrap
    repo_root = str(PROJECT_ROOT)
    repo_src = str(PROJECT_ROOT / "src")
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
    if repo_src not in sys.path:
        sys.path.insert(0, repo_src)
