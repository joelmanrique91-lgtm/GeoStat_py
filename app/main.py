"""Application entry point for the local desktop GUI."""

from app.adapters.geostatspy_adapter import GeostatSpyAdapter
from app.services.geostat_service import GeostatService
from app.ui.main_window import MainWindow


def main() -> None:
    """Build and launch the GeoStat desktop app."""
    adapter = GeostatSpyAdapter()
    service = GeostatService(adapter=adapter)
    app = MainWindow(service=service)
    app.run()


if __name__ == "__main__":
    main()
