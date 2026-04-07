"""Tests for typed spatial geometry conversion service."""

from __future__ import annotations

import unittest

try:
    import pandas as pd

    HAS_PANDAS = True
except ModuleNotFoundError:
    HAS_PANDAS = False

from app.services.spatial_geometry_service import SpatialGeometryService


@unittest.skipUnless(HAS_PANDAS, "pandas no disponible en este entorno")
class SpatialGeometryServiceTests(unittest.TestCase):
    def test_build_geometry_with_hole_id_builds_trajectories_and_intervals(self) -> None:
        df = pd.DataFrame(
            {
                "x": [0, 1, 2, 10, 11],
                "y": [0, 0, 0, 1, 1],
                "z": [100, 90, 80, 120, 100],
                "au": [1.0, 1.2, 0.8, 2.0, 1.9],
                "hole": ["DH1", "DH1", "DH1", "DH2", "DH2"],
            }
        )
        service = SpatialGeometryService()
        payload = service.build_geometry(
            df,
            x_col="x",
            y_col="y",
            z_col="z",
            color_col="au",
            hole_id_col="hole",
            color_mode="numeric",
            color_tick_positions=None,
            color_tick_labels=None,
        )
        self.assertEqual(payload.point_cloud.rendered_point_count, 5)
        self.assertEqual(len(payload.drillholes), 2)
        self.assertEqual(len(payload.assay_intervals), 2)

    def test_build_geometry_without_hole_id_keeps_point_cloud_only(self) -> None:
        df = pd.DataFrame({"x": [0, 1], "y": [0, 1], "z": [10, 20], "au": [1.0, 2.0]})
        service = SpatialGeometryService()
        payload = service.build_geometry(
            df,
            x_col="x",
            y_col="y",
            z_col="z",
            color_col="au",
            hole_id_col=None,
            color_mode="numeric",
            color_tick_positions=None,
            color_tick_labels=None,
        )
        self.assertEqual(len(payload.drillholes), 0)
        self.assertEqual(len(payload.assay_intervals), 0)


if __name__ == "__main__":
    unittest.main()
