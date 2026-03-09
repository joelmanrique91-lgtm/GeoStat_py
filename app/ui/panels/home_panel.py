"""Workflow-oriented dashboard with dominant visual EDA panels."""

from __future__ import annotations

from tkinter import filedialog
import threading

import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from app.services.geostat_service import GeostatService


class HomePanel(ctk.CTkFrame):
    def __init__(self, parent: ctk.CTk, service: GeostatService) -> None:
        super().__init__(master=parent)
        self.service = service

        self.dataset_label = ctk.StringVar(value="Dataset: No cargado")
        self.target_label = ctk.StringVar(value="Target: No definido")
        self.domain_label = ctk.StringVar(value="Dominio activo: No definido")
        self.support_label = ctk.StringVar(value="Soporte activo: No definido")
        self.step_label = ctk.StringVar(value="Paso actual: Datos")
        self.status_text = ctk.StringVar(value="Listo")
        self.qc_semaphore = ctk.StringVar(value="Semáforo QA/QC: N/A")

        self.x_var = ctk.StringVar(value="")
        self.y_var = ctk.StringVar(value="")
        self.z_var = ctk.StringVar(value="")
        self.target_var = ctk.StringVar(value="")
        self.hole_var = ctk.StringVar(value="")
        self.domain_var = ctk.StringVar(value="")

        self.log_visible = True
        self.summary_value_labels: dict[str, ctk.CTkLabel] = {}
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
        body.grid_columnconfigure(2, weight=2)
        body.grid_rowconfigure(0, weight=1)

        self._build_sidebar(body).grid(row=0, column=0, sticky="nsw", padx=(0, 8), pady=8)
        body.grid_columnconfigure(2, weight=1)
        body.grid_rowconfigure(0, weight=1)

        self.sidebar = self._build_sidebar(body)
        self.sidebar.grid(row=0, column=0, sticky="nsw", padx=(0, 8), pady=8)

        self.center_panel = ctk.CTkFrame(body)
        self.center_panel.grid(row=0, column=1, sticky="nsew", padx=(0, 8), pady=8)

        self.right_panel = ctk.CTkFrame(body)
        self.right_panel.grid(row=0, column=2, sticky="nsew", pady=8)
        self.right_panel.grid_columnconfigure(0, weight=1)
        self.right_panel.grid_rowconfigure(1, weight=1)

        self._build_summary_cards(self.right_panel)
        self.eda_tabs = ctk.CTkTabview(self.right_panel)
        self.eda_tabs.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))
        self.eda_tabs.add("Resumen")
        self.eda_tabs.add("Univariado")
        self.eda_tabs.add("Espacial")

        self.log_panel = ctk.CTkFrame(self)
        self.log_panel.grid(row=2, column=0, sticky="ew")
        self.log_panel.grid_columnconfigure(0, weight=1)
        ctk.CTkButton(self.log_panel, text="Ocultar/Mostrar log", width=150, command=self._toggle_log).grid(row=0, column=0, sticky="w", padx=8, pady=4)
        self.log_box = ctk.CTkTextbox(self.log_panel, height=80)
        self.log_box.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 8))
        self.log_box.insert("1.0", "Actividad reciente\n")
        self.log_box.configure(state="disabled")

    def _build_header(self) -> ctk.CTkFrame:
        header = ctk.CTkFrame(self)
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(header, text="GeoStat Py | Exploración Visual Geoestadística", font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=0, sticky="w", padx=12, pady=(8, 4))

        context = ctk.CTkFrame(header)
        context.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 8))
        for idx, tvar in enumerate([self.dataset_label, self.target_label, self.domain_label, self.support_label, self.step_label]):
            ctk.CTkLabel(context, textvariable=tvar).grid(row=0, column=idx, padx=8, sticky="w")

        actions = ctk.CTkFrame(header, fg_color="transparent")
        actions.grid(row=0, column=1, rowspan=2, sticky="e", padx=8)
        self.update_repo_button = ctk.CTkButton(actions, text="Actualizar repo", width=120, command=self._on_update_repo)
        self.update_repo_button.pack(side="left", padx=4)
        ctk.CTkButton(actions, text="Exportar log", width=110, command=self._on_export_log).pack(side="left", padx=4)
        ctk.CTkLabel(actions, textvariable=self.status_text).pack(side="left", padx=6)
        return header

    def _build_sidebar(self, parent: ctk.CTkFrame) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(parent, width=230)
        frame.grid_propagate(False)
        ctk.CTkLabel(frame, text="Workflow", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=8, pady=(10, 6))
        for idx, (step, state) in enumerate(self.service.get_workflow_step_status(), start=1):
            ctk.CTkButton(frame, text=f"{idx}. {step} [{state}]", command=lambda s=step: self._on_change_step(s)).pack(fill="x", padx=8, pady=3)
        return frame

    def _build_summary_cards(self, parent: ctk.CTkFrame) -> None:
        cards = ctk.CTkFrame(parent)
        cards.grid(row=0, column=0, sticky="ew", padx=8, pady=8)
        keys = ["Dataset", "Muestras", "Columnas", "Target", "Estado", "Dominio", "Soporte", "Mean", "Std", "CV"]
        for i, key in enumerate(keys):
            ctk.CTkLabel(cards, text=f"{key}:", font=ctk.CTkFont(weight="bold")).grid(row=i // 5, column=(i % 5) * 2, sticky="e", padx=(6, 2), pady=2)
            lbl = ctk.CTkLabel(cards, text="-")
            lbl.grid(row=i // 5, column=(i % 5) * 2 + 1, sticky="w", padx=(0, 6), pady=2)
            self.summary_value_labels[key] = lbl

    def _on_change_step(self, step_name: str) -> None:
        self.status_text.set(self.service.set_workflow_step(step_name))
        self.step_label.set(f"Paso actual: {step_name}")
        self._append_activity(self.status_text.get())
        self._render_step(step_name)

    def _render_step(self, step_name: str) -> None:
        for c in self.center_panel.winfo_children():
            c.destroy()
        if step_name == "Datos":
            self._render_data_step()
        elif step_name == "QA/QC":
            self._render_qaqc_step()
        elif step_name in {"EDA", "Espacial"}:
            self._render_eda_step(step_name)
        else:
            self._render_future_step(step_name)

    def _render_data_step(self) -> None:
        self.center_panel.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkLabel(self.center_panel, text="Etapa Datos", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, sticky="w", padx=8, pady=(8, 4))
        ctk.CTkButton(self.center_panel, text="Cargar CSV", command=self._on_load_csv).grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 8))

        cols = self.service.get_available_columns() or [""]
        self._selector("X", self.x_var, cols, 2, 0)
        self._selector("Y", self.y_var, cols, 2, 1)
        self._selector("Z", self.z_var, cols, 4, 0)
        self._selector("Target", self.target_var, cols, 4, 1)
        self._selector("Hole ID", self.hole_var, cols, 6, 0)
        self._selector("Dominio", self.domain_var, cols, 6, 1)
        ctk.CTkButton(self.center_panel, text="Aplicar configuración", command=self._on_apply_config).grid(row=8, column=0, columnspan=2, sticky="ew", padx=8, pady=8)

    def _render_qaqc_step(self) -> None:
        ctk.CTkLabel(self.center_panel, text="Etapa QA/QC", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=8, pady=(8, 4))
        ctk.CTkButton(self.center_panel, text="Evaluar calidad", command=self._on_evaluate_quality).pack(fill="x", padx=8, pady=(0, 8))
        ctk.CTkLabel(self.center_panel, textvariable=self.qc_semaphore).pack(anchor="w", padx=8)

    def _render_eda_step(self, step_name: str) -> None:
        ctk.CTkLabel(self.center_panel, text=f"Etapa {step_name}", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=8, pady=(8, 4))
        ctk.CTkButton(self.center_panel, text="Actualizar visuales", command=self._render_visuals).pack(fill="x", padx=8, pady=(0, 8))

    def _render_future_step(self, step_name: str) -> None:
        ctk.CTkLabel(self.center_panel, text=f"Etapa {step_name}", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=8, pady=(8, 4))
        ctk.CTkLabel(self.center_panel, text="Etapa futura. Se registra intento en log.").pack(anchor="w", padx=8)
        ctk.CTkButton(self.center_panel, text="Registrar intento", command=lambda: self._on_future_step(step_name)).pack(fill="x", padx=8, pady=8)

    def _selector(self, label: str, variable: ctk.StringVar, values: list[str], row: int, col: int) -> None:
        ctk.CTkLabel(self.center_panel, text=label).grid(row=row, column=col, sticky="w", padx=8)
        state = "normal" if values and values[0] else "disabled"
        menu = ctk.CTkOptionMenu(self.center_panel, variable=variable, values=values, state=state)
        menu.grid(row=row + 1, column=col, sticky="ew", padx=8, pady=(0, 6))

    def _on_load_csv(self) -> None:
        path = filedialog.askopenfilename(title="Seleccionar CSV", filetypes=[("CSV", "*.csv"), ("All", "*.*")])
        if not path:
            self.service.activity_log.log("csv_load_cancelled", "info", "Carga cancelada.", {})
            return
        result = self.service.load_csv(path)
        self.status_text.set(result.message)
        self._append_activity(result.message)
        if result.success and result.dataset:
            self.dataset_label.set(f"Dataset: {result.dataset.file_name}")
            self._render_step("Datos")
            self._refresh_summary_cards()
            self._set_summary_tab_text(result.details)

    def _on_apply_config(self) -> None:
        result = self.service.set_variable_config(
            self.x_var.get(), self.y_var.get(), self.z_var.get(), self.target_var.get(), self.hole_var.get() or None, self.domain_var.get() or None
        )
        self.status_text.set(result.message)
        self._append_activity(result.message)
        if result.success:
            self.target_label.set(f"Target: {self.target_var.get()}")
            self.domain_label.set(f"Dominio activo: {self.service.workflow_state.active_domain}")
            self.support_label.set(f"Soporte activo: {self.service.workflow_state.active_support}")
            self._refresh_summary_cards()
            self._set_summary_tab_text(result.eda_summary)
            self._render_visuals()

    def _on_evaluate_quality(self) -> None:
        semaphore, summary = self.service.evaluate_data_quality()
        self.qc_semaphore.set(f"Semáforo QA/QC: {semaphore.upper()}")
        self._set_summary_tab_text(summary)
        self._append_activity(f"QA/QC evaluado: {semaphore}")

    def _render_visuals(self) -> None:
        result = self.service.prepare_visual_data()
        if not result.success:
            self.status_text.set(result.message)
            self._append_activity(result.message)
            self._set_summary_tab_text(result.message)
            return

        self._render_univariate_plots(result.target_values)
        self._render_spatial_scatter(result.x_values, result.y_values, result.target_values)
        self._set_summary_tab_text(self.service.build_eda_summary())

    def _render_univariate_plots(self, values: list[float]) -> None:
        tab = self.eda_tabs.tab("Univariado")
        for child in tab.winfo_children():
            child.destroy()
        fig = Figure(figsize=(6.5, 3.6), dpi=100)
        ax1 = fig.add_subplot(121)
        ax2 = fig.add_subplot(122)
        ax1.hist(values, bins=20, color="#4c78a8", edgecolor="white")
        ax1.set_title("Histograma target")
        ax2.boxplot(values, vert=True, patch_artist=True)
        ax2.set_title("Boxplot target")
        fig.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=tab)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=4, pady=4)

    def _render_spatial_scatter(self, x: list[float], y: list[float], target: list[float]) -> None:
        tab = self.eda_tabs.tab("Espacial")
        for child in tab.winfo_children():
            child.destroy()
        fig = Figure(figsize=(6.5, 3.8), dpi=100)
        ax = fig.add_subplot(111)
        scatter = ax.scatter(x, y, c=target, cmap="viridis", s=16)
        ax.set_xlabel("X")
        ax.set_ylabel("Y")
        ax.set_title("Scatter XY coloreado por target")
        fig.colorbar(scatter, ax=ax, shrink=0.85, label="Target")
        fig.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=tab)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=4, pady=4)

    def _set_summary_tab_text(self, text: str) -> None:
        tab = self.eda_tabs.tab("Resumen")
        for child in tab.winfo_children():
            child.destroy()
        box = ctk.CTkTextbox(tab)
        box.pack(fill="both", expand=True, padx=6, pady=6)
        box.insert("1.0", text)
        box.configure(state="disabled")

        stats = self.service.get_target_statistics_table()
        if stats:
            tbl = ctk.CTkFrame(tab)
            tbl.pack(fill="x", padx=6, pady=(0, 6))
            for i, (k, v) in enumerate(stats):
                ctk.CTkLabel(tbl, text=k, width=90, anchor="w").grid(row=i // 4, column=(i % 4) * 2, sticky="w", padx=4, pady=1)
                ctk.CTkLabel(tbl, text=v, anchor="w").grid(row=i // 4, column=(i % 4) * 2 + 1, sticky="w", padx=4, pady=1)

    def _refresh_summary_cards(self) -> None:
        cards = self.service.get_summary_cards()
        for key, label in self.summary_value_labels.items():
            label.configure(text=cards.get(key, "-"))

    def _on_future_step(self, step_name: str) -> None:
        msg = self.service.module_not_implemented(step_name)
        self.status_text.set(msg)
        self._append_activity(msg)

    def _on_update_repo(self) -> None:
        self.update_repo_button.configure(state="disabled")
        self.status_text.set("Actualizando repo...")

        def worker() -> None:
            result = self.service.update_repository()
            self.after(0, lambda: self._finish_repo_update(result.message, result.details))

        threading.Thread(target=worker, daemon=True).start()

    def _finish_repo_update(self, message: str, details: str) -> None:
        self.update_repo_button.configure(state="normal")
        self.status_text.set(message)
        self._append_activity(message)
        self._append_activity(details)

    def _on_export_log(self) -> None:
        destination = filedialog.asksaveasfilename(title="Exportar log", defaultextension=".jsonl", filetypes=[("JSONL", "*.jsonl")])
        if not destination:
            return
        path = self.service.export_activity_log(destination)
        self.status_text.set(f"Log exportado: {path}")
        self._append_activity(self.status_text.get())

    def _append_activity(self, text: str) -> None:
        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"{text}\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _toggle_log(self) -> None:
        self.log_visible = not self.log_visible
        if self.log_visible:
            self.log_box.grid()
        else:
            self.log_box.grid_remove()
