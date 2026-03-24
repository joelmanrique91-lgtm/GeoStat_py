"""Tests for domain context behavior."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

try:
    import pandas  # noqa: F401

    HAS_PANDAS = True
except ModuleNotFoundError:
    HAS_PANDAS = False

from app.adapters.geostatspy_adapter import GeostatSpyAdapter
from app.services.geostat_service import GeostatService


@unittest.skipUnless(HAS_PANDAS, "pandas no disponible en este entorno")
class DomainEstimationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = GeostatService(adapter=GeostatSpyAdapter())

    def _load_dataset(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "domains.csv"
            csv_path.write_text(
                "x,y,z,target,Minz,Lito\n0,0,0,10,A,L1\n1,1,1,12,B,L1\n2,2,2,14,C,L2\n3,3,3,9,D,L3\n",
                encoding="utf-8",
            )
            self.assertTrue(self.service.load_csv(str(csv_path)).success)
            self.assertTrue(self.service.set_variable_config("x", "y", "z", "target", domain_column="Lito").success)

    def test_apply_domain_definition_is_disabled(self) -> None:
        self._load_dataset()
        result = self.service.apply_domain_definition(
            {"variable_base": "Minz", "domains": {"D1": ["A", "B", "C"], "D2": ["D"]}}
        )
        self.assertFalse(result.success)

    def test_confirm_domain_assignment_is_disabled(self) -> None:
        self._load_dataset()
        result = self.service.confirm_domain_assignment("D1")
        self.assertFalse(result.success)
        state = self.service.get_domain_state()
        self.assertEqual(state["assignment_history"], [])

    def test_univariate_payload_keeps_contract_with_disabled_domain_boxplot(self) -> None:
        self._load_dataset()
        payload = self.service.prepare_univariate_data()
        self.assertIn("domain_boxplot", payload)
        self.assertTrue(payload["domain_boxplot"]["enabled"])
        self.assertGreaterEqual(len(payload["domain_boxplot"]["labels"]), 2)


if __name__ == "__main__":
    unittest.main()
