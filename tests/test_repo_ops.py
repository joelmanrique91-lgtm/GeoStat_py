"""Unit tests for shared repository operation helpers."""

from __future__ import annotations

import subprocess
import unittest
from unittest.mock import patch

from scripts import repo_ops


class RepoOpsTests(unittest.TestCase):
    def test_normalize_output_combines_stdout_and_stderr(self) -> None:
        out = repo_ops.normalize_output("ok\n", "warn\n")
        self.assertEqual(out, "ok\nwarn")

    @patch("scripts.repo_ops.subprocess.run")
    def test_run_capture_uses_project_root_and_returns_combined_output(self, run_mock) -> None:
        run_mock.return_value = subprocess.CompletedProcess(
            args=["git", "status"],
            returncode=0,
            stdout="line1\n",
            stderr="",
        )
        code, output = repo_ops.run_capture(["git", "status"])

        self.assertEqual(code, 0)
        self.assertEqual(output, "line1")
        run_mock.assert_called_once()
        self.assertEqual(run_mock.call_args.kwargs["cwd"], repo_ops.PROJECT_ROOT)

    @patch("scripts.repo_ops.run_capture", return_value=(0, "true"))
    def test_is_git_repo_true(self, run_capture_mock) -> None:
        self.assertTrue(repo_ops.is_git_repo())
        run_capture_mock.assert_called_once_with(["git", "rev-parse", "--is-inside-work-tree"])

    @patch("scripts.repo_ops.run_capture", return_value=(1, ""))
    def test_is_git_repo_false(self, run_capture_mock) -> None:
        self.assertFalse(repo_ops.is_git_repo())
        run_capture_mock.assert_called_once_with(["git", "rev-parse", "--is-inside-work-tree"])


if __name__ == "__main__":
    unittest.main()
