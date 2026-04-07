from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.adapters.geostatspy_adapter import GeostatSpyAdapter
from app.services.activity_log_service import ActivityLogService
from app.services.geostat_service import GeostatService


class DomainsNotEnabledRegressionTests(unittest.TestCase):
    def test_configure_domains_is_active_in_main_flow(self) -> None:
        service = GeostatService(adapter=GeostatSpyAdapter(), activity_log=ActivityLogService())
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "domains.csv"
            csv_path.write_text("x,y,z,target,dom,zone\n0,0,0,1,a,z1\n1,1,1,2,a,z1\n2,2,2,3,b,z2\n", encoding="utf-8")
            self.assertTrue(service.load_csv(str(csv_path)).success)
            self.assertTrue(service.set_variable_config("x", "y", "z", "target", domain_column="dom").success)
            result = service.configure_domains(["dom", "zone"], ["dom", "zone"], min_samples=1, include_missing=False)
            self.assertTrue(result.success)
            self.assertNotIn("no habilitada", result.message.lower())


if __name__ == "__main__":
    unittest.main()
