"""Adapter isolating direct interactions with the GeostatsPy submodule."""

from __future__ import annotations

from importlib import import_module


class GeostatSpyAdapter:
    """Encapsulates GeostatsPy import checks and future API calls."""

    MODULE_CANDIDATES = ("geostatspy", "geostatspy.geostats")

    def describe_availability(self) -> str:
        """Return a human-readable status for GeostatsPy availability."""
        module = self._import_first_available()
        if module is None:
            return (
                "GeostatsPy no está importable aún. "
                "Verifica `git submodule update --init --recursive`."
            )
        return f"GeostatsPy detectado ({module.__name__})."

    def _import_first_available(self):
        for module_name in self.MODULE_CANDIDATES:
            try:
                return import_module(module_name)
            except ModuleNotFoundError:
                continue
        return None
