from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from app.adapters.geostatspy_adapter import GeostatSpyAdapter
from app.services.activity_log_service import ActivityLogService
from app.services.geostat_service import GeostatService
from scripts.update_and_run import _build_runtime_env


class VariographyBackendUnificationTests(unittest.TestCase):
    def test_app_and_cli_report_same_backend_family(self) -> None:
        service = GeostatService(adapter=GeostatSpyAdapter(), activity_log=ActivityLogService())
        fixture = Path("tests/fixtures/variography/variography_small_numeric.csv")
        self.assertTrue(service.load_csv(str(fixture)).success)
        self.assertTrue(service.set_variable_config("x", "y", "z", "target", domain_column="domain").success)
        self.assertTrue(service.apply_basic_compositing(composite_length=2.0, target_column="target").success)
        self.assertTrue(service.set_variography_domain_bypass(enabled=True, reason="audit").success)
        response = service.compute_experimental_variography(
            {"lag_distance": 10.0, "n_lags": 8, "lag_tolerance": 5.0, "max_distance": 120.0}
        )
        app_backend = str((response.result.metadata if response.result else {}).get("backend_used", ""))
        self.assertIn(app_backend, {"numpy", "numpy+kdtree", "scikit-gstat"})

        with tempfile.TemporaryDirectory() as tmp_dir:
            out = Path(tmp_dir) / "trace.json"
            cmd = [sys.executable, "-m", "cli.geostat_cli", "variogram", "--seed", "7", "--out", str(out)]
            run = subprocess.run(cmd, cwd=Path(__file__).resolve().parents[1], env=_build_runtime_env(), check=True, capture_output=True, text=True)
            self.assertEqual(run.returncode, 0)
            payload = json.loads(out.read_text(encoding="utf-8"))
        cli_backend = str(payload["experimental_variogram"]["metadata"].get("backend", ""))
        self.assertIn(cli_backend, {"numpy", "numpy+kdtree", "scikit-gstat"})


if __name__ == "__main__":
    unittest.main()
