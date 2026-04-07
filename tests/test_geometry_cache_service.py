"""Unit tests for geometry cache service."""

from __future__ import annotations

import unittest

from app.services.geometry_cache_service import GeometryCacheService


class GeometryCacheServiceTests(unittest.TestCase):
    def test_put_get_and_invalidate(self) -> None:
        cache = GeometryCacheService()
        key = cache.build_key(
            dataset_signature="d1",
            active_domain="A",
            active_variable="au",
            view_mode="3d",
            filters={"active_domain_filter": "A"},
        )
        cache.put(key, {"ok": True})
        self.assertEqual(cache.size(), 1)
        self.assertEqual(cache.get(key), {"ok": True})
        cache.invalidate(dataset_signature="d1")
        self.assertEqual(cache.size(), 0)

    def test_filter_signature_affects_key(self) -> None:
        cache = GeometryCacheService()
        k1 = cache.build_key(dataset_signature="d", active_domain="A", active_variable="au", view_mode="3d", filters={"f": "1"})
        k2 = cache.build_key(dataset_signature="d", active_domain="A", active_variable="au", view_mode="3d", filters={"f": "2"})
        self.assertNotEqual(k1, k2)


if __name__ == "__main__":
    unittest.main()
