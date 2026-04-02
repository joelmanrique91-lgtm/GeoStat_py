"""Application entry point for the local desktop GUI."""

import logging

import customtkinter as ctk

from app.adapters.geostatspy_adapter import GeostatSpyAdapter
from app.services.activity_log_service import ActivityLogService
from app.services.geostat_service import GeostatService
from app.ui.main_window import MainWindow

logger = logging.getLogger(__name__)


def main() -> None:
    """Build and launch the GeoStat desktop app."""
    activity_log = ActivityLogService()
    try:
        ctk.deactivate_automatic_dpi_awareness()
        ctk.set_window_scaling(1.0)
        ctk.set_widget_scaling(1.08)
        adapter = GeostatSpyAdapter()
        service = GeostatService(adapter=adapter, activity_log=activity_log)
        app = MainWindow(service=service)
    except Exception as exc:
        activity_log.log("app_start_failed", "error", f"No se pudo iniciar la aplicación: {exc}", {"error": str(exc)})
        logger.exception("GeoStat startup failed.")
        raise
    service.activity_log.log("app_started", "success", "Aplicación iniciada.", {})
    app.run()


if __name__ == "__main__":
    main()
