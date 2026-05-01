from __future__ import annotations


class DomainError(Exception):
    """Base exception for geostat domain errors."""


class VariographyError(DomainError):
    """Variography-specific failures."""


class KrigingError(DomainError):
    """Kriging-specific failures."""


class DatasetError(DomainError):
    """Dataset-level validation failures."""
