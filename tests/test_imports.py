"""Minimal smoke tests for package imports and basic wiring."""

import unittest

from app.adapters.geostatspy_adapter import GeostatSpyAdapter
from app.services.geostat_service import GeostatService


class ImportSmokeTests(unittest.TestCase):
    def test_adapter_and_service_wiring(self) -> None:
        adapter = GeostatSpyAdapter()
        service = GeostatService(adapter=adapter)

        message = service.variogram_placeholder()
        self.assertIsInstance(message, str)
        self.assertIn("no implementada", message)


if __name__ == "__main__":
    unittest.main()
