"""Workflow-oriented dashboard panel for geostatistics."""

from __future__ import annotations

from tkinter import filedialog
import threading

import customtkinter as ctk

from app.services.geostat_service import GeostatService


class HomePanel(ctk.CTkFrame):
    """UI structured as workflow navigation + controls + results."""

    def __init__(self, parent: ctk.CTk, service: GeostatService) -> None:
        super().__init__(master=parent)
        self.service = service

        self.status_text = ctk.StringVar(value="Listo para trabajar.")
        self.dataset_label = ctk.StringVar(value="Dataset: No cargado")
        self.target_label = ctk.StringVar(value="Target: No definido")
        self.domain_label = ctk.StringVar(value="Dominio activo: No definido")
        self.support_label = ctk.StringVar(value="Soporte activo: No definido")
        self.step_label = ctk.StringVar(value="Paso actual: Datos")
        self.qc_semaphore = ctk.StringVar(value="Semáforo QA/QC: N/A")

        self.x_var = ctk.StringVar(value="")
        self.y_var = ctk.StringVar(value="")
        self.z_var = ctk.StringVar(value="")
        self.target_var = ctk.StringVar(value="")
        self.hole_var = ctk.StringVar(value="")
        self.domain_var = ctk.StringVar(value="")

        self.log_visible = True
        self.step_buttons: dict[str, ctk.CTkButton] = {}

        self._build_layout()
        self._render_step("Datos")

    def _build_layout(self) -> None:
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_header().grid(row=0, column=0, sticky="ew", pady=(0, 8))

        body = ctk.CTkFrame(self)
        body.grid(row=1, column=0, sticky="nsew", pady=(0, 8))
        body.grid_columnconfigure(0, weight=0)
        body.grid_columnconfigure(1, weight=1)
        body.grid_columnconfigure(2, weight=1)
        body.grid_rowconfigure(0, weight=1)

        self.sidebar = self._build_sidebar(body)
        self.sidebar.grid(row=0, column=0, sticky="nsw", padx=(0, 8), pady=8)

        self.center_panel = ctk.CTkFrame(body)
        self.center_panel.grid(row=0, column=1, sticky="nsew", padx=(0, 8), pady=8)

        self.result_panel = ctk.CTkFrame(body)
        self.result_panel.grid(row=0, column=2, sticky="nsew", pady=8)
        self.result_panel.grid_rowconfigure(1, weight=1)
        self.result_panel.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self.result_panel, text="Resultados y vista previa", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=0, sticky="w", padx=12, pady=(10, 6)
        )
        self.result_box = ctk.CTkTextbox(self.result_panel)
        self.result_box.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self.result_box.insert("1.0", "Selecciona una etapa del workflow para comenzar.")
        self.result_box.configure(state="disabled")

        self.log_panel = ctk.CTkFrame(self)
        self.log_panel.grid(row=2, column=0, sticky="ew")
        self.log_panel.grid_columnconfigure(0, weight=1)
        self.log_panel.grid_rowconfigure(1, weight=1)

        self.toggle_log_button = ctk.CTkButton(
            self.log_panel,
            text="Ocultar log técnico",
            width=160,
            command=self._toggle_log,
        )
        self.toggle_log_button.grid(row=0, column=0, sticky="w", padx=8, pady=(4, 4))

        self.log_box = ctk.CTkTextbox(self.log_panel, height=120)
        self.log_box.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 8))
        self.log_box.insert("1.0", "Actividad reciente\n----------------\n")
        self.log_box.configure(state="disabled")

    def _build_header(self) -> ctk.CTkFrame:
        header = ctk.CTkFrame(self)
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text="GeoStat Py | Workflow geoestadístico guiado",
            font=ctk.CTkFont(size=19, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(8, 4))

        context = ctk.CTkFrame(header)
        context.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 8))
        context.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)

        for idx, textvar in enumerate(
            [self.dataset_label, self.target_label, self.domain_label, self.support_label, self.step_label]
        ):
            ctk.CTkLabel(context, textvariable=textvar, anchor="w").grid(row=0, column=idx, sticky="w", padx=4)

        actions = ctk.CTkFrame(header, fg_color="transparent")
        actions.grid(row=0, column=1, rowspan=2, sticky="e", padx=8)
        self.update_repo_button = ctk.CTkButton(actions, text="Actualizar repo", width=130, command=self._on_update_repo)
        self.update_repo_button.pack(side="left", padx=4)
        ctk.CTkButton(actions, text="Exportar log", width=120, command=self._on_export_log).pack(side="left", padx=4)

        return header

    def _build_sidebar(self, parent: ctk.CTkFrame) -> ctk.CTkFrame:
        sidebar = ctk.CTkFrame(parent, width=220)
        sidebar.grid_propagate(False)

        ctk.CTkLabel(sidebar, text="Workflow", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(10, 6))

        for idx, (step, state) in enumerate(self.service.get_workflow_step_status(), start=1):
            label = f"{idx}. {step} [{state}]"
            btn = ctk.CTkButton(sidebar, text=label, command=lambda step=step: self._on_change_step(step))
            btn.pack(fill="x", padx=10, pady=3)
            self.step_buttons[step] = btn
        return sidebar

    def _on_change_step(self, step_name: str) -> None:
        message = self.service.set_workflow_step(step_name)
        self.step_label.set(f"Paso actual: {step_name}")
        self.status_text.set(message)
        self._append_activity(message)
        self._render_step(step_name)

    def _render_step(self, step_name: str) -> None:
        for child in self.center_panel.winfo_children():
            child.destroy()

        if step_name == "Datos":
            self._build_data_step(self.center_panel)
        elif step_name == "QA/QC":
            self._build_qaqc_step(self.center_panel)
        elif step_name == "EDA":
            self._build_eda_step(self.center_panel)
        elif step_name == "Espacial":
            self._build_partial_step(self.center_panel, step_name, "Vista espacial preliminar (XY/sections/swath) será implementada en siguiente iteración.")
        elif step_name == "Exportación":
            self._build_partial_step(self.center_panel, step_name, "Exportación de resultados geostatísticos se habilitará al completar variografía/estimación.")
        else:
            self._build_future_step(self.center_panel, step_name)

    def _build_data_step(self, parent: ctk.CTkFrame) -> None:
        parent.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkLabel(parent, text="Etapa 1: Datos", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, sticky="w", padx=12, pady=(10, 6))
        ctk.CTkButton(parent, text="Cargar CSV", command=self._on_load_csv).grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 8))

        columns = self.service.get_available_columns() or [""]
        self._make_selector(parent, "X", self.x_var, columns, 2, 0)
        self._make_selector(parent, "Y", self.y_var, columns, 2, 1)
        self._make_selector(parent, "Z", self.z_var, columns, 4, 0)
        self._make_selector(parent, "Target", self.target_var, columns, 4, 1)
        self._make_selector(parent, "Hole ID", self.hole_var, columns, 6, 0)
        self._make_selector(parent, "Dominio/Litología", self.domain_var, columns, 6, 1)

        if columns and columns[0]:
            for var in [self.x_var, self.y_var, self.z_var, self.target_var]:
                if not var.get():
                    var.set(columns[0])

        ctk.CTkButton(parent, text="Aplicar configuración espacial", command=self._on_apply_variable_config).grid(
            row=8, column=0, columnspan=2, sticky="ew", padx=12, pady=(8, 6)
        )
        ctk.CTkLabel(parent, textvariable=self.qc_semaphore, anchor="w").grid(row=9, column=0, columnspan=2, sticky="w", padx=12, pady=(0, 10))

    def _build_qaqc_step(self, parent: ctk.CTkFrame) -> None:
        parent.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(parent, text="Etapa 2: QA/QC", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, sticky="w", padx=12, pady=(10, 6))
        ctk.CTkLabel(
            parent,
            text="Controles actuales: duplicados, nulos en coordenadas/target, numéricas y semáforo de riesgo.\nTratamiento de extremos (top-cut/capping) visible para próxima etapa.",
            justify="left",
        ).grid(row=1, column=0, sticky="w", padx=12, pady=(0, 8))
        ctk.CTkButton(parent, text="Evaluar calidad", command=self._on_evaluate_quality).grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 10))

    def _build_eda_step(self, parent: ctk.CTkFrame) -> None:
        parent.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(parent, text="Etapa 3: EDA", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, sticky="w", padx=12, pady=(10, 6))
        ctk.CTkLabel(parent, text="Submódulos: Univariado | Bivariado | Multivariado (futuro)", anchor="w").grid(
            row=1, column=0, sticky="w", padx=12, pady=(0, 8)
        )
        ctk.CTkButton(parent, text="Actualizar vista EDA", command=self._on_show_eda).grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 10))

    def _build_partial_step(self, parent: ctk.CTkFrame, step_name: str, message: str) -> None:
        parent.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(parent, text=f"Etapa: {step_name}", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=0, sticky="w", padx=12, pady=(10, 6)
        )
        ctk.CTkLabel(parent, text=message, justify="left").grid(row=1, column=0, sticky="w", padx=12, pady=(0, 8))
        ctk.CTkButton(parent, text="Registrar intento", command=lambda: self._on_future_step_action(step_name)).grid(
            row=2, column=0, sticky="ew", padx=12, pady=(0, 10)
        )

    def _build_future_step(self, parent: ctk.CTkFrame, step_name: str) -> None:
        self._build_partial_step(parent, step_name, "Etapa planificada, aún no implementada. Se registrará el intento en el log.")

    def _make_selector(self, parent: ctk.CTkFrame, label: str, variable: ctk.StringVar, values: list[str], row: int, col: int) -> None:
        ctk.CTkLabel(parent, text=label).grid(row=row, column=col, sticky="w", padx=12)
        state = "normal" if values and values[0] else "disabled"
        menu = ctk.CTkOptionMenu(parent, variable=variable, values=values, state=state)
        menu.grid(row=row + 1, column=col, sticky="ew", padx=12, pady=(0, 6))

    def _on_load_csv(self) -> None:
        file_path = filedialog.askopenfilename(title="Seleccionar CSV", filetypes=[("CSV", "*.csv"), ("All", "*.*")])
        if not file_path:
            self.service.activity_log.log("csv_load_cancelled", "info", "Carga cancelada por usuario.", {})
            self.status_text.set("Carga cancelada por usuario.")
            self._append_activity("Carga CSV cancelada.")
            return

        result = self.service.load_csv(file_path)
        self.status_text.set(result.message)
        self._set_result_text(result.details)
        self._append_activity(result.message)
        if result.success:
            self.dataset_label.set(f"Dataset: {result.dataset.file_name}")
            self.qc_semaphore.set("Semáforo QA/QC: pendiente evaluación")
            self._render_step("Datos")

    def _on_apply_variable_config(self) -> None:
        result = self.service.set_variable_config(
            x_column=self.x_var.get(),
            y_column=self.y_var.get(),
            z_column=self.z_var.get(),
            target_column=self.target_var.get(),
            hole_id_column=self.hole_var.get() or None,
            domain_column=self.domain_var.get() or None,
        )
        self.status_text.set(result.message)
        self._set_result_text(result.eda_summary)
        self._append_activity(result.message)

        if result.success:
            self.target_label.set(f"Target: {self.target_var.get()}")
            self.domain_label.set(f"Dominio activo: {self.service.workflow_state.active_domain}")
            self.support_label.set(f"Soporte activo: {self.service.workflow_state.active_support}")

    def _on_evaluate_quality(self) -> None:
        semaphore, summary = self.service.evaluate_data_quality()
        self.qc_semaphore.set(f"Semáforo QA/QC: {semaphore.upper()}")
        self._set_result_text(summary)
        self.status_text.set("QA/QC evaluado.")
        self._append_activity(f"QA/QC evaluado ({semaphore}).")

    def _on_show_eda(self) -> None:
        summary = self.service.build_eda_summary()
        self._set_result_text(summary)
        self.status_text.set("Vista EDA actualizada.")
        self._append_activity("EDA abierta/actualizada.")

    def _on_future_step_action(self, step_name: str) -> None:
        message = self.service.module_not_implemented(step_name)
        self.status_text.set(message)
        self._append_activity(message)

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
            title="Exportar log",
            defaultextension=".jsonl",
            filetypes=[("JSONL", "*.jsonl")],
        )
        if not destination:
            self.status_text.set("Exportación de log cancelada.")
            return

        exported_path = self.service.export_activity_log(destination)
        self.status_text.set(f"Log exportado: {exported_path}")
        self._append_activity(f"Log exportado: {exported_path}")

    def _set_result_text(self, text: str) -> None:
        self.result_box.configure(state="normal")
        self.result_box.delete("1.0", "end")
        self.result_box.insert("1.0", text)
        self.result_box.configure(state="disabled")

    def _append_activity(self, text: str) -> None:
        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"{text}\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _toggle_log(self) -> None:
        self.log_visible = not self.log_visible
        if self.log_visible:
            self.log_box.grid()
            self.toggle_log_button.configure(text="Ocultar log técnico")
        else:
            self.log_box.grid_remove()
            self.toggle_log_button.configure(text="Mostrar log técnico")
