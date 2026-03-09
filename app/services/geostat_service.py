"""Service layer for geostatistical workflows."""

from __future__ import annotations

from app.adapters.geostatspy_adapter import GeostatSpyAdapter


class GeostatService:
    """Mediates between UI actions and adapter calls."""

    def __init__(self, adapter: GeostatSpyAdapter) -> None:
        self.adapter = adapter

    def load_csv_placeholder(self) -> str:
        return "[Placeholder] Flujo de carga CSV listo para implementar."

    def variogram_placeholder(self) -> str:
        availability = self.adapter.describe_availability()
        return f"[Placeholder] Análisis variográfico pendiente. {availability}"

    def kriging_placeholder(self) -> str:
        return "[Placeholder] Módulo de kriging pendiente de implementación."

    def sgs_placeholder(self) -> str:
        return "[Placeholder] Simulación SGS pendiente de implementación."

    def visualization_placeholder(self) -> str:
        return "[Placeholder] Visualización pendiente de implementación."
