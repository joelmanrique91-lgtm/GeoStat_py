"""Workflow-oriented dashboard with clear stage separation: Datos / EDA / Cutoffs / Espacial."""

from __future__ import annotations

from tkinter import filedialog
import threading

import customtkinter as ctk

from app.services.geostat_service import GeostatService
from app.ui.panels.dashboard_grid import DashboardGrid


class HomePanel(ctk.CTkFrame):
    def __init__(self, parent: ctk.CTk, service: GeostatService) -> None:
        super().__init__(master=parent)
        self.service = service

        self.dataset_label = ctk.StringVar(value="Dataset: No cargado")
        self.target_label = ctk.StringVar(value="Target: No definido")
        self.domain_label = ctk.StringVar(value="Dominio: No definido")
        self.step_label = ctk.StringVar(value="Paso actual: Datos")
        self.status_text = ctk.StringVar(value="Listo")

        self.x_var = ctk.StringVar(value="")
        self.y_var = ctk.StringVar(value="")
        self.z_var = ctk.StringVar(value="")
        self.target_var = ctk.StringVar(value="")
        self.hole_var = ctk.StringVar(value="")
        self.domain_var = ctk.StringVar(value="")
        self.cutoff_enabled_var = ctk.BooleanVar(value=False)
        self.cutoff_target_var = ctk.StringVar(value="")
        self.cutoff_limits_var = ctk.StringVar(value="")
        self.cutoff_output_var = ctk.StringVar(value="")

        self.log_visible = True
        self.data_panel_collapsed = False
        self.summary_value_labels: dict[str, ctk.CTkLabel] = {}

        self._build_layout()
        self._render_step("Datos")

    def _build_layout(self) -> None:
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._build_header().grid(row=0, column=0, sticky="ew", pady=(0, 6))

        body = ctk.CTkFrame(self)
        body.grid(row=1, column=0, sticky="nsew", pady=(0, 6))
        body.grid_columnconfigure(0, weight=0)
        body.grid_columnconfigure(1, weight=1)
        body.grid_columnconfigure(2, weight=4)
        body.grid_rowconfigure(0, weight=1)

        self.sidebar = self._build_sidebar(body)
        self.sidebar.grid(row=0, column=0, sticky="nsw", padx=(0, 6), pady=6)

        self.center_panel = ctk.CTkFrame(body, width=290)
        self.center_panel.grid(row=0, column=1, sticky="nsew", padx=(0, 6), pady=6)

        self.right_panel = ctk.CTkFrame(body)
        self.right_panel.grid(row=0, column=2, sticky="nsew", pady=6)
        self.right_panel.grid_columnconfigure(0, weight=1)
        self.right_panel.grid_rowconfigure(1, weight=1)

        self._build_summary_cards(self.right_panel)

        self.data_stage_view = ctk.CTkFrame(self.right_panel)
        self.data_stage_view.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))

        self.eda_tabs = ctk.CTkTabview(self.right_panel, command=self._on_eda_tab_changed)
        self.eda_tabs.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))
        self.eda_tabs.add("Resumen")
        self.eda_tabs.add("Univariado")

        self.spatial_stage_view = ctk.CTkFrame(self.right_panel)
        self.spatial_stage_view.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))
        self.cutoff_stage_view = ctk.CTkFrame(self.right_panel)
        self.cutoff_stage_view.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))

        self.log_panel = ctk.CTkFrame(self)
        self.log_panel.grid(row=2, column=0, sticky="ew")
        self.log_panel.grid_columnconfigure(1, weight=1)
        ctk.CTkButton(self.log_panel, text="Ocultar/Mostrar log", width=140, command=self._toggle_log).grid(row=0, column=0, sticky="w", padx=8, pady=4)
        self.log_box = ctk.CTkTextbox(self.log_panel, height=65)
        self.log_box.grid(row=0, column=1, sticky="ew", padx=8, pady=4)
        self.log_box.insert("1.0", "Actividad reciente\n")
        self.log_box.configure(state="disabled")

    def _build_header(self) -> ctk.CTkFrame:
        header = ctk.CTkFrame(self)
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(header, text="GeoStat Py | Datos + EDA + Cutoffs + Espacial", font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=0, sticky="w", padx=12, pady=(8, 4))

        context = ctk.CTkFrame(header)
        context.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 8))
        for idx, tvar in enumerate([self.dataset_label, self.target_label, self.domain_label, self.step_label]):
            ctk.CTkLabel(context, textvariable=tvar).grid(row=0, column=idx, padx=8, sticky="w")

        actions = ctk.CTkFrame(header, fg_color="transparent")
        actions.grid(row=0, column=1, rowspan=2, sticky="e", padx=8)
        self.update_repo_button = ctk.CTkButton(actions, text="Actualizar repo (seguro)", width=170, command=self._on_update_repo)
        self.update_repo_button.pack(side="left", padx=4)
        ctk.CTkButton(actions, text="Exportar log", width=110, command=self._on_export_log).pack(side="left", padx=4)
        ctk.CTkLabel(actions, textvariable=self.status_text).pack(side="left", padx=6)
        return header

    def _build_sidebar(self, parent: ctk.CTkFrame) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(parent, width=200)
        frame.grid_propagate(False)
        ctk.CTkLabel(frame, text="Workflow", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=8, pady=(10, 6))
        for idx, (step, state) in enumerate(self.service.get_workflow_step_status(), start=1):
            ctk.CTkButton(frame, text=f"{idx}. {step} [{state}]", command=lambda s=step: self._on_change_step(s)).pack(fill="x", padx=8, pady=3)
        return frame

    def _build_summary_cards(self, parent: ctk.CTkFrame) -> None:
        cards = ctk.CTkFrame(parent)
        cards.grid(row=0, column=0, sticky="ew", padx=8, pady=8)
        keys = ["Dataset", "Muestras", "Columnas", "Target", "Estado", "Dominio"]
        for i, key in enumerate(keys):
            ctk.CTkLabel(cards, text=f"{key}:", font=ctk.CTkFont(weight="bold")).grid(row=i // 3, column=(i % 3) * 2, sticky="e", padx=(6, 2), pady=2)
            lbl = ctk.CTkLabel(cards, text="-")
            lbl.grid(row=i // 3, column=(i % 3) * 2 + 1, sticky="w", padx=(0, 6), pady=2)
            self.summary_value_labels[key] = lbl

    def _show_stage_view(self, stage: str) -> None:
        self.data_stage_view.grid_remove()
        self.eda_tabs.grid_remove()
        self.cutoff_stage_view.grid_remove()
        self.spatial_stage_view.grid_remove()
        if stage == "Datos":
            self.data_stage_view.grid()
        elif stage == "EDA":
            self.eda_tabs.grid()
        elif stage == "Cutoffs":
            self.cutoff_stage_view.grid()
        elif stage == "Espacial":
            self.spatial_stage_view.grid()

    def _on_change_step(self, step_name: str) -> None:
        self.status_text.set(self.service.set_workflow_step(step_name))
        self.step_label.set(f"Paso actual: {step_name}")
        self._append_activity(self.status_text.get())
        self._render_step(step_name)

    def _render_step(self, step_name: str) -> None:
        self._show_stage_view(step_name)
        for child in self.center_panel.winfo_children():
            child.destroy()

        if step_name == "Datos":
            self._render_data_step()
            self._render_data_stage_panel()
        elif step_name == "EDA":
            self._render_analysis_step("EDA")
            self._render_eda_tab(self.eda_tabs.get() or "Resumen")
        elif step_name == "Cutoffs":
            self._render_analysis_step("Cutoffs")
            self._render_cutoff_stage_panel()
        elif step_name == "Espacial":
            self._render_analysis_step("Espacial")
            self._render_spatial_stage_panel()

    def _render_data_step(self) -> None:
        ctk.CTkLabel(self.center_panel, text="Etapa Datos", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=8, pady=(8, 4))
        ctk.CTkButton(self.center_panel, text="Cargar CSV", command=self._on_load_csv).pack(fill="x", padx=8, pady=(0, 8))
        ctk.CTkButton(
            self.center_panel,
            text="Ocultar configuración" if not self.data_panel_collapsed else "Mostrar configuración",
            command=self._toggle_data_panel,
        ).pack(fill="x", padx=8, pady=(0, 8))

        if self.data_panel_collapsed:
            ctk.CTkLabel(self.center_panel, text=self._build_compact_config_summary(), justify="left").pack(anchor="w", padx=8, pady=4)
            ctk.CTkButton(self.center_panel, text="Editar configuración", command=self._toggle_data_panel).pack(fill="x", padx=8, pady=8)
            return

        config_grid = ctk.CTkFrame(self.center_panel, fg_color="transparent")
        config_grid.pack(fill="x", padx=8, pady=(0, 8))
        config_grid.grid_columnconfigure((0, 1), weight=1)
        cols = self.service.get_available_columns() or [""]
        self._selector(config_grid, "X", self.x_var, cols, 0, 0)
        self._selector(config_grid, "Y", self.y_var, cols, 0, 1)
        self._selector(config_grid, "Z", self.z_var, cols, 2, 0)
        self._selector(config_grid, "Target", self.target_var, cols, 2, 1)
        self._selector(config_grid, "Hole ID", self.hole_var, cols, 4, 0)
        self._selector(config_grid, "Dominio", self.domain_var, cols, 4, 1)
        ctk.CTkButton(config_grid, text="Aplicar configuración", command=self._on_apply_config).grid(row=6, column=0, columnspan=2, sticky="ew", pady=8)

    def _render_analysis_step(self, step_name: str) -> None:
        ctk.CTkLabel(self.center_panel, text=f"Etapa {step_name}", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=8, pady=(8, 4))
        ctk.CTkButton(self.center_panel, text="Actualizar vista", command=lambda: self._render_step(step_name)).pack(fill="x", padx=8, pady=(0, 8))

    def _selector(self, parent: ctk.CTkFrame, label: str, variable: ctk.StringVar, values: list[str], row: int, col: int) -> None:
        ctk.CTkLabel(parent, text=label).grid(row=row, column=col, sticky="w", padx=4)
        state = "normal" if values and values[0] else "disabled"
        ctk.CTkOptionMenu(parent, variable=variable, values=values, state=state).grid(row=row + 1, column=col, sticky="ew", padx=4, pady=(0, 6))

    def _toggle_data_panel(self) -> None:
        self.data_panel_collapsed = not self.data_panel_collapsed
        event = "data_panel_collapsed" if self.data_panel_collapsed else "data_panel_expanded"
        self.service.activity_log.log(event, "info", "Panel de datos actualizado.", {"collapsed": self.data_panel_collapsed})
        self._render_step("Datos")

    def _build_compact_config_summary(self) -> str:
        return (
            f"X: {self.x_var.get() or '-'}\n"
            f"Y: {self.y_var.get() or '-'}\n"
            f"Z: {self.z_var.get() or '-'}\n"
            f"Target: {self.target_var.get() or '-'}\n"
            f"Hole ID: {self.hole_var.get() or '-'}\n"
            f"Dominio: {self.domain_var.get() or '-'}"
        )

    def _render_data_stage_panel(self) -> None:
        DashboardGrid.clear(self.data_stage_view)
        ctk.CTkLabel(
            self.data_stage_view,
            text="Etapa Datos: carga y configuración de columnas.\nLas vistas analíticas se habilitan en EDA y Espacial.",
            justify="left",
        ).pack(anchor="w", padx=8, pady=8)

    def _on_eda_tab_changed(self, *_args) -> None:
        if self.service.workflow_state.current_step == "EDA":
            self.after(20, lambda: self._render_eda_tab(self.eda_tabs.get() or "Resumen"))

    def _render_eda_tab(self, tab_name: str) -> None:
        if tab_name == "Resumen":
            self._set_summary_tab_content()
        elif tab_name == "Univariado":
            self._render_univariado_tab()

    def _render_univariado_tab(self) -> None:
        tab = self.eda_tabs.tab("Univariado")
        DashboardGrid.clear(tab)
        self.service.activity_log.log("eda_univariate_render_started", "info", "Render Univariado iniciado.", {})
        try:
            data = self.service.prepare_univariate_data(max_domain_categories=10)
        except Exception as exc:
            self.service.activity_log.log("eda_univariate_render_failed", "error", str(exc), {})
            self.service.activity_log.log("empty_state_shown", "warning", "Estado vacío mostrado en Univariado.", {"reason": str(exc)})
            ctk.CTkLabel(tab, text=f"No se pudo renderizar Univariado: {exc}", justify="left").pack(anchor="w", padx=8, pady=8)
            return

        dashboard = DashboardGrid(tab, 2, 2, figsize=(8.6, 6.0))
        failed_parts: list[str] = []
        availability = data.get("availability", {})

        ax_hist = dashboard.axis(0, 0)
        try:
            hist_meta = availability.get("histogram", {})
            if not hist_meta.get("available", True):
                raise ValueError(hist_meta.get("message", "Histograma no disponible"))
            ax_hist.hist(data["target_values"], bins=20, color="#4c78a8", edgecolor="white")
            ax_hist.set_title("Histograma target")
        except Exception as exc:
            failed_parts.append("histograma")
            ax_hist.axis("off")
            ax_hist.text(0.5, 0.5, str(exc), ha="center", va="center", wrap=True)
            self.service.activity_log.log("eda_univariate_render_partial", "warning", str(exc), {"component": "histogram"})

        ax_box = dashboard.axis(0, 1)
        try:
            box_meta = availability.get("boxplot", {})
            if not box_meta.get("available", True):
                raise ValueError(box_meta.get("message", "Boxplot general no disponible"))
            ax_box.boxplot(data["target_values"], vert=True, patch_artist=True)
            ax_box.set_title("Boxplot general")
        except Exception as exc:
            failed_parts.append("boxplot general")
            ax_box.axis("off")
            ax_box.text(0.5, 0.5, str(exc), ha="center", va="center", wrap=True)
            self.service.activity_log.log("eda_univariate_render_partial", "warning", str(exc), {"component": "boxplot_general"})

        ax_prob = dashboard.axis(1, 0)
        try:
            prob_meta = availability.get("probability", {})
            if not prob_meta.get("available", True):
                raise ValueError(prob_meta.get("message", "Probability plot no disponible"))
            if data.get("probability_failed") or not data["probplot_x"] or not data["probplot_y"]:
                raise ValueError("Probability plot no disponible: payload vacío o inválido.")
            ax_prob.scatter(data["probplot_x"], data["probplot_y"], s=10, color="#54a24b")
            ax_prob.set_title("Probability plot")
            ax_prob.set_xlabel("Cuantiles teóricos normal")
            ax_prob.set_ylabel("Cuantiles observados")
        except Exception as exc:
            failed_parts.append("probability plot")
            ax_prob.axis("off")
            ax_prob.text(0.5, 0.5, str(exc), ha="center", va="center", wrap=True)
            self.service.activity_log.log("probability_plot_failed", "error", str(exc), {})
            self.service.activity_log.log("eda_univariate_render_partial", "warning", str(exc), {"component": "probability_plot"})

        ax_domain = dashboard.axis(1, 1)
        try:
            domain_data = data["domain_boxplot"]
            if domain_data["enabled"]:
                ax_domain.boxplot(domain_data["values"], labels=domain_data["labels"], patch_artist=True)
                ax_domain.set_title("Boxplot por dominio")
                ax_domain.tick_params(axis="x", rotation=30)
                if domain_data["message"]:
                    self._append_activity(domain_data["message"])
            else:
                raise ValueError(domain_data.get("message") or "Boxplot por dominio no disponible")
        except Exception as exc:
            failed_parts.append("boxplot por dominio")
            ax_domain.axis("off")
            ax_domain.text(0.5, 0.5, str(exc), ha="center", va="center", wrap=True)
            self.service.activity_log.log("domain_boxplot_failed", "warning", str(exc), {})
            self.service.activity_log.log("eda_univariate_render_partial", "warning", str(exc), {"component": "domain_boxplot"})

        dashboard.render()
        diagnostics = data.get("diagnostics", {})
        if diagnostics:
            self.service.activity_log.log("eda_univariate_diagnostics", "info", "Métricas de validación de univariado.", diagnostics)
        if failed_parts and len(failed_parts) < 4:
            self._append_activity(f"Univariado render parcial. No disponible: {', '.join(failed_parts)}")
        if len(failed_parts) == 4:
            self.service.activity_log.log("eda_univariate_render_failed", "error", "Ningún gráfico univariado pudo renderizarse.", {})
            self.service.activity_log.log("empty_state_shown", "warning", "Todos los componentes univariados fallaron.", {})
        else:
            self.service.activity_log.log("eda_univariate_render_finished", "success", "Render Univariado completado.", {"failed_components": failed_parts})

    def _render_spatial_stage_panel(self) -> None:
        DashboardGrid.clear(self.spatial_stage_view)
        self.service.activity_log.log("spatial_3d_disabled_or_hidden", "info", "Vista 3D deshabilitada como vista principal.", {})

        try:
            result = self.service.prepare_visual_data()
            if not result.success or result.spatial_data is None:
                raise ValueError(result.message)
            spatial = result.spatial_data
        except Exception as exc:
            self.service.activity_log.log("empty_state_shown", "warning", "Estado vacío mostrado en Espacial.", {"reason": str(exc)})
            ctk.CTkLabel(self.spatial_stage_view, text=f"No se pudo renderizar Espacial: {exc}", justify="left").pack(anchor="w", padx=8, pady=8)
            return

        dashboard = DashboardGrid(self.spatial_stage_view, 2, 2, figsize=(9.2, 6.8))
        ax_xy = dashboard.axis(0, 0)
        ax_xz = dashboard.axis(0, 1)
        ax_yz = dashboard.axis(1, 0)
        ax_info = dashboard.axis(1, 1)

        sc_xy = ax_xy.scatter(spatial.x, spatial.y, c=spatial.target, cmap="viridis", s=12)
        sc_xz = ax_xz.scatter(spatial.x, spatial.z, c=spatial.target, cmap="viridis", s=12)
        sc_yz = ax_yz.scatter(spatial.y, spatial.z, c=spatial.target, cmap="viridis", s=12)

        ax_xy.set_title("XY (planta)")
        ax_xy.set_xlabel("X")
        ax_xy.set_ylabel("Y")

        ax_xz.set_title("XZ (sección)")
        ax_xz.set_xlabel("X")
        ax_xz.set_ylabel("Z")

        ax_yz.set_title("YZ (sección)")
        ax_yz.set_xlabel("Y")
        ax_yz.set_ylabel("Z")

        for sc, ax in [(sc_xy, ax_xy), (sc_xz, ax_xz), (sc_yz, ax_yz)]:
            cbar = dashboard.figure.colorbar(sc, ax=ax, shrink=0.78, label=spatial.target_label)
            if spatial.target_tick_positions and spatial.target_tick_labels:
                cbar.set_ticks(spatial.target_tick_positions)
                cbar.set_ticklabels(spatial.target_tick_labels)

        ax_info.axis("off")
        msg = "Vistas 2D activas: XY, XZ, YZ."
        state = self.service.get_cutoff_state()
        if state["enabled"]:
            msg += f"\nCutoffs activos: {state['output_column']} ({state['target_column']})."
        if spatial.downsampled:
            msg += f"\nMuestreo: {spatial.plotted_points}/{spatial.source_points} puntos."
        ax_info.text(0.05, 0.9, msg, va="top")

        dashboard.render()

    def _set_summary_tab_content(self) -> None:
        tab = self.eda_tabs.tab("Resumen")
        DashboardGrid.clear(tab)
        table_data = self.service.get_target_statistics_table()
        if not table_data:
            self.service.activity_log.log("empty_state_shown", "warning", "Estado vacío mostrado en Resumen EDA.", {})
            ctk.CTkLabel(tab, text=self.service.build_eda_summary(), justify="left").pack(anchor="w", padx=8, pady=8)
            return

        grid = ctk.CTkFrame(tab)
        grid.pack(fill="x", padx=8, pady=8)
        for idx, (key, val) in enumerate(table_data):
            ctk.CTkLabel(grid, text=f"{key}:", font=ctk.CTkFont(weight="bold"), width=120, anchor="w").grid(row=idx // 2, column=(idx % 2) * 2, sticky="w", padx=4, pady=2)
            ctk.CTkLabel(grid, text=val, anchor="w", width=150).grid(row=idx // 2, column=(idx % 2) * 2 + 1, sticky="w", padx=4, pady=2)

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
            self._apply_autodetected_columns()
            self._sync_cutoff_defaults()
            self._refresh_summary_cards()
            self._render_step(self.service.workflow_state.current_step)

    def _apply_autodetected_columns(self) -> None:
        suggestions = self.service.get_autodetected_columns()
        self.x_var.set(suggestions.get("x", ""))
        self.y_var.set(suggestions.get("y", ""))
        self.z_var.set(suggestions.get("z", ""))
        self.target_var.set(suggestions.get("target", ""))
        self.hole_var.set(suggestions.get("hole_id", ""))
        self.domain_var.set(suggestions.get("domain", ""))

    def _on_apply_config(self) -> None:
        result = self.service.set_variable_config(
            self.x_var.get(), self.y_var.get(), self.z_var.get(), self.target_var.get(), self.hole_var.get() or None, self.domain_var.get() or None
        )
        self.status_text.set(result.message)
        self._append_activity(result.message)
        if result.success:
            self.target_label.set(f"Target: {self.target_var.get()}")
            self.domain_label.set(f"Dominio: {self.service.workflow_state.active_domain}")
            self._sync_cutoff_defaults()
            self.data_panel_collapsed = True
            self.service.activity_log.log("data_panel_collapsed", "info", "Panel de datos colapsado automáticamente.", {})
            self._refresh_summary_cards()
            self._render_step(self.service.workflow_state.current_step)

    def _sync_cutoff_defaults(self) -> None:
        self.cutoff_enabled_var.set(False)
        self.cutoff_limits_var.set("")
        self.cutoff_target_var.set(self.target_var.get())
        default_output = f"{self.target_var.get()}_cutoff" if self.target_var.get() else ""
        self.cutoff_output_var.set(default_output)

    def _render_cutoff_stage_panel(self) -> None:
        DashboardGrid.clear(self.cutoff_stage_view)
        state = self.service.get_cutoff_state()
        numeric_columns = self.service.get_numeric_columns()
        target_default = state["target_column"] or self.target_var.get()
        if target_default and not self.cutoff_target_var.get():
            self.cutoff_target_var.set(target_default)
        if state["output_column"]:
            self.cutoff_output_var.set(str(state["output_column"]))
        if state["limits"] and not self.cutoff_limits_var.get():
            self.cutoff_limits_var.set(", ".join(f"{val:.6g}" for val in state["limits"]))
        self.cutoff_enabled_var.set(bool(state["enabled"]))

        ctk.CTkLabel(
            self.cutoff_stage_view,
            text="Paso 3: aplicar cutoffs manuales sobre variable numérica (opcional).",
            justify="left",
        ).pack(anchor="w", padx=8, pady=(8, 6))

        ctk.CTkSwitch(self.cutoff_stage_view, text="Aplicar cutoffs", variable=self.cutoff_enabled_var).pack(anchor="w", padx=8, pady=4)
        ctk.CTkLabel(self.cutoff_stage_view, text="Variable numérica objetivo").pack(anchor="w", padx=8, pady=(8, 2))
        ctk.CTkOptionMenu(
            self.cutoff_stage_view,
            variable=self.cutoff_target_var,
            values=numeric_columns or [""],
            state="normal" if numeric_columns else "disabled",
        ).pack(fill="x", padx=8, pady=(0, 8))

        ctk.CTkLabel(self.cutoff_stage_view, text="Cutoffs manuales (coma o punto y coma)").pack(anchor="w", padx=8, pady=(0, 2))
        ctk.CTkEntry(self.cutoff_stage_view, textvariable=self.cutoff_limits_var, placeholder_text="Ej: 0.5, 1.2, 2.0").pack(fill="x", padx=8, pady=(0, 8))

        ctk.CTkLabel(self.cutoff_stage_view, text="Nombre de salida categorizada").pack(anchor="w", padx=8, pady=(0, 2))
        ctk.CTkEntry(self.cutoff_stage_view, textvariable=self.cutoff_output_var, placeholder_text="target_cutoff").pack(fill="x", padx=8, pady=(0, 8))

        ctk.CTkButton(self.cutoff_stage_view, text="Guardar Paso 3", command=self._on_apply_cutoffs).pack(fill="x", padx=8, pady=(0, 8))
        effective = state["effective_target_column"] or "-"
        ctk.CTkLabel(self.cutoff_stage_view, text=f"Variable efectiva para Espacial: {effective}", justify="left").pack(anchor="w", padx=8, pady=(0, 8))

    def _on_apply_cutoffs(self) -> None:
        result = self.service.apply_cutoffs(
            enabled=bool(self.cutoff_enabled_var.get()),
            target_column=self.cutoff_target_var.get(),
            limits_text=self.cutoff_limits_var.get(),
            output_column=self.cutoff_output_var.get() or None,
        )
        self.status_text.set(result.message)
        self._append_activity(result.message)
        if result.success:
            self._refresh_summary_cards()
            self._render_step("Cutoffs")

    def _refresh_summary_cards(self) -> None:
        cards = self.service.get_summary_cards()
        for key, label in self.summary_value_labels.items():
            label.configure(text=cards.get(key, "-"))

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
