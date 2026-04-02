"""Directional geometry helpers for experimental variography.

Conventions (explicit for auditability):
- Azimuth is measured in degrees on XY plane from +X towards +Y (right-handed).
- Dip is measured in degrees from horizontal plane: +90 up, -90 down.
- Pair direction is axial (bidirectional): v and -v are equivalent for variography.
"""

from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class DirectionalConfig:
    azimuth_deg: float
    dip_deg: float
    azimuth_tolerance_deg: float
    dip_tolerance_deg: float
    band_width: float
    band_height: float

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not (-360.0 <= float(self.azimuth_deg) <= 360.0):
            errors.append("azimuth debe estar en [-360, 360].")
        if not (-90.0 <= float(self.dip_deg) <= 90.0):
            errors.append("dip debe estar en [-90, 90].")
        if not (0.0 < float(self.azimuth_tolerance_deg) <= 90.0):
            errors.append("ang_tol_h debe estar en (0, 90].")
        if not (0.0 < float(self.dip_tolerance_deg) <= 90.0):
            errors.append("ang_tol_v debe estar en (0, 90].")
        if float(self.band_width) < 0.0:
            errors.append("band_width no puede ser negativo.")
        if float(self.band_height) < 0.0:
            errors.append("band_height no puede ser negativo.")
        return errors


def _unit_direction_from_angles(azimuth_deg: float, dip_deg: float) -> tuple[float, float, float]:
    az = math.radians(float(azimuth_deg))
    dip = math.radians(float(dip_deg))
    cos_dip = math.cos(dip)
    return (cos_dip * math.cos(az), cos_dip * math.sin(az), math.sin(dip))


def _clip(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _axial_angle_deg(vx: float, vy: float, vz: float, ux: float, uy: float, uz: float) -> float:
    """Return acute angle [0, 90] between vector and axis direction (axial symmetry)."""
    v_norm = math.sqrt(vx * vx + vy * vy + vz * vz)
    if v_norm <= 1e-15:
        return 0.0
    dot = (vx * ux + vy * uy + vz * uz) / v_norm
    dot = abs(_clip(dot, -1.0, 1.0))
    return math.degrees(math.acos(dot))


def pair_matches_direction(dx: float, dy: float, dz: float, config: DirectionalConfig) -> bool:
    ux, uy, uz = _unit_direction_from_angles(config.azimuth_deg, config.dip_deg)
    axial_angle = _axial_angle_deg(dx, dy, dz, ux, uy, uz)
    if axial_angle > float(config.azimuth_tolerance_deg):
        return False

    horizontal = math.sqrt(dx * dx + dy * dy)
    pair_dip = math.degrees(math.atan2(dz, horizontal))
    dip_mirror = min(abs(pair_dip - config.dip_deg), abs((-pair_dip) - config.dip_deg))
    if dip_mirror > float(config.dip_tolerance_deg):
        return False

    # Lateral offset to principal direction axis.
    proj = dx * ux + dy * uy + dz * uz
    perp_sq = max(0.0, dx * dx + dy * dy + dz * dz - proj * proj)
    lateral = math.sqrt(perp_sq)
    if config.band_width > 0.0 and lateral > (float(config.band_width) * 0.5):
        return False
    if config.band_height > 0.0 and abs(dz) > (float(config.band_height) * 0.5):
        return False
    return True

