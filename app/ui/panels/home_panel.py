"""Home panel with workflow placeholders."""

from __future__ import annotations

from tkinter import filedialog

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
            text="Carga CSV habilitada. Usa el botón para seleccionar un archivo local.",
            justify="left",
            anchor="w",
        )
        description.pack(fill="x", padx=16, pady=(16, 12))

        buttons_frame = ctk.CTkFrame(self)
        buttons_frame.pack(fill="x", padx=16, pady=(0, 12))

        actions = [
            ("Cargar CSV", self._on_load_csv),
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

        status = ctk.CTkLabel(self, textvariable=self.status_text, anchor="w", justify="left")
        status.pack(fill="x", padx=16, pady=(4, 8))

        self.summary_box = ctk.CTkTextbox(self, height=260)
        self.summary_box.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        self.summary_box.insert("1.0", "Sin dataset cargado todavía.")
        self.summary_box.configure(state="disabled")

    def _on_action(self, action) -> None:
        message = action()
        self.status_text.set(message)

    def _on_load_csv(self) -> str:
        file_path = filedialog.askopenfilename(
            title="Seleccionar archivo CSV",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )

        if not file_path:
            return "Carga cancelada por el usuario."

        result = self.service.load_csv(file_path)
        self.status_text.set(result.message)
        self._update_summary(result.details)
        return result.message

    def _update_summary(self, text: str) -> None:
        self.summary_box.configure(state="normal")
        self.summary_box.delete("1.0", "end")
        self.summary_box.insert("1.0", text)
        self.summary_box.configure(state="disabled")
