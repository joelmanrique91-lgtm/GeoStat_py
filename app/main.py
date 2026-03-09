"""Application entry point for the local desktop GUI."""

from app.adapters.geostatspy_adapter import GeostatSpyAdapter
from app.services.activity_log_service import ActivityLogService
from app.services.geostat_service import GeostatService
from app.ui.main_window import MainWindow


def main() -> None:
    """Build and launch the GeoStat desktop app."""
    adapter = GeostatSpyAdapter()
    activity_log = ActivityLogService()
    service = GeostatService(adapter=adapter, activity_log=activity_log)
    service.activity_log.log("app_started", "success", "Aplicación iniciada.", {})
    app = MainWindow(service=service)
    app.run()


if __name__ == "__main__":
    main()
