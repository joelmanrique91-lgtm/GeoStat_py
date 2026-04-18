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

    def test_diagnose_startup_failure_reports_required_module(self) -> None:
        output = "Traceback (most recent call last):\nModuleNotFoundError: No module named 'mining_geostat'"
        hints = update_and_run._diagnose_startup_failure(output)
        self.assertTrue(any("requerida ausente" in hint for hint in hints))
        self.assertTrue(any("Traceback completo" in hint for hint in hints))

    def test_diagnose_startup_failure_reports_ui_failure(self) -> None:
        output = "Traceback (most recent call last):\n_tkinter.TclError: boom"
        hints = update_and_run._diagnose_startup_failure(output)
        self.assertTrue(any("inicialización UI" in hint for hint in hints))


if __name__ == "__main__":
    unittest.main()
