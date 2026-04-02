"""Bootstrap logging semantics for app.main."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

import app.main as app_main


class MainBootstrapTests(unittest.TestCase):
    def test_main_logs_started_only_after_window_is_built(self) -> None:
        with patch("app.main.ctk.deactivate_automatic_dpi_awareness"), patch("app.main.ctk.set_window_scaling"), patch(
            "app.main.ctk.set_widget_scaling"
        ), patch("app.main.GeostatSpyAdapter"), patch("app.main.ActivityLogService") as activity_log_cls, patch(
            "app.main.GeostatService"
        ) as service_cls, patch("app.main.MainWindow") as main_window_cls:
            activity_log = MagicMock()
            activity_log_cls.return_value = activity_log
            service = MagicMock()
            service.activity_log = activity_log
            service_cls.return_value = service
            app = MagicMock()
            main_window_cls.return_value = app

            app_main.main()

            activity_log.log.assert_any_call("app_started", "success", "Aplicación iniciada.", {})
            app.run.assert_called_once()

    def test_main_logs_bootstrap_failure_and_raises(self) -> None:
        with patch("app.main.ctk.deactivate_automatic_dpi_awareness"), patch("app.main.ctk.set_window_scaling"), patch(
            "app.main.ctk.set_widget_scaling"
        ), patch("app.main.GeostatSpyAdapter"), patch("app.main.ActivityLogService") as activity_log_cls, patch(
            "app.main.GeostatService"
        ) as service_cls, patch("app.main.MainWindow", side_effect=RuntimeError("boom")):
            activity_log = MagicMock()
            activity_log_cls.return_value = activity_log
            service = MagicMock()
            service.activity_log = activity_log
            service_cls.return_value = service

            with self.assertRaises(RuntimeError):
                app_main.main()

            first_event = activity_log.log.call_args_list[0].args[0]
            self.assertEqual(first_event, "app_start_failed")


if __name__ == "__main__":
    unittest.main()
