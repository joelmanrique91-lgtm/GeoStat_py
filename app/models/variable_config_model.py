"""Model for spatial and target variable selection."""

from dataclasses import dataclass


@dataclass
class VariableConfigModel:
    """Selected columns used by downstream geostatistical workflows."""

    x_column: str
    y_column: str
    z_column: str
    target_column: str
    hole_id_column: str | None = None
    domain_column: str | None = None
