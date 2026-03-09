"""Home panel with workflow placeholders."""

from __future__ import annotations

import customtkinter as ctk

from app.services.geostat_service import GeostatService


class HomePanel(ctk.CTkFrame):
    """Primary panel exposing initial geostatistical workflow actions."""

    def __init__(self, parent: ctk.CTk, service: GeostatService) -> None:
        super().__init__(master=parent)
        self.service = service

        self.status_text = ctk.StringVar(value="Ready. Select a workflow action.")
        self._build_widgets()

    def _build_widgets(self) -> None:
        description = ctk.CTkLabel(
            self,
            text="Initial desktop UI scaffold with placeholders for geostatistical workflows.",
            justify="left",
            anchor="w",
        )
        description.pack(fill="x", padx=16, pady=(16, 12))

        buttons_frame = ctk.CTkFrame(self)
        buttons_frame.pack(fill="x", padx=16, pady=(0, 12))

        actions = [
            ("Cargar CSV", self.service.load_csv_placeholder),
            ("Análisis variográfico", self.service.variogram_placeholder),
            ("Kriging", self.service.kriging_placeholder),
            ("Simulación SGS", self.service.sgs_placeholder),
            ("Visualización", self.service.visualization_placeholder),
        ]

        for label, action in actions:
            button = ctk.CTkButton(
                buttons_frame,
                text=label,
                command=lambda action=action: self._on_action(action),
            )
            button.pack(fill="x", padx=12, pady=6)

        status = ctk.CTkLabel(
            self,
            textvariable=self.status_text,
            anchor="w",
            justify="left",
        )
        status.pack(fill="x", padx=16, pady=(4, 16))

    def _on_action(self, action) -> None:
        message = action()
        self.status_text.set(message)
