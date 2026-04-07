from __future__ import annotations

import tempfile
import unittest
import warnings
from pathlib import Path

from app.adapters.geostatspy_adapter import GeostatSpyAdapter
from app.services.activity_log_service import ActivityLogService
from app.services.geostat_service import GeostatService


class CompositingWarningFreeTests(unittest.TestCase):
    def test_apply_basic_compositing_does_not_emit_incompatible_dtype_futurewarning(self) -> None:
        service = GeostatService(adapter=GeostatSpyAdapter(), activity_log=ActivityLogService())
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "composite.csv"
            csv_path.write_text(
                "x,y,z,target,hole,from,to\n0,0,0,1,H1,0,1\n1,1,1,2,H1,1,2\n2,2,2,3,H2,0,1\n3,3,3,4,H2,1,2\n",
                encoding="utf-8",
            )
            self.assertTrue(service.load_csv(str(csv_path)).success)
            self.assertTrue(service.set_variable_config("x", "y", "z", "target", hole_id_column="hole").success)
            with warnings.catch_warnings(record=True) as captured:
                warnings.simplefilter("always")
                result = service.apply_basic_compositing(composite_length=2.0, target_column="target", output_column="target_comp")
            self.assertTrue(result.success)
            incompatible_warnings = [
                item
                for item in captured
                if issubclass(item.category, FutureWarning) and "incompatible dtype" in str(item.message).lower()
            ]
            self.assertEqual(incompatible_warnings, [])


if __name__ == "__main__":
    unittest.main()
