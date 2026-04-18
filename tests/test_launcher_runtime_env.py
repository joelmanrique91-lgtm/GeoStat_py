from __future__ import annotations

import os
import unittest

from scripts import update_and_run


class LauncherRuntimeEnvTests(unittest.TestCase):
    def test_build_runtime_env_includes_repo_and_src(self) -> None:
        env = update_and_run._build_runtime_env()
        py_path = env.get("PYTHONPATH", "")
        parts = py_path.split(os.pathsep)
        self.assertGreaterEqual(len(parts), 2)
        self.assertEqual(parts[0], str(update_and_run.PROJECT_ROOT))
        self.assertEqual(parts[1], str(update_and_run.PROJECT_ROOT / "src"))


if __name__ == "__main__":
    unittest.main()
