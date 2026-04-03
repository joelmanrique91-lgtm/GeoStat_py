"""Unit tests for directional geometry rules used by variography."""

from __future__ import annotations

import unittest

from app.services.variography_geometry import DirectionalConfig, pair_matches_direction


class VariographyGeometryTests(unittest.TestCase):
    def test_directional_config_validation(self) -> None:
        cfg = DirectionalConfig(
            azimuth_deg=0.0,
            dip_deg=120.0,
            azimuth_tolerance_deg=95.0,
            dip_tolerance_deg=0.0,
            band_width=-1.0,
            band_height=-2.0,
        )
        errors = cfg.validate()
        self.assertGreaterEqual(len(errors), 4)

    def test_pair_matches_direction_for_axis_aligned_vector(self) -> None:
        cfg = DirectionalConfig(
            azimuth_deg=0.0,
            dip_deg=0.0,
            azimuth_tolerance_deg=10.0,
            dip_tolerance_deg=10.0,
            band_width=0.0,
            band_height=0.0,
        )
        self.assertTrue(pair_matches_direction(10.0, 0.0, 0.0, cfg))
        self.assertTrue(pair_matches_direction(-10.0, 0.0, 0.0, cfg))  # axial symmetry
        self.assertFalse(pair_matches_direction(0.0, 10.0, 0.0, cfg))

    def test_pair_matches_direction_respects_bandwidth(self) -> None:
        cfg = DirectionalConfig(
            azimuth_deg=0.0,
            dip_deg=0.0,
            azimuth_tolerance_deg=90.0,
            dip_tolerance_deg=90.0,
            band_width=4.0,
            band_height=0.0,
        )
        self.assertTrue(pair_matches_direction(10.0, 1.0, 0.0, cfg))
        self.assertFalse(pair_matches_direction(10.0, 3.0, 0.0, cfg))


if __name__ == "__main__":
    unittest.main()

