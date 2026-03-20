"""Continuous geostat workflow dashboard with unified UX (Datos / EDA / Cutoffs / Espacial)."""

from __future__ import annotations

from tkinter import filedialog, messagebox
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
        self.dynamic_cutoff_enabled_var = ctk.BooleanVar(value=False)
        self.dynamic_mode_var = ctk.StringVar(value="Percentil")
        self.dynamic_slider_var = ctk.DoubleVar(value=95.0)
        self.dynamic_output_var = ctk.StringVar(value="")
        self.dynamic_keep_class_var = ctk.BooleanVar(value=True)
        self.cutoff_metrics_var = ctk.StringVar(value="Sin preview.")
        self.dynamic_percentile_label_var = ctk.StringVar(value="Percentil: P95.0")
        self.dynamic_cutoff_label_var = ctk.StringVar(value="Cutoff actual: -")
        self.dynamic_impact_label_var = ctk.StringVar(value="Impacto: -")
        self.eda_use_capping_var = ctk.BooleanVar(value=False)
        self._cutoff_preview_after_id: str | None = None
        self.cutoff_preview_container: ctk.CTkFrame | None = None

        self.log_visible = True
        self.controls_collapsed = False
        self.summary_value_labels: dict[str, ctk.CTkLabel] = {}
        self.workflow_buttons: dict[str, ctk.CTkButton] = {}
        self.context_chip_vars: dict[str, ctk.StringVar] = {}
        self.kpi_value_vars: dict[str, ctk.StringVar] = {}

        self._build_layout()
        self._render_step("Datos")

    def _build_layout(self) -> None:
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_header().grid(row=0, column=0, sticky="ew", pady=(0, 4))
        self._build_step_progress().grid(row=1, column=0, sticky="ew", pady=(0, 4))

        body = ctk.CTkFrame(self)
        body.grid(row=2, column=0, sticky="nsew", pady=(0, 6))
        body.grid_columnconfigure(0, weight=0)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        self.sidebar = self._build_control_panel(body)
        self.sidebar.grid(row=0, column=0, sticky="nsw", padx=(0, 6), pady=4)

        self.right_panel = ctk.CTkFrame(body)
        self.right_panel.grid(row=0, column=1, sticky="nsew", pady=6)
        self.right_panel.grid_columnconfigure(0, weight=1)
        self.right_panel.grid_rowconfigure(0, weight=1)

        self.main_scroll = ctk.CTkScrollableFrame(self.right_panel)
        self.main_scroll.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
        self.main_scroll.grid_columnconfigure(0, weight=1)

        self._build_kpi_strip(self.main_scroll)
        self._build_cutoff_block(self.main_scroll)
        self._build_distribution_block(self.main_scroll)
        self._build_domain_block(self.main_scroll)
        self._build_spatial_block(self.main_scroll)

        self.log_panel = ctk.CTkFrame(self)
        self.log_panel.grid(row=3, column=0, sticky="ew")
        self.log_panel.grid_columnconfigure(1, weight=1)
        ctk.CTkButton(self.log_panel, text="Ocultar/Mostrar log", width=120, height=28, command=self._toggle_log).grid(row=0, column=0, sticky="w", padx=6, pady=3)
        self.log_box = ctk.CTkTextbox(self.log_panel, height=56)
        self.log_box.grid(row=0, column=1, sticky="ew", padx=6, pady=3)
        self.log_box.insert("1.0", "Actividad reciente\n")
        self.log_box.configure(state="disabled")

    def _build_header(self) -> ctk.CTkFrame:
        header = ctk.CTkFrame(self)
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(header, text="GeoStat Py · Control Geoestadístico Ejecutivo", font=ctk.CTkFont(size=17, weight="bold")).grid(row=0, column=0, sticky="w", padx=10, pady=(6, 2))

        chip_frame = ctk.CTkFrame(header, fg_color="transparent")
        chip_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 6))
        labels = {
            "dataset": "Dataset no cargado",
            "target": "Target no definido",
            "domain": "Dominio no definido",
            "status": "Estado operativo: Listo",
            "capping": "Capping inactivo",
        }
        for idx, (key, value) in enumerate(labels.items()):
            var = ctk.StringVar(value=value)
            self.context_chip_vars[key] = var
            chip = ctk.CTkLabel(chip_frame, textvariable=var, corner_radius=12, padx=9, pady=3, font=ctk.CTkFont(size=11))
            chip.grid(row=0, column=idx, padx=3, sticky="w")

        actions = ctk.CTkFrame(header, fg_color="transparent")
        actions.grid(row=0, column=1, rowspan=2, sticky="e", padx=8)
        self.update_repo_button = ctk.CTkButton(actions, text="Actualizar repo", width=124, height=28, fg_color="#334155", hover_color="#475569", command=self._on_update_repo)
        self.update_repo_button.pack(side="left", padx=4)
        ctk.CTkButton(actions, text="Exportar log", width=96, height=28, fg_color="#1f2937", hover_color="#374151", command=self._on_export_log).pack(side="left", padx=4)
        ctk.CTkLabel(actions, textvariable=self.status_text, font=ctk.CTkFont(size=11)).pack(side="left", padx=6)
        return header

    def _build_step_progress(self) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(self)
        ctk.CTkLabel(frame, text="Workflow", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=(8, 6), pady=4)
        for step in ["Datos", "EDA", "Cutoffs", "Espacial"]:
            btn = ctk.CTkButton(frame, text=step, width=104, height=30, corner_radius=12, command=lambda s=step: self._on_change_step(s))
            btn.pack(side="left", padx=3, pady=4)
            self.workflow_buttons[step] = btn
        return frame

    def _build_control_panel(self, parent: ctk.CTkFrame) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(parent, width=332)
        frame.grid_propagate(False)
        head = ctk.CTkFrame(frame, fg_color="transparent")
        head.pack(fill="x", padx=8, pady=(8, 4))
        ctk.CTkLabel(head, text="Panel de control", font=ctk.CTkFont(size=13, weight="bold")).pack(side="left")
        ctk.CTkButton(head, text="Colapsar" if not self.controls_collapsed else "Expandir", width=82, height=26, fg_color="#1f2937", command=self._toggle_controls).pack(side="right")

        self.controls_container = ctk.CTkScrollableFrame(frame)
        self.controls_container.pack(fill="both", expand=True, padx=8, pady=(0, 6))
        self.controls_container.grid_columnconfigure(0, weight=1)

        self._render_control_sections()
        return frame

    def _toggle_controls(self) -> None:
        self.controls_collapsed = not self.controls_collapsed
        if self.controls_collapsed:
            self.controls_container.pack_forget()
        else:
            self.controls_container.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self._render_step(self.service.workflow_state.current_step)

    def _render_control_sections(self) -> None:
        for child in self.controls_container.winfo_children():
            child.destroy()
        if self.controls_collapsed:
            ctk.CTkLabel(self.controls_container, text="Panel colapsado", justify="left").pack(anchor="w", padx=8, pady=8)
            return

        self._build_data_controls(self.controls_container)
        self._build_eda_controls(self.controls_container)
        self._build_cutoff_controls(self.controls_container)
        self._build_spatial_controls(self.controls_container)

    def _build_data_controls(self, parent: ctk.CTkScrollableFrame) -> None:
        section = ctk.CTkFrame(parent)
        section.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(section, text="Datos y columnas", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=8, pady=(7, 3))
        ctk.CTkButton(section, text="Cargar CSV", height=30, command=self._on_load_csv).pack(fill="x", padx=8, pady=(0, 5))

        # compat: config_grid = ctk.CTkFrame(self.center_panel, fg_color="transparent")
        config_grid = ctk.CTkFrame(section, fg_color="transparent")
        config_grid.pack(fill="x", padx=8, pady=(0, 8))
        config_grid.grid_columnconfigure((0, 1), weight=1)
        cols = self.service.get_available_columns() or [""]
        self._selector(config_grid, "X", self.x_var, cols, 0, 0)
        self._selector(config_grid, "Y", self.y_var, cols, 0, 1)
        self._selector(config_grid, "Z", self.z_var, cols, 2, 0)
        self._selector(config_grid, "Target", self.target_var, cols, 2, 1)
        self._selector(config_grid, "Hole ID", self.hole_var, cols, 4, 0)
        self._selector(config_grid, "Dominio", self.domain_var, cols, 4, 1)
        ctk.CTkButton(config_grid, text="Aplicar configuración", height=30, command=self._on_apply_config).grid(row=6, column=0, columnspan=2, sticky="ew", pady=6)

    def _build_eda_controls(self, parent: ctk.CTkScrollableFrame) -> None:
        section = ctk.CTkFrame(parent)
        section.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(section, text="Vista analítica", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=8, pady=(7, 3))
        has_capping = self.service.has_confirmed_dynamic_capping()
        if not has_capping:
            self.eda_use_capping_var.set(False)
        ctk.CTkSwitch(
            section,
            text="EDA con capping confirmado",
            variable=self.eda_use_capping_var,
            state="normal" if has_capping else "disabled",
            command=self._refresh_dashboard,
        ).pack(fill="x", padx=8, pady=(0, 5))
        ctk.CTkButton(section, text="Actualizar panel", height=28, fg_color="#334155", hover_color="#475569", command=self._refresh_dashboard).pack(fill="x", padx=8, pady=(0, 7))

    def _build_cutoff_controls(self, parent: ctk.CTkScrollableFrame) -> None:
        section = ctk.CTkFrame(parent)
        section.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(section, text="Control de capping", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=8, pady=(7, 3))
        numeric_columns = self.service.get_numeric_columns()
        ctk.CTkOptionMenu(section, variable=self.cutoff_target_var, values=numeric_columns or [""], state="normal" if numeric_columns else "disabled", height=28, command=lambda _v: self._schedule_cutoff_preview()).pack(fill="x", padx=8, pady=(0, 4))
        ctk.CTkLabel(section, text="La decisión principal se gestiona en el panel de impacto.", font=ctk.CTkFont(size=11), text_color="#a1a1aa").pack(anchor="w", padx=8, pady=(0, 6))
        ctk.CTkSwitch(section, text="Activar capping dinámico", variable=self.dynamic_cutoff_enabled_var, command=self._schedule_cutoff_preview).pack(anchor="w", padx=8, pady=(0, 4))
        ctk.CTkButton(section, text="Aplicar cutoffs manuales", height=28, fg_color="#1f2937", command=self._on_apply_cutoffs).pack(fill="x", padx=8, pady=(0, 7))

    def _build_spatial_controls(self, parent: ctk.CTkScrollableFrame) -> None:
        section = ctk.CTkFrame(parent)
        section.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(section, text="Visualización espacial", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=8, pady=(7, 3))
        ctk.CTkLabel(section, text="Plano XY, secciones XZ/YZ y escala por ley efectiva.", justify="left", font=ctk.CTkFont(size=11)).pack(anchor="w", padx=8, pady=(0, 7))

    def _build_kpi_strip(self, parent: ctk.CTkScrollableFrame) -> None:
        block = ctk.CTkFrame(parent)
        block.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        ctk.CTkLabel(block, text="Resumen estadístico", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=8, pady=(6, 3))
        cards = ctk.CTkFrame(block, fg_color="transparent")
        cards.pack(fill="x", padx=8, pady=(0, 6))
        for idx, key in enumerate(["samples", "valid_count", "mean", "p50", "p90", "cv", "std", "% truncado", "cutoff actual"]):
            card = ctk.CTkFrame(cards, corner_radius=10)
            card.grid(row=idx // 3, column=idx % 3, padx=3, pady=3, sticky="nsew")
            cards.grid_columnconfigure(idx % 3, weight=1)
            ctk.CTkLabel(card, text=key.upper(), font=ctk.CTkFont(size=10, weight="bold"), text_color="#94a3b8").pack(anchor="w", padx=6, pady=(5, 1))
            var = ctk.StringVar(value="-")
            self.kpi_value_vars[key] = var
            ctk.CTkLabel(card, textvariable=var, font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=6, pady=(0, 5))

    def _build_distribution_block(self, parent: ctk.CTkScrollableFrame) -> None:
        self.distribution_block = ctk.CTkFrame(parent)
        self.distribution_block.grid(row=2, column=0, sticky="nsew", pady=(0, 6))
        ctk.CTkLabel(self.distribution_block, text="Distribución", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=8, pady=(6, 1))
        ctk.CTkLabel(self.distribution_block, text="Histograma, boxplot general y probability plot.", font=ctk.CTkFont(size=11), text_color="#a1a1aa").pack(anchor="w", padx=8, pady=(0, 4))
        self.distribution_content = ctk.CTkFrame(self.distribution_block)
        self.distribution_content.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def _build_domain_block(self, parent: ctk.CTkScrollableFrame) -> None:
        self.domain_block = ctk.CTkFrame(parent)
        self.domain_block.grid(row=3, column=0, sticky="nsew", pady=(0, 6))
        ctk.CTkLabel(self.domain_block, text="Análisis por dominio", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=8, pady=(6, 1))
        ctk.CTkLabel(self.domain_block, text="Comparativa de distribución por dominio activo.", font=ctk.CTkFont(size=11), text_color="#a1a1aa").pack(anchor="w", padx=8, pady=(0, 4))
        self.domain_content = ctk.CTkFrame(self.domain_block)
        self.domain_content.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def _build_cutoff_block(self, parent: ctk.CTkScrollableFrame) -> None:
        self.cutoff_block = ctk.CTkFrame(parent)
        self.cutoff_block.grid(row=1, column=0, sticky="nsew", pady=(0, 6))
        ctk.CTkLabel(self.cutoff_block, text="Impacto del capping", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=8, pady=(6, 1))
        ctk.CTkLabel(self.cutoff_block, text="Panel de decisión: modo, percentil, cutoff e impacto operativo.", font=ctk.CTkFont(size=11), text_color="#a1a1aa").pack(anchor="w", padx=8, pady=(0, 4))
        self._build_cutoff_decision_panel(self.cutoff_block)
        self.cutoff_preview_container = ctk.CTkFrame(self.cutoff_block)
        self.cutoff_preview_container.pack(fill="both", expand=True, padx=8, pady=(0, 6))

    def _build_spatial_block(self, parent: ctk.CTkScrollableFrame) -> None:
        self.spatial_block = ctk.CTkFrame(parent)
        self.spatial_block.grid(row=4, column=0, sticky="nsew", pady=(0, 6))
        ctk.CTkLabel(self.spatial_block, text="Comportamiento espacial", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=8, pady=(6, 1))
        ctk.CTkLabel(self.spatial_block, text="Secciones XY / XZ / YZ con metadatos operativos.", font=ctk.CTkFont(size=11), text_color="#a1a1aa").pack(anchor="w", padx=8, pady=(0, 4))
        self.spatial_content = ctk.CTkFrame(self.spatial_block)
        self.spatial_content.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def _build_cutoff_decision_panel(self, parent: ctk.CTkFrame) -> None:
        decision = ctk.CTkFrame(parent)
        decision.pack(fill="x", padx=8, pady=(0, 6))
        decision.grid_columnconfigure((0, 1, 2, 3), weight=1)

        ctk.CTkLabel(decision, text="Modo activo", font=ctk.CTkFont(size=10), text_color="#94a3b8").grid(row=0, column=0, sticky="w", padx=6, pady=(6, 0))
        ctk.CTkOptionMenu(decision, variable=self.dynamic_mode_var, values=["Percentil", "Valor absoluto"], height=28, command=lambda _v: self._schedule_cutoff_preview()).grid(row=1, column=0, sticky="ew", padx=6, pady=(1, 5))

        ctk.CTkLabel(decision, text="Salida capping", font=ctk.CTkFont(size=10), text_color="#94a3b8").grid(row=0, column=1, sticky="w", padx=6, pady=(6, 0))
        ctk.CTkEntry(decision, textvariable=self.dynamic_output_var, height=28, placeholder_text="columna salida").grid(row=1, column=1, sticky="ew", padx=6, pady=(1, 5))

        ctk.CTkLabel(decision, text="Estado", font=ctk.CTkFont(size=10), text_color="#94a3b8").grid(row=0, column=2, sticky="w", padx=6, pady=(6, 0))
        ctk.CTkSwitch(decision, text="Capping dinámico", variable=self.dynamic_cutoff_enabled_var, command=self._schedule_cutoff_preview).grid(row=1, column=2, sticky="w", padx=6, pady=(0, 5))

        ctk.CTkButton(decision, text="Confirmar capping", height=30, fg_color="#2563eb", hover_color="#1d4ed8", command=self._on_apply_dynamic_cutoff).grid(row=1, column=3, sticky="ew", padx=6, pady=(1, 5))

        slider_row = ctk.CTkFrame(decision, fg_color="transparent")
        slider_row.grid(row=2, column=0, columnspan=4, sticky="ew", padx=6, pady=(0, 4))
        slider_row.grid_columnconfigure(0, weight=1)
        ctk.CTkSlider(slider_row, from_=0, to=100, variable=self.dynamic_slider_var, command=self._on_slider_change).grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ctk.CTkLabel(slider_row, textvariable=self.dynamic_percentile_label_var, font=ctk.CTkFont(size=11, weight="bold")).grid(row=0, column=1, sticky="e")
        ctk.CTkLabel(slider_row, textvariable=self.dynamic_cutoff_label_var, font=ctk.CTkFont(size=11)).grid(row=0, column=2, sticky="e", padx=(8, 0))

        impact = ctk.CTkFrame(decision, fg_color="#1e293b")
        impact.grid(row=3, column=0, columnspan=4, sticky="ew", padx=6, pady=(0, 6))
        ctk.CTkLabel(impact, textvariable=self.dynamic_impact_label_var, font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=8, pady=5)

    def _show_stage_view(self, _stage: str) -> None:
        return

    def _on_change_step(self, step_name: str) -> None:
        self.status_text.set(self.service.set_workflow_step(step_name))
        self.step_label.set(f"Paso actual: {step_name}")
        self._append_activity(self.status_text.get())
        self._render_step(step_name)

    def _render_step(self, step_name: str) -> None:
        self._show_stage_view(step_name)
        self._paint_workflow_state(step_name)
        self._render_control_sections()
        self._refresh_dashboard()

    def _paint_workflow_state(self, active_step: str) -> None:
        ordered = ["Datos", "EDA", "Cutoffs", "Espacial"]
        active_idx = ordered.index(active_step) if active_step in ordered else 0
        for idx, step in enumerate(ordered):
            if idx < active_idx:
                self.workflow_buttons[step].configure(text=f"✓ {step}", fg_color=("#14532d", "#14532d"), hover_color="#166534")
            elif idx == active_idx:
                self.workflow_buttons[step].configure(text=f"● {step}", fg_color=("#1d4ed8", "#1d4ed8"), hover_color="#1e40af")
            else:
                self.workflow_buttons[step].configure(text=f"○ {step}", fg_color=("#1f2937", "#1f2937"), hover_color="#374151")

    def _refresh_dashboard(self) -> None:
        self._refresh_context_chips()
        self._refresh_summary_cards()
        self._render_unified_eda_blocks()
        self._refresh_cutoff_preview()
        self._render_spatial_stage_panel()

    def _refresh_context_chips(self) -> None:
        state = self.service.get_cutoff_state()
        self.context_chip_vars["dataset"].set(self.dataset_label.get().replace("Dataset: ", "Dataset: "))
        self.context_chip_vars["target"].set(self.target_label.get().replace("Target: ", "Target: "))
        self.context_chip_vars["domain"].set(self.domain_label.get().replace("Dominio: ", "Dominio: "))
        self.context_chip_vars["status"].set(f"Estado operativo: {self.step_label.get().replace('Paso actual: ', '')}")
        if state["dynamic_enabled"]:
            self.context_chip_vars["capping"].set(f"Capping activo P{state['dynamic_percent']:.0f}")
        elif state["enabled"]:
            self.context_chip_vars["capping"].set("Cutoff manual activo")
        else:
            self.context_chip_vars["capping"].set("Capping inactivo")

    def _render_unified_eda_blocks(self) -> None:
        DashboardGrid.clear(self.distribution_content)
        DashboardGrid.clear(self.domain_content)
        try:
            data = self.service.prepare_univariate_data(max_domain_categories=10, use_effective_target=bool(self.eda_use_capping_var.get()))
        except Exception as exc:
            ctk.CTkLabel(self.distribution_content, text=f"Sin EDA disponible: {exc}", justify="left").pack(anchor="w", padx=8, pady=8)
            ctk.CTkLabel(self.domain_content, text="Sin boxplot por dominio.", justify="left").pack(anchor="w", padx=8, pady=8)
            return

        dist = DashboardGrid(self.distribution_content, 1, 3, figsize=(11.8, 3.2))
        ax_hist = dist.axis(0, 0)
        ax_box = dist.axis(0, 1)
        ax_prob = dist.axis(0, 2)

        ax_hist.hist(data["target_values"], bins=20, color="#4c78a8", edgecolor="white")
        ax_hist.set_title("Histograma")

        ax_box.boxplot(data["target_values"], vert=True, patch_artist=True)
        ax_box.set_title("Boxplot general")

        if data.get("probplot_x") and data.get("probplot_y") and not data.get("probability_failed"):
            ax_prob.scatter(data["probplot_x"], data["probplot_y"], s=10, color="#54a24b")
            ax_prob.set_title("Probability plot")
        else:
            ax_prob.axis("off")
            ax_prob.text(0.5, 0.5, "No disponible", ha="center", va="center")
        dist.render()

        domain = DashboardGrid(self.domain_content, 1, 2, figsize=(11.8, 2.9))
        ax_domain = domain.axis(0, 0)
        ax_reserved = domain.axis(0, 1)
        domain_data = data.get("domain_boxplot", {})
        if domain_data.get("enabled"):
            ax_domain.boxplot(domain_data["values"], labels=domain_data["labels"], patch_artist=True)
            ax_domain.tick_params(axis="x", rotation=25)
            ax_domain.set_title("Boxplot por dominio")
        else:
            ax_domain.axis("off")
            ax_domain.text(0.5, 0.5, domain_data.get("message", "No disponible"), ha="center", va="center", wrap=True)
        ax_reserved.axis("off")
        ax_reserved.text(
            0.05,
            0.8,
            "Próxima expansión\n• Swath por dominio\n• Curvas por litología\n• Control de soporte",
            va="top",
            fontsize=9,
            bbox={"facecolor": "#1e293b", "edgecolor": "#334155", "boxstyle": "round,pad=0.5"},
        )
        domain.render()

    def _selector(self, parent: ctk.CTkFrame, label: str, variable: ctk.StringVar, values: list[str], row: int, col: int) -> None:
        ctk.CTkLabel(parent, text=label, font=ctk.CTkFont(size=11), text_color="#94a3b8").grid(row=row, column=col, sticky="w", padx=4)
        state = "normal" if values and values[0] else "disabled"
        ctk.CTkOptionMenu(parent, variable=variable, values=values, state=state, height=28).grid(row=row + 1, column=col, sticky="ew", padx=4, pady=(0, 5))

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
            self._refresh_dashboard()

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
            self._refresh_dashboard()

    def _sync_cutoff_defaults(self) -> None:
        self.cutoff_enabled_var.set(False)
        self.cutoff_limits_var.set("")
        self.cutoff_target_var.set(self.target_var.get())
        self.cutoff_output_var.set(f"{self.target_var.get()}_cutoff" if self.target_var.get() else "")
        self.dynamic_cutoff_enabled_var.set(False)
        self.dynamic_mode_var.set("Percentil")
        self.dynamic_slider_var.set(95.0)
        self.dynamic_output_var.set(f"{self.target_var.get()}_capped" if self.target_var.get() else "")
        self.dynamic_keep_class_var.set(True)
        self.dynamic_percentile_label_var.set("Percentil: P95.0")
        self.dynamic_cutoff_label_var.set("Cutoff actual: -")
        self.dynamic_impact_label_var.set("Impacto: Sin preview.")

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
            self._refresh_dashboard()

    def _schedule_cutoff_preview(self) -> None:
        if self._cutoff_preview_after_id is not None:
            self.after_cancel(self._cutoff_preview_after_id)
        self._cutoff_preview_after_id = self.after(120, self._refresh_cutoff_preview)

    def _on_slider_change(self, _value: float) -> None:
        self.dynamic_percentile_label_var.set(f"Percentil: P{float(self.dynamic_slider_var.get()):.1f}")
        self._schedule_cutoff_preview()

    def _refresh_cutoff_preview(self) -> None:
        if self.cutoff_preview_container is None:
            return
        DashboardGrid.clear(self.cutoff_preview_container)
        self._render_cutoff_preview_plots(self.cutoff_preview_container)

    def _render_cutoff_preview_plots(self, parent: ctk.CTkFrame) -> None:
        target = self.cutoff_target_var.get() or self.target_var.get()
        if not target:
            self.dynamic_cutoff_label_var.set("Cutoff actual: -")
            self.dynamic_impact_label_var.set("Impacto: sin datos para preview")
            ctk.CTkLabel(parent, text="Selecciona variable numérica para preview.", justify="left").pack(anchor="w", padx=8, pady=8)
            return

        mode = "absolute" if self.dynamic_mode_var.get() == "Valor absoluto" else "percentile"
        try:
            preview = self.service.prepare_dynamic_cutoff_preview(target, mode, float(self.dynamic_slider_var.get()))
        except Exception as exc:
            self.dynamic_cutoff_label_var.set("Cutoff actual: -")
            self.dynamic_impact_label_var.set("Impacto: no disponible")
            ctk.CTkLabel(parent, text=f"No se pudo generar preview: {exc}", justify="left").pack(anchor="w", padx=8, pady=8)
            return

        cutoff = float(preview["cutoff_value"])
        self.dynamic_percentile_label_var.set(f"Percentil: P{float(self.dynamic_slider_var.get()):.1f}")
        self.dynamic_cutoff_label_var.set(f"Cutoff actual: {cutoff:.6g}")
        self.dynamic_impact_label_var.set(
            f"{preview['affected_pct']:.2f}% afectado · {preview['affected_count']} muestras truncadas · Máx {preview['max_original']:.6g} → {preview['max_truncated']:.6g}"
        )
        dashboard = DashboardGrid(parent, 2, 2, figsize=(11.6, 6.8))
        ax_hist = dashboard.axis(0, 0)
        ax_prob = dashboard.axis(0, 1)
        ax_before_after = dashboard.axis(1, 0)
        ax_decision = dashboard.axis(1, 1)

        ax_hist.hist(preview["retained_values"], bins="sturges", color="#4c78a8", alpha=0.85, label="Retenido")
        if preview["truncated_values"]:
            ax_hist.hist(preview["truncated_values"], bins="sturges", color="#f58518", alpha=0.75, label="Truncado")
        ax_hist.axvline(cutoff, color="#e45756", linestyle="--", linewidth=1.4, label="Cutoff")
        ax_hist.set_title("Histograma + cutoff")
        ax_hist.legend(fontsize=8)

        retained_x, retained_y, trunc_x, trunc_y = [], [], [], []
        for x_val, y_val in zip(preview["sorted_values"], preview["theoretical_quantiles"]):
            if x_val <= cutoff:
                retained_x.append(x_val)
                retained_y.append(y_val)
            else:
                trunc_x.append(x_val)
                trunc_y.append(y_val)
        ax_prob.scatter(retained_x, retained_y, s=10, color="#4c78a8", alpha=0.85, label="Retenido")
        if trunc_x:
            ax_prob.scatter(trunc_x, trunc_y, s=10, color="#f58518", alpha=0.85, label="Truncado")
        ax_prob.axvline(cutoff, color="#e45756", linestyle="--", linewidth=1.4)
        ax_prob.set_title("Probability plot")
        ax_prob.legend(fontsize=8)

        original_sorted = sorted(preview["values"])
        capped_sorted = sorted(preview["capped_values"])
        original_cdf = [(idx + 1) / len(original_sorted) for idx in range(len(original_sorted))]
        capped_cdf = [(idx + 1) / len(capped_sorted) for idx in range(len(capped_sorted))]
        ax_before_after.plot(original_sorted, original_cdf, color="#9c755f", label="Original")
        ax_before_after.plot(capped_sorted, capped_cdf, color="#59a14f", label="Capped")
        ax_before_after.axvline(cutoff, color="#e45756", linestyle="--", linewidth=1.2)
        ax_before_after.set_title("Curva acumulada")
        ax_before_after.legend(fontsize=8)

        ax_decision.boxplot([preview["values"], preview["capped_values"]], labels=["Original", "Capped"], patch_artist=True)
        ax_decision.set_title(f"Impacto: {preview['affected_pct']:.2f}% | max {preview['max_original']:.6g} -> {preview['max_truncated']:.6g}")
        dashboard.render()

    def _on_apply_dynamic_cutoff(self) -> None:
        mode = "absolute" if self.dynamic_mode_var.get() == "Valor absoluto" else "percentile"
        result = self.service.apply_dynamic_cutoff(
            enabled=bool(self.dynamic_cutoff_enabled_var.get()),
            target_column=self.cutoff_target_var.get() or self.target_var.get(),
            mode=mode,
            slider_percent=float(self.dynamic_slider_var.get()),
            output_column=self.dynamic_output_var.get() or None,
            keep_category_column=bool(self.dynamic_keep_class_var.get()),
        )
        self.status_text.set(result.message)
        self._append_activity(f"{result.message} (cutoff={result.cutoff_value:.6g})" if result.success else result.message)
        if result.success:
            self._refresh_dashboard()

    def _refresh_summary_cards(self) -> None:
        stats_table = self.service.get_target_statistics_table(use_effective_target=bool(self.eda_use_capping_var.get()))
        stats_map = {str(k).lower(): str(v) for k, v in stats_table}
        self.kpi_value_vars["samples"].set(stats_map.get("samples", stats_map.get("muestras", "-")))
        self.kpi_value_vars["valid_count"].set(stats_map.get("valid_count", stats_map.get("válidos", "-")))
        self.kpi_value_vars["mean"].set(stats_map.get("mean", stats_map.get("media", "-")))
        self.kpi_value_vars["p50"].set(stats_map.get("p50", "-"))
        self.kpi_value_vars["p90"].set(stats_map.get("p90", "-"))
        self.kpi_value_vars["cv"].set(stats_map.get("cv", "-"))
        self.kpi_value_vars["std"].set(stats_map.get("std", stats_map.get("desv", "-")))

        state = self.service.get_cutoff_state()
        cutoff_actual = "-"
        trunc_pct = "-"
        if state["dynamic_enabled"]:
            cutoff_actual = f"{state['dynamic_cutoff_value']:.6g}"
            target = str(state["dynamic_target_column"] or self.target_var.get())
            mode = str(state["dynamic_mode"])
            slider = float(state["dynamic_percent"])
            try:
                preview = self.service.prepare_dynamic_cutoff_preview(target, mode, slider)
                trunc_pct = f"{preview['affected_pct']:.2f}%"
            except Exception:
                trunc_pct = "-"
        elif state["enabled"] and state["limits"]:
            cutoff_actual = ", ".join(f"{float(v):.4g}" for v in state["limits"])
        self.kpi_value_vars["% truncado"].set(trunc_pct)
        self.kpi_value_vars["cutoff actual"].set(cutoff_actual)

    def _render_spatial_stage_panel(self) -> None:
        DashboardGrid.clear(self.spatial_content)
        try:
            result = self.service.prepare_visual_data()
            if not result.success or result.spatial_data is None:
                raise ValueError(result.message)
            spatial = result.spatial_data
        except Exception as exc:
            ctk.CTkLabel(self.spatial_content, text=f"No se pudo renderizar Espacial: {exc}", justify="left").pack(anchor="w", padx=8, pady=8)
            return

        dashboard = DashboardGrid(self.spatial_content, 2, 2, figsize=(11.2, 6.0))
        ax_xy = dashboard.axis(0, 0)
        ax_xz = dashboard.axis(0, 1)
        ax_yz = dashboard.axis(1, 0)
        ax_info = dashboard.axis(1, 1)

        sc_xy = ax_xy.scatter(spatial.x, spatial.y, c=spatial.target, cmap="viridis", s=12)
        sc_xz = ax_xz.scatter(spatial.x, spatial.z, c=spatial.target, cmap="viridis", s=12)
        sc_yz = ax_yz.scatter(spatial.y, spatial.z, c=spatial.target, cmap="viridis", s=12)

        ax_xy.set_title("XY (planta)")
        ax_xz.set_title("XZ (sección)")
        ax_yz.set_title("YZ (sección)")

        for sc, ax in [(sc_xy, ax_xy), (sc_xz, ax_xz), (sc_yz, ax_yz)]:
            dashboard.figure.colorbar(sc, ax=ax, shrink=0.78, label=spatial.target_label)

        ax_info.axis("off")
        msg = "Panel de metadatos espaciales\n\nVistas activas: XY · XZ · YZ."
        state = self.service.get_cutoff_state()
        if state["dynamic_enabled"]:
            msg += f"\nCapping activo: {state['dynamic_output_column']} @ {state['dynamic_cutoff_value']:.6g}."
        elif state["enabled"]:
            msg += f"\nCutoff manual activo: {state['output_column']}"
        if spatial.downsampled:
            msg += f"\nMuestreo: {spatial.plotted_points}/{spatial.source_points} puntos."
        ax_info.text(0.05, 0.9, msg, va="top", fontsize=9, bbox={"facecolor": "#1e293b", "edgecolor": "#334155", "boxstyle": "round,pad=0.5"})
        dashboard.render()

    def _on_update_repo(self) -> None:
        if not messagebox.askyesno("Confirmar actualización", "Esto actualizará el repositorio. ¿Continuar?"):
            self._append_activity("Actualización de repositorio cancelada por usuario.")
            return
        self.update_repo_button.configure(state="disabled")
        self.status_text.set("Actualizando repo...")

        def worker() -> None:
            result = self.service.update_repository()
            self.after(0, lambda: self._finish_repo_update(result.message, result.details))

        threading.Thread(target=worker, daemon=True).start()

    def _finish_repo_update(self, message: str, details: str) -> None:
        self.update_repo_button.configure(state="normal")
        prefix = "✅" if "actualizado" in message.lower() or "correctamente" in message.lower() else "⚠️"
        self.status_text.set(f"{prefix} {message}")
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
