"""Main dashboard panel for geostatistical workflow."""

from __future__ import annotations

from tkinter import filedialog
import threading

import customtkinter as ctk

from app.services.geostat_service import GeostatService


class HomePanel(ctk.CTkFrame):
    """Professionalized desktop layout with dataset, config, EDA, modules and logs."""

    def __init__(self, parent: ctk.CTk, service: GeostatService) -> None:
        super().__init__(master=parent)
        self.service = service

        self.status_text = ctk.StringVar(value="Listo para trabajar.")
        self.dataset_status = ctk.StringVar(value="Dataset: no cargado")
        self.active_config = ctk.StringVar(value="Configuración activa: sin definir")
        self.x_var = ctk.StringVar(value="")
        self.y_var = ctk.StringVar(value="")
        self.z_var = ctk.StringVar(value="")
        self.target_var = ctk.StringVar(value="")

        self._build_layout()

    def _build_layout(self) -> None:
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_header().grid(row=0, column=0, sticky="ew", pady=(0, 10))

        top = ctk.CTkFrame(self)
        top.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        top.grid_columnconfigure((0, 1), weight=1)

        self._build_dataset_panel(top).grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self._build_config_panel(top).grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        center = ctk.CTkFrame(self)
        center.grid(row=2, column=0, sticky="nsew")
        center.grid_columnconfigure((0, 1), weight=1)
        center.grid_rowconfigure(0, weight=1)

        self._build_eda_panel(center).grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self._build_modules_panel(center).grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        status = ctk.CTkLabel(self, textvariable=self.status_text, anchor="w")
        status.grid(row=3, column=0, sticky="ew", pady=(10, 0))

    def _build_header(self) -> ctk.CTkFrame:
        header = ctk.CTkFrame(self)
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text="GeoStat Py | Workspace geostatístico local",
            font=ctk.CTkFont(size=20, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(10, 4))

        ctk.CTkLabel(header, textvariable=self.dataset_status, anchor="w").grid(
            row=1, column=0, sticky="w", padx=12, pady=(0, 10)
        )

        button_frame = ctk.CTkFrame(header, fg_color="transparent")
        button_frame.grid(row=0, column=1, rowspan=2, sticky="e", padx=10)

        self.update_repo_button = ctk.CTkButton(button_frame, text="Actualizar repo", width=140, command=self._on_update_repo)
        self.update_repo_button.pack(side="left", padx=6)
        self.export_log_button = ctk.CTkButton(button_frame, text="Exportar log", width=130, command=self._on_export_log)
        self.export_log_button.pack(side="left", padx=6)

        return header

    def _build_dataset_panel(self, parent: ctk.CTkFrame) -> ctk.CTkFrame:
        panel = ctk.CTkFrame(parent)
        panel.grid_rowconfigure(2, weight=1)
        panel.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(panel, text="1) Dataset", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=0, sticky="w", padx=12, pady=(10, 6)
        )
        ctk.CTkButton(panel, text="Cargar CSV", command=self._on_load_csv).grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 8))

        self.dataset_box = ctk.CTkTextbox(panel, height=180)
        self.dataset_box.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self.dataset_box.insert("1.0", "Carga un CSV para comenzar.")
        self.dataset_box.configure(state="disabled")
        return panel

    def _build_config_panel(self, parent: ctk.CTkFrame) -> ctk.CTkFrame:
        panel = ctk.CTkFrame(parent)
        panel.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(panel, text="2) Configuración espacial", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=12, pady=(10, 6)
        )

        self.x_menu = self._selector(panel, "X", self.x_var, 1, 0)
        self.y_menu = self._selector(panel, "Y", self.y_var, 1, 1)
        self.z_menu = self._selector(panel, "Z", self.z_var, 3, 0)
        self.target_menu = self._selector(panel, "Target", self.target_var, 3, 1)

        self.apply_config_button = ctk.CTkButton(
            panel, text="Aplicar configuración", command=self._on_apply_variable_config, state="disabled"
        )
        self.apply_config_button.grid(row=5, column=0, columnspan=2, sticky="ew", padx=12, pady=(8, 8))

        ctk.CTkLabel(panel, textvariable=self.active_config, anchor="w", justify="left").grid(
            row=6, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 12)
        )
        return panel

    def _build_eda_panel(self, parent: ctk.CTkFrame) -> ctk.CTkFrame:
        panel = ctk.CTkFrame(parent)
        panel.grid_rowconfigure(1, weight=1)
        panel.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(panel, text="3) EDA inicial", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=0, sticky="w", padx=12, pady=(10, 6)
        )
        self.eda_box = ctk.CTkTextbox(panel)
        self.eda_box.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self.eda_box.insert("1.0", "EDA disponible una vez cargado el dataset y aplicada la configuración.")
        self.eda_box.configure(state="disabled")
        return panel

    def _build_modules_panel(self, parent: ctk.CTkFrame) -> ctk.CTkFrame:
        panel = ctk.CTkFrame(parent)
        panel.grid_rowconfigure(2, weight=1)
        panel.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(panel, text="4) Workflows geostatísticos", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=0, sticky="w", padx=12, pady=(10, 6)
        )
        ctk.CTkLabel(panel, text="Estado actual: módulos aún no implementados (Próximamente)", anchor="w").grid(
            row=1, column=0, sticky="w", padx=12, pady=(0, 6)
        )

        workflow_frame = ctk.CTkFrame(panel)
        workflow_frame.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 8))

        modules = ["Análisis variográfico", "Kriging", "Simulación SGS", "Visualización"]
        for module in modules:
            ctk.CTkButton(
                workflow_frame,
                text=f"{module} · Próximamente",
                command=lambda module=module: self._on_module_clicked(module),
            ).pack(fill="x", pady=5)

        self.log_box = ctk.CTkTextbox(panel, height=130)
        self.log_box.grid(row=3, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self.log_box.insert("1.0", "5) Actividad reciente\n-------------------\n")
        self.log_box.configure(state="disabled")
        return panel

    def _selector(self, panel: ctk.CTkFrame, label: str, variable: ctk.StringVar, row: int, column: int) -> ctk.CTkOptionMenu:
        ctk.CTkLabel(panel, text=label).grid(row=row, column=column, sticky="w", padx=12, pady=(2, 2))
        menu = ctk.CTkOptionMenu(panel, variable=variable, values=[""], state="disabled")
        menu.grid(row=row + 1, column=column, sticky="ew", padx=12, pady=(0, 6))
        return menu

    def _on_load_csv(self) -> None:
        file_path = filedialog.askopenfilename(
            title="Seleccionar archivo CSV",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if not file_path:
            self.service.activity_log.log("csv_load_cancelled", "info", "Carga cancelada por usuario.", {})
            self.status_text.set("Carga cancelada por el usuario.")
            self._append_activity("Carga CSV cancelada.")
            return

        result = self.service.load_csv(file_path)
        self.status_text.set(result.message)
        self._set_text(self.dataset_box, result.details)
        self._append_activity(result.message)

        if result.success:
            columns = self.service.get_available_columns()
            self._populate_selectors(columns)
            self.dataset_status.set(
                f"Dataset: {result.dataset.file_name} | filas={result.dataset.row_count} columnas={result.dataset.column_count}"
            )
            self._set_text(self.eda_box, self.service.build_eda_summary())

    def _on_apply_variable_config(self) -> None:
        result = self.service.set_variable_config(
            x_column=self.x_var.get(), y_column=self.y_var.get(), z_column=self.z_var.get(), target_column=self.target_var.get()
        )
        self.status_text.set(result.message)
        self._set_text(self.eda_box, result.eda_summary)
        if result.success:
            self.active_config.set(
                f"Configuración activa: X={self.x_var.get()} | Y={self.y_var.get()} | Z={self.z_var.get()} | Target={self.target_var.get()}"
            )
        self._append_activity(result.message)

    def _on_update_repo(self) -> None:
        self.status_text.set("Actualizando repositorio...")
        self.update_repo_button.configure(state="disabled")

        def worker() -> None:
            result = self.service.update_repository()
            self.after(0, lambda: self._finish_repo_update(result.message, result.details))

        threading.Thread(target=worker, daemon=True).start()

    def _finish_repo_update(self, message: str, details: str) -> None:
        self.status_text.set(message)
        self._append_activity(message)
        self._append_activity(details)
        self.update_repo_button.configure(state="normal")

    def _on_export_log(self) -> None:
        destination = filedialog.asksaveasfilename(
            title="Exportar log de actividad",
            defaultextension=".jsonl",
            filetypes=[("JSONL", "*.jsonl")],
        )
        if not destination:
            self.status_text.set("Exportación de log cancelada.")
            return

        exported_path = self.service.export_activity_log(destination)
        message = f"Log exportado: {exported_path}"
        self.status_text.set(message)
        self._append_activity(message)

    def _on_module_clicked(self, module_name: str) -> None:
        message = self.service.module_not_implemented(module_name)
        self.status_text.set(message)
        self._append_activity(message)

    def _populate_selectors(self, columns: list[str]) -> None:
        if not columns:
            return
        for variable in [self.x_var, self.y_var, self.z_var, self.target_var]:
            variable.set(columns[0])
        for menu in [self.x_menu, self.y_menu, self.z_menu, self.target_menu]:
            menu.configure(values=columns, state="normal")
        self.apply_config_button.configure(state="normal")

    def _set_text(self, widget: ctk.CTkTextbox, text: str) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", text)
        widget.configure(state="disabled")

    def _append_activity(self, text: str) -> None:
        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"{text}\n\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")
