"""Home panel with workflow placeholders."""

from __future__ import annotations

from tkinter import filedialog
import threading

import customtkinter as ctk

from app.services.geostat_service import GeostatService


class HomePanel(ctk.CTkFrame):
    """Primary panel exposing initial geostatistical workflow actions."""

    def __init__(self, parent: ctk.CTk, service: GeostatService) -> None:
        super().__init__(master=parent)
        self.service = service

        self.status_text = ctk.StringVar(value="Ready. Select a workflow action.")
        self.x_var = ctk.StringVar(value="")
        self.y_var = ctk.StringVar(value="")
        self.z_var = ctk.StringVar(value="")
        self.target_var = ctk.StringVar(value="")
        self._build_widgets()

    def _build_widgets(self) -> None:
        toolbar = ctk.CTkFrame(self)
        toolbar.pack(fill="x", padx=16, pady=(16, 8))

        description = ctk.CTkLabel(
            toolbar,
            text="Carga CSV + configuración X/Y/Z/target + EDA inicial.",
            justify="left",
            anchor="w",
        )
        description.pack(side="left", padx=10, pady=8)

        self.update_repo_button = ctk.CTkButton(
            toolbar,
            text="Actualizar repo",
            width=140,
            command=self._on_update_repo,
        )
        self.update_repo_button.pack(side="right", padx=10, pady=8)

        buttons_frame = ctk.CTkFrame(self)
        buttons_frame.pack(fill="x", padx=16, pady=(0, 8))

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

        self._build_variable_selectors()

        status = ctk.CTkLabel(self, textvariable=self.status_text, anchor="w", justify="left")
        status.pack(fill="x", padx=16, pady=(4, 8))

        self.summary_box = ctk.CTkTextbox(self, height=200)
        self.summary_box.pack(fill="both", expand=True, padx=16, pady=(0, 10))
        self.summary_box.insert("1.0", "Sin dataset cargado todavía.")
        self.summary_box.configure(state="disabled")

        self.eda_box = ctk.CTkTextbox(self, height=220)
        self.eda_box.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        self.eda_box.insert("1.0", "EDA inicial aparecerá aquí tras configurar X/Y/Z/target.")
        self.eda_box.configure(state="disabled")

    def _build_variable_selectors(self) -> None:
        selector_frame = ctk.CTkFrame(self)
        selector_frame.pack(fill="x", padx=16, pady=(0, 8))

        selector_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.x_menu = self._build_selector(selector_frame, 0, "X", self.x_var)
        self.y_menu = self._build_selector(selector_frame, 1, "Y", self.y_var)
        self.z_menu = self._build_selector(selector_frame, 2, "Z", self.z_var)
        self.target_menu = self._build_selector(selector_frame, 3, "Target", self.target_var)

        apply_button = ctk.CTkButton(
            selector_frame,
            text="Aplicar configuración",
            command=self._on_apply_variable_config,
        )
        apply_button.grid(row=2, column=0, columnspan=4, sticky="ew", padx=8, pady=(8, 10))

        self._set_selectors_enabled(False)

    def _build_selector(self, parent: ctk.CTkFrame, column: int, label: str, variable: ctk.StringVar) -> ctk.CTkOptionMenu:
        ctk.CTkLabel(parent, text=label, anchor="w").grid(row=0, column=column, sticky="w", padx=8, pady=(8, 2))
        menu = ctk.CTkOptionMenu(parent, variable=variable, values=[""], state="disabled")
        menu.grid(row=1, column=column, sticky="ew", padx=8, pady=(0, 8))
        return menu

    def _set_selectors_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        for menu in [self.x_menu, self.y_menu, self.z_menu, self.target_menu]:
            menu.configure(state=state)

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

        if result.success:
            columns = self.service.get_available_columns()
            self._populate_selectors(columns)
            self._update_eda(self.service.build_eda_summary())
        return result.message

    def _populate_selectors(self, columns: list[str]) -> None:
        if not columns:
            self._set_selectors_enabled(False)
            return

        for variable in [self.x_var, self.y_var, self.z_var, self.target_var]:
            variable.set(columns[0])

        for menu in [self.x_menu, self.y_menu, self.z_menu, self.target_menu]:
            menu.configure(values=columns)

        self._set_selectors_enabled(True)

    def _on_apply_variable_config(self) -> None:
        result = self.service.set_variable_config(
            x_column=self.x_var.get(),
            y_column=self.y_var.get(),
            z_column=self.z_var.get(),
            target_column=self.target_var.get(),
        )
        self.status_text.set(result.message)
        self._update_eda(result.eda_summary)

    def _on_update_repo(self) -> None:
        self.status_text.set("Actualizando repositorio...")
        self.update_repo_button.configure(state="disabled")

        def worker() -> None:
            result = self.service.update_repository()
            self.after(0, lambda: self._finish_repo_update(result.message, result.details))

        threading.Thread(target=worker, daemon=True).start()

    def _finish_repo_update(self, message: str, details: str) -> None:
        self.status_text.set(message)
        self._update_eda(f"{self._current_eda_text()}\n\n[Update repo]\n{details}")
        self.update_repo_button.configure(state="normal")

    def _current_eda_text(self) -> str:
        self.eda_box.configure(state="normal")
        text = self.eda_box.get("1.0", "end").strip()
        self.eda_box.configure(state="disabled")
        return text

    def _update_summary(self, text: str) -> None:
        self.summary_box.configure(state="normal")
        self.summary_box.delete("1.0", "end")
        self.summary_box.insert("1.0", text)
        self.summary_box.configure(state="disabled")

    def _update_eda(self, text: str) -> None:
        self.eda_box.configure(state="normal")
        self.eda_box.delete("1.0", "end")
        self.eda_box.insert("1.0", text)
        self.eda_box.configure(state="disabled")
