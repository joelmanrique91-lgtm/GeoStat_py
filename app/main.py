"""Application entry point for the local desktop GUI."""

import customtkinter as ctk

from app.adapters.geostatspy_adapter import GeostatSpyAdapter
from app.services.activity_log_service import ActivityLogService
from app.services.geostat_service import GeostatService
from app.ui.main_window import MainWindow


def _configure_windows_dpi_awareness() -> None:
    """Configure a conservative Windows DPI-awareness mode before Tk init."""
    if sys.platform != "win32":
        return
    try:
        # Per-monitor DPI awareness v1 (supported on modern Windows).
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # type: ignore[attr-defined]
        return
    except Exception:
        pass
    try:
        # Legacy fallback available on older Windows builds.
        ctypes.windll.user32.SetProcessDPIAware()  # type: ignore[attr-defined]
    except Exception:
        return


def main() -> None:
    """Build and launch the GeoStat desktop app."""
    ctk.deactivate_automatic_dpi_awareness()
    ctk.set_window_scaling(1.0)
    ctk.set_widget_scaling(1.08)
    adapter = GeostatSpyAdapter()
    activity_log = ActivityLogService()
    service = GeostatService(adapter=adapter, activity_log=activity_log)
    service.activity_log.log("app_started", "success", "Aplicación iniciada.", {})
    app = MainWindow(service=service)
    app.run()


if __name__ == "__main__":
    main()
