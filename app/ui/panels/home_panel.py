"""Continuous geostat workflow dashboard with fixed-screen technical workspace."""

from __future__ import annotations

from tkinter import filedialog, messagebox
import threading

import customtkinter as ctk

from app.services.geostat_service import GeostatService
from app.ui.panels.dashboard_grid import DashboardGrid


BG_MAIN = "#1c1d21"
BG_PANEL = "#25272c"
BG_SOFT = "#2d3036"
TXT_MAIN = "#f1f3f5"
TXT_MUTED = "#aeb6c2"
C_ORIGINAL = "#3b82f6"
C_TRUNCATED = "#f59e0b"
C_CUTOFF = "#ef4444"
C_ACTIVE = "#2f6ea5"
C_SUCCESS = "#5aa469"
C_TAB_IDLE = "#30343b"
C_TAB_DONE = "#3a485a"
PLOT_TXT = "#1f2937"


class HomePanel(ctk.CTkFrame):
    def __init__(self, parent: ctk.CTk, service: GeostatService) -> None:
        super().__init__(master=parent, fg_color=BG_MAIN)
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
        self.dynamic_percentile_label_var = ctk.StringVar(value="Percentil: P95.0")
        self.dynamic_cutoff_label_var = ctk.StringVar(value="Cutoff actual: -")
        self.dynamic_impact_label_var = ctk.StringVar(value="Impacto: -")
        self.eda_use_capping_var = ctk.BooleanVar(value=False)

        self.log_visible = False
        self.controls_collapsed = False
        self.workflow_buttons: dict[str, ctk.CTkButton] = {}
        self.context_chip_vars: dict[str, ctk.StringVar] = {}
        self.kpi_value_vars: dict[str, ctk.StringVar] = {}
        self.kpi_cards: dict[str, ctk.CTkFrame] = {}

        self.control_sections: dict[str, ctk.CTkFrame] = {}
        self.workspace_title_var = ctk.StringVar(value="Vista Datos")
        self.plot_frame: ctk.CTkFrame | None = None
        self._cutoff_preview_after_id: str | None = None

        self._build_layout()
        self._render_step("Datos")

    def _build_layout(self) -> None:
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_header().grid(row=0, column=0, sticky="ew", padx=8, pady=(7, 3))
        self._build_step_progress().grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 3))

        workspace = ctk.CTkFrame(self, fg_color=BG_MAIN)
        workspace.grid(row=2, column=0, sticky="nsew", padx=8, pady=(0, 4))
        workspace.grid_columnconfigure(1, weight=1)
        workspace.grid_rowconfigure(0, weight=1)

        self.sidebar = self._build_control_panel(workspace)
        self.sidebar.grid(row=0, column=0, sticky="nsw", padx=(0, 6))

        self.content_panel = ctk.CTkFrame(workspace, fg_color=BG_PANEL, corner_radius=10)
        self.content_panel.grid(row=0, column=1, sticky="nsew")
        self.content_panel.grid_columnconfigure(0, weight=1)
        self.content_panel.grid_rowconfigure(2, weight=1)

        top = ctk.CTkFrame(self.content_panel, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=8, pady=(6, 3))
        top.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(top, textvariable=self.workspace_title_var, font=ctk.CTkFont(size=14, weight="bold"), text_color=TXT_MAIN).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(top, textvariable=self.status_text, font=ctk.CTkFont(size=10), text_color=TXT_MUTED).grid(row=0, column=1, sticky="e")

        self._build_kpi_strip(self.content_panel)

        self.view_body = ctk.CTkFrame(self.content_panel, fg_color=BG_PANEL)
        self.view_body.grid(row=2, column=0, sticky="nsew", padx=8, pady=(0, 8))
        self.view_body.grid_columnconfigure(0, weight=1)
        self.view_body.grid_rowconfigure(0, weight=1)

        self.log_panel = ctk.CTkFrame(self, fg_color=BG_PANEL)
        self.log_panel.grid(row=3, column=0, sticky="ew", padx=8, pady=(0, 6))
        self.log_panel.grid_columnconfigure(1, weight=1)
        ctk.CTkButton(
            self.log_panel,
            text="Ocultar/Mostrar log",
            width=130,
            height=22,
            fg_color=BG_SOFT,
            hover_color="#333333",
            command=self._toggle_log,
        ).grid(row=0, column=0, sticky="w", padx=6, pady=4)
        self.log_box = ctk.CTkTextbox(self.log_panel, height=44, fg_color=BG_SOFT, text_color=TXT_MAIN)
        self.log_box.grid(row=0, column=1, sticky="ew", padx=6, pady=3)
        self.log_box.insert("1.0", "Actividad reciente\n")
        self.log_box.configure(state="disabled")
        self.log_box.grid_remove()

    def _build_header(self) -> ctk.CTkFrame:
        header = ctk.CTkFrame(self, fg_color=BG_PANEL, corner_radius=10)
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(header, text="GeoStat Py · Workspace técnico", font=ctk.CTkFont(size=15, weight="bold"), text_color=TXT_MAIN).grid(row=0, column=0, sticky="w", padx=10, pady=(5, 1))

        chip_frame = ctk.CTkFrame(header, fg_color="transparent")
        chip_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 5))
        labels = {
            "dataset": "Dataset no cargado",
            "target": "Target no definido",
            "domain": "Dominio no definido",
            "status": "Estado: Listo",
            "capping": "Capping inactivo",
        }
        for idx, (key, value) in enumerate(labels.items()):
            var = ctk.StringVar(value=value)
            self.context_chip_vars[key] = var
            ctk.CTkLabel(
                chip_frame,
                textvariable=var,
                corner_radius=8,
                fg_color=BG_SOFT,
                text_color=TXT_MAIN,
                padx=7,
                pady=2,
                font=ctk.CTkFont(size=10),
            ).grid(row=0, column=idx, padx=3, sticky="w")

        actions = ctk.CTkFrame(header, fg_color="transparent")
        actions.grid(row=0, column=1, rowspan=2, sticky="e", padx=8)
        self.update_repo_button = ctk.CTkButton(actions, text="Actualizar repo", width=108, height=24, fg_color="#3a434f", hover_color="#4a5563", command=self._on_update_repo)
        self.update_repo_button.pack(side="left", padx=3)
        ctk.CTkButton(actions, text="Exportar log", width=88, height=24, fg_color=BG_SOFT, hover_color="#3a3d44", command=self._on_export_log).pack(side="left", padx=3)
        return header

    def _build_step_progress(self) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(self, fg_color=BG_PANEL, corner_radius=10)
        ctk.CTkLabel(frame, text="Workflow", font=ctk.CTkFont(size=11, weight="bold"), text_color=TXT_MUTED).pack(side="left", padx=(8, 6), pady=3)
        for step in ["Datos", "EDA", "Cutoffs", "Espacial"]:
            btn = ctk.CTkButton(frame, text=step, width=94, height=24, corner_radius=7, fg_color=C_TAB_IDLE, hover_color="#3a3f47", border_width=1, border_color="#454b55", command=lambda s=step: self._on_change_step(s))
            btn.pack(side="left", padx=3, pady=3)
            self.workflow_buttons[step] = btn
        return frame

    def _build_control_panel(self, parent: ctk.CTkFrame) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(parent, width=292, fg_color=BG_PANEL, corner_radius=9)
        frame.grid_propagate(False)

        head = ctk.CTkFrame(frame, fg_color="transparent")
        head.pack(fill="x", padx=8, pady=(6, 3))
        ctk.CTkLabel(head, text="Panel de control", text_color=TXT_MAIN, font=ctk.CTkFont(size=12, weight="bold")).pack(side="left")
        ctk.CTkButton(head, text="Colapsar" if not self.controls_collapsed else "Expandir", width=78, height=22, fg_color="#363a42", hover_color="#454b55", command=self._toggle_controls).pack(side="right")

        self.controls_container = ctk.CTkScrollableFrame(frame, fg_color="transparent")
        self.controls_container.pack(fill="both", expand=True, padx=8, pady=(0, 6))
        self.controls_container.grid_columnconfigure(0, weight=1)
        self._render_control_sections()
        return frame

    def _toggle_controls(self) -> None:
        self.controls_collapsed = not self.controls_collapsed
        if self.controls_collapsed:
            self.controls_container.pack_forget()
        else:
            self.controls_container.pack(fill="both", expand=True, padx=8, pady=(0, 6))
        self._render_control_sections()

    def _render_control_sections(self) -> None:
        for child in self.controls_container.winfo_children():
            child.destroy()
        if self.controls_collapsed:
            ctk.CTkLabel(self.controls_container, text="Panel colapsado", text_color=TXT_MUTED).pack(anchor="w", padx=8, pady=8)
            return

        self.control_sections = {
            "Datos": self._build_data_controls(self.controls_container),
            "EDA": self._build_eda_controls(self.controls_container),
            "Cutoffs": self._build_cutoff_controls(self.controls_container),
            "Espacial": self._build_spatial_controls(self.controls_container),
        }
        self._focus_sidebar_sections(self.service.workflow_state.current_step)

    def _section_shell(self, parent: ctk.CTkScrollableFrame, title: str) -> ctk.CTkFrame:
        section = ctk.CTkFrame(parent, fg_color="transparent")
        section.pack(fill="x", pady=(0, 6))
        ctk.CTkLabel(section, text=title, text_color=TXT_MAIN, font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=6, pady=(4, 3))
        ctk.CTkFrame(section, height=1, fg_color="#3c4048").pack(fill="x", padx=6, pady=(0, 4))
        return section

    def _build_data_controls(self, parent: ctk.CTkScrollableFrame) -> ctk.CTkFrame:
        section = self._section_shell(parent, "Datos y columnas")
        ctk.CTkButton(section, text="Cargar CSV", height=26, fg_color="#3a434f", hover_color="#4a5563", command=self._on_load_csv).pack(fill="x", padx=6, pady=(0, 4))

        # compat: config_grid = ctk.CTkFrame(self.center_panel, fg_color="transparent")
        grid = ctk.CTkFrame(section, fg_color="transparent")
        grid.pack(fill="x", padx=6, pady=(0, 5))
        grid.grid_columnconfigure((0, 1), weight=1)
        cols = self.service.get_available_columns() or [""]
        self._selector(grid, "X", self.x_var, cols, 0, 0)
        self._selector(grid, "Y", self.y_var, cols, 0, 1)
        self._selector(grid, "Z", self.z_var, cols, 2, 0)
        self._selector(grid, "Target", self.target_var, cols, 2, 1)
        self._selector(grid, "Hole ID", self.hole_var, cols, 4, 0)
        self._selector(grid, "Dominio", self.domain_var, cols, 4, 1)
        ctk.CTkButton(grid, text="Aplicar configuración", height=26, fg_color=C_ACTIVE, hover_color="#245883", command=self._on_apply_config).grid(row=6, column=0, columnspan=2, sticky="ew", pady=(3, 0))
        return section

    def _build_eda_controls(self, parent: ctk.CTkScrollableFrame) -> ctk.CTkFrame:
        section = self._section_shell(parent, "Vista analítica")
        has_capping = self.service.has_confirmed_dynamic_capping()
        if not has_capping:
            self.eda_use_capping_var.set(False)
        ctk.CTkSwitch(
            section,
            text="EDA con capping confirmado",
            variable=self.eda_use_capping_var,
            state="normal" if has_capping else "disabled",
            text_color=TXT_MAIN,
            command=self._refresh_dashboard,
        ).pack(fill="x", padx=6, pady=(0, 4))
        ctk.CTkButton(section, text="Actualizar vista", height=24, fg_color="#363a42", hover_color="#454b55", command=self._refresh_dashboard).pack(fill="x", padx=6, pady=(0, 5))
        return section

    def _build_cutoff_controls(self, parent: ctk.CTkScrollableFrame) -> ctk.CTkFrame:
        section = self._section_shell(parent, "Control de capping")
        numeric_columns = self.service.get_numeric_columns()
        ctk.CTkOptionMenu(section, variable=self.cutoff_target_var, values=numeric_columns or [""], state="normal" if numeric_columns else "disabled", height=24, command=lambda _v: self._schedule_cutoff_preview()).pack(fill="x", padx=6, pady=(0, 4))
        ctk.CTkSwitch(section, text="Activar capping dinámico", variable=self.dynamic_cutoff_enabled_var, text_color=TXT_MAIN, command=self._schedule_cutoff_preview).pack(fill="x", padx=6, pady=(0, 4))
        ctk.CTkEntry(section, textvariable=self.cutoff_limits_var, height=24, placeholder_text="Cutoffs manuales: 0.5, 1.2, 2.0").pack(fill="x", padx=6, pady=(0, 4))
        ctk.CTkButton(section, text="Aplicar cutoffs manuales", height=24, fg_color="#363a42", hover_color="#454b55", command=self._on_apply_cutoffs).pack(fill="x", padx=6, pady=(0, 5))
        return section

    def _build_spatial_controls(self, parent: ctk.CTkScrollableFrame) -> ctk.CTkFrame:
        section = self._section_shell(parent, "Visualización espacial")
        ctk.CTkLabel(section, text="Vista fija XY / XZ / YZ + metadatos.", text_color=TXT_MUTED, font=ctk.CTkFont(size=10)).pack(anchor="w", padx=6, pady=(0, 5))
        return section

    def _focus_sidebar_sections(self, step_name: str) -> None:
        for name, frame in self.control_sections.items():
            frame.configure(fg_color=BG_SOFT if name == step_name else "transparent")

    def _build_kpi_strip(self, parent: ctk.CTkFrame) -> None:
        block = ctk.CTkFrame(parent, fg_color=BG_SOFT, corner_radius=7)
        block.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 5))
        cards = ctk.CTkFrame(block, fg_color="transparent")
        cards.pack(fill="x", padx=5, pady=4)
        keys = ["samples", "valid_count", "mean", "p50", "p90", "std", "cv", "% truncado", "cutoff actual"]
        for idx, key in enumerate(keys):
            cards.grid_columnconfigure(idx, weight=1)
            card = ctk.CTkFrame(cards, fg_color="#2b2e35", corner_radius=6)
            card.grid(row=0, column=idx, padx=2, pady=0, sticky="nsew")
            ctk.CTkLabel(card, text=key.upper(), font=ctk.CTkFont(size=8, weight="bold"), text_color=TXT_MUTED).pack(anchor="w", padx=5, pady=(2, 0))
            val = ctk.StringVar(value="-")
            self.kpi_value_vars[key] = val
            self.kpi_cards[key] = card
            ctk.CTkLabel(card, textvariable=val, text_color=TXT_MAIN, font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=5, pady=(0, 2))

    def _apply_kpi_focus(self, step_name: str) -> None:
        focus_by_step = {
            "Datos": {"samples", "valid_count"},
            "EDA": {"valid_count", "mean", "p90", "cv"},
            "Cutoffs": {"cutoff actual", "% truncado"},
            "Espacial": {"samples", "cutoff actual"},
        }
        focus = focus_by_step.get(step_name, set())
        for key, card in self.kpi_cards.items():
            card.configure(fg_color="#344355" if key in focus else "#2b2e35")

    def _build_cutoff_decision_controls(self, parent: ctk.CTkFrame) -> None:
        parent.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkLabel(parent, text="Control de capping", text_color=TXT_MAIN, font=ctk.CTkFont(size=12, weight="bold")).grid(row=0, column=0, columnspan=2, sticky="w", padx=8, pady=(7, 3))

        ctk.CTkOptionMenu(parent, variable=self.dynamic_mode_var, values=["Percentil", "Valor absoluto"], height=26, command=lambda _v: self._schedule_cutoff_preview()).grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 3))
        ctk.CTkEntry(parent, textvariable=self.dynamic_output_var, height=26, placeholder_text="salida capped").grid(row=1, column=1, sticky="ew", padx=8, pady=(0, 3))

        ctk.CTkSlider(parent, from_=0, to=100, variable=self.dynamic_slider_var, command=self._on_slider_change, button_color="#4e7fad", progress_color="#4e7fad").grid(row=2, column=0, columnspan=2, sticky="ew", padx=8, pady=(0, 3))
        ctk.CTkLabel(parent, textvariable=self.dynamic_percentile_label_var, text_color=TXT_MAIN).grid(row=3, column=0, sticky="w", padx=8)
        ctk.CTkLabel(parent, textvariable=self.dynamic_cutoff_label_var, text_color=TXT_MAIN).grid(row=3, column=1, sticky="e", padx=8)

        ctk.CTkFrame(parent, height=1, fg_color="#3c3c3c").grid(row=4, column=0, columnspan=2, sticky="ew", padx=8, pady=4)
        ctk.CTkLabel(parent, textvariable=self.dynamic_impact_label_var, text_color=TXT_MAIN, font=ctk.CTkFont(size=10, weight="bold"), wraplength=350, justify="left").grid(row=5, column=0, columnspan=2, sticky="w", padx=8)

        ctk.CTkSwitch(parent, text="Capping dinámico", variable=self.dynamic_cutoff_enabled_var, text_color=TXT_MAIN, command=self._schedule_cutoff_preview).grid(row=6, column=0, sticky="w", padx=8, pady=(5, 6))
        ctk.CTkButton(parent, text="Confirmar capping", height=28, fg_color="#2b5f8e", hover_color="#245883", command=self._on_apply_dynamic_cutoff).grid(row=6, column=1, sticky="ew", padx=8, pady=(5, 6))

    def _show_stage_view(self, stage: str) -> None:
        DashboardGrid.clear(self.view_body)
        self.view_body.grid_columnconfigure(0, weight=1)
        self.view_body.grid_rowconfigure(0, weight=1)

        if stage == "Datos":
            self.workspace_title_var.set("Vista Datos")
            card = ctk.CTkFrame(self.view_body, fg_color=BG_SOFT, corner_radius=8)
            card.grid(row=0, column=0, sticky="nsew")
            ctk.CTkLabel(card, text="Inicio de configuración", text_color=TXT_MAIN, font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=10, pady=(10, 3))
            ctk.CTkLabel(card, text="1) Cargar CSV · 2) Asignar columnas · 3) Confirmar configuración.", text_color=TXT_MUTED, font=ctk.CTkFont(size=11)).pack(anchor="w", padx=10, pady=(0, 8))
            summary = ctk.CTkFrame(card, fg_color=BG_PANEL, corner_radius=7)
            summary.pack(fill="x", padx=10, pady=(0, 8))
            ctk.CTkLabel(summary, textvariable=self.dataset_label, text_color=TXT_MAIN, font=ctk.CTkFont(size=11)).pack(anchor="w", padx=8, pady=(6, 2))
            ctk.CTkLabel(summary, textvariable=self.target_label, text_color=TXT_MAIN, font=ctk.CTkFont(size=11)).pack(anchor="w", padx=8, pady=2)
            ctk.CTkLabel(summary, textvariable=self.domain_label, text_color=TXT_MAIN, font=ctk.CTkFont(size=11)).pack(anchor="w", padx=8, pady=(2, 6))
            return

        if stage == "EDA":
            self.workspace_title_var.set("Vista EDA")
            self._render_eda_view()
            return

        if stage == "Cutoffs":
            self.workspace_title_var.set("Vista Cutoffs")
            self._render_cutoff_view()
            return

        self.workspace_title_var.set("Vista Espacial")
        self._render_spatial_view()

    def _render_eda_view(self) -> None:
        wrapper = ctk.CTkFrame(self.view_body, fg_color=BG_PANEL)
        wrapper.grid(row=0, column=0, sticky="nsew")
        try:
            data = self.service.prepare_univariate_data(max_domain_categories=10, use_effective_target=bool(self.eda_use_capping_var.get()))
        except Exception as exc:
            ctk.CTkLabel(wrapper, text=f"Sin EDA disponible: {exc}", text_color=TXT_MAIN).pack(anchor="w", padx=8, pady=8)
            return

        grid = DashboardGrid(wrapper, 2, 2, figsize=(12.2, 6.2))
        ax_hist = grid.axis(0, 0)
        ax_box = grid.axis(0, 1)
        ax_prob = grid.axis(1, 0)
        ax_domain = grid.axis(1, 1)

        ax_hist.hist(data["target_values"], bins=24, color=C_ORIGINAL, edgecolor="white", alpha=0.9)
        ax_hist.set_title("Histograma", color=PLOT_TXT)

        ax_box.boxplot(data["target_values"], vert=True, patch_artist=True)
        ax_box.set_title("Boxplot general", color=PLOT_TXT)

        if data.get("probplot_x") and data.get("probplot_y") and not data.get("probability_failed"):
            ax_prob.scatter(data["probplot_x"], data["probplot_y"], s=10, color=C_ACTIVE, alpha=0.85)
            ax_prob.set_title("Probability plot", color=PLOT_TXT)
        else:
            ax_prob.axis("off")
            ax_prob.text(0.5, 0.5, "No disponible", ha="center", va="center", color=PLOT_TXT)

        domain_data = data.get("domain_boxplot", {})
        if domain_data.get("enabled"):
            ax_domain.boxplot(domain_data["values"], labels=domain_data["labels"], patch_artist=True)
            ax_domain.tick_params(axis="x", rotation=22)
            ax_domain.set_title("Dominio", color=PLOT_TXT)
        else:
            ax_domain.axis("off")
            ax_domain.text(0.5, 0.5, domain_data.get("message", "No disponible"), ha="center", va="center", color=PLOT_TXT, wrap=True)
        grid.render()

    def _render_cutoff_view(self) -> None:
        container = ctk.CTkFrame(self.view_body, fg_color=BG_PANEL)
        container.grid(row=0, column=0, sticky="nsew")
        container.grid_columnconfigure((0, 1), weight=1)
        container.grid_rowconfigure((0, 1), weight=1)

        control_card = ctk.CTkFrame(container, fg_color=BG_SOFT, corner_radius=8)
        control_card.grid(row=0, column=0, sticky="nsew", padx=(0, 4), pady=(0, 4))
        self._build_cutoff_decision_controls(control_card)

        plot_card = ctk.CTkFrame(container, fg_color=BG_SOFT, corner_radius=8)
        plot_card.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=(4, 0), pady=(0, 0))
        self.plot_frame = plot_card
        self._refresh_cutoff_preview()

    def _render_spatial_view(self) -> None:
        wrapper = ctk.CTkFrame(self.view_body, fg_color=BG_PANEL)
        wrapper.grid(row=0, column=0, sticky="nsew")
        try:
            result = self.service.prepare_visual_data()
            if not result.success or result.spatial_data is None:
                raise ValueError(result.message)
            spatial = result.spatial_data
        except Exception as exc:
            ctk.CTkLabel(wrapper, text=f"No se pudo renderizar Espacial: {exc}", text_color=TXT_MAIN).pack(anchor="w", padx=8, pady=8)
            return

        grid = DashboardGrid(wrapper, 2, 2, figsize=(12.2, 6.2))
        ax_xy = grid.axis(0, 0)
        ax_xz = grid.axis(0, 1)
        ax_yz = grid.axis(1, 0)
        ax_info = grid.axis(1, 1)

        sc_xy = ax_xy.scatter(spatial.x, spatial.y, c=spatial.target, cmap="viridis", s=10)
        sc_xz = ax_xz.scatter(spatial.x, spatial.z, c=spatial.target, cmap="viridis", s=10)
        sc_yz = ax_yz.scatter(spatial.y, spatial.z, c=spatial.target, cmap="viridis", s=10)

        ax_xy.set_title("XY", color=PLOT_TXT)
        ax_xz.set_title("XZ", color=PLOT_TXT)
        ax_yz.set_title("YZ", color=PLOT_TXT)

        for sc, ax in [(sc_xy, ax_xy), (sc_xz, ax_xz), (sc_yz, ax_yz)]:
            grid.figure.colorbar(sc, ax=ax, shrink=0.76, label=spatial.target_label)

        ax_info.axis("off")
        msg = "Panel metadatos\n\nVistas: XY · XZ · YZ"
        state = self.service.get_cutoff_state()
        if state["dynamic_enabled"]:
            msg += f"\nCapping: {state['dynamic_cutoff_value']:.6g}"
        if spatial.downsampled:
            msg += f"\nMuestreo: {spatial.plotted_points}/{spatial.source_points}"
        ax_info.text(0.05, 0.9, msg, va="top", color=PLOT_TXT, fontsize=10, bbox={"facecolor": "#eef2f7", "edgecolor": "#cbd5e1", "boxstyle": "round,pad=0.45"})
        grid.render()

    def _on_change_step(self, step_name: str) -> None:
        self.status_text.set(self.service.set_workflow_step(step_name))
        self.step_label.set(f"Paso actual: {step_name}")
        self._append_activity(self.status_text.get())
        self._render_step(step_name)

    def _render_step(self, step_name: str) -> None:
        self._paint_workflow_state(step_name)
        self._focus_sidebar_sections(step_name)
        self._refresh_dashboard()

    def _paint_workflow_state(self, active_step: str) -> None:
        ordered = ["Datos", "EDA", "Cutoffs", "Espacial"]
        active_idx = ordered.index(active_step) if active_step in ordered else 0
        for idx, step in enumerate(ordered):
            if idx < active_idx:
                self.workflow_buttons[step].configure(text=f"✓ {step}", fg_color=C_TAB_DONE, hover_color="#455468", border_color="#5a687a")
            elif idx == active_idx:
                self.workflow_buttons[step].configure(text=f"● {step}", fg_color=C_ACTIVE, hover_color="#255b87", border_color="#4d7fae")
            else:
                self.workflow_buttons[step].configure(text=f"○ {step}", fg_color=C_TAB_IDLE, hover_color="#3a3f47", border_color="#454b55")

    def _refresh_dashboard(self) -> None:
        self._refresh_context_chips()
        self._refresh_summary_cards()
        current_step = self.service.workflow_state.current_step
        self._apply_kpi_focus(current_step)
        self._show_stage_view(current_step)

    def _refresh_context_chips(self) -> None:
        state = self.service.get_cutoff_state()
        self.context_chip_vars["dataset"].set(self.dataset_label.get().replace("Dataset: ", "Dataset: "))
        self.context_chip_vars["target"].set(self.target_label.get().replace("Target: ", "Target: "))
        self.context_chip_vars["domain"].set(self.domain_label.get().replace("Dominio: ", "Dominio: "))
        self.context_chip_vars["status"].set(f"Estado: {self.step_label.get().replace('Paso actual: ', '')}")
        if state["dynamic_enabled"]:
            self.context_chip_vars["capping"].set(f"Capping activo P{state['dynamic_percent']:.0f}")
        elif state["enabled"]:
            self.context_chip_vars["capping"].set("Cutoff manual activo")
        else:
            self.context_chip_vars["capping"].set("Capping inactivo")

    def _selector(self, parent: ctk.CTkFrame, label: str, variable: ctk.StringVar, values: list[str], row: int, col: int) -> None:
        ctk.CTkLabel(parent, text=label, text_color=TXT_MUTED, font=ctk.CTkFont(size=10)).grid(row=row, column=col, sticky="w", padx=4)
        state = "normal" if values and values[0] else "disabled"
        ctk.CTkOptionMenu(parent, variable=variable, values=values, state=state, height=24).grid(row=row + 1, column=col, sticky="ew", padx=4, pady=(0, 4))

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
        self._cutoff_preview_after_id = self.after(80, self._refresh_cutoff_preview)

    def _on_slider_change(self, _value: float) -> None:
        self.dynamic_percentile_label_var.set(f"Percentil: P{float(self.dynamic_slider_var.get()):.1f}")
        self._schedule_cutoff_preview()

    def _refresh_cutoff_preview(self) -> None:
        if self.service.workflow_state.current_step != "Cutoffs" or self.plot_frame is None:
            return
        DashboardGrid.clear(self.plot_frame)
        self._render_cutoff_preview_plots(self.plot_frame)

    def _render_cutoff_preview_plots(self, parent: ctk.CTkFrame) -> None:
        target = self.cutoff_target_var.get() or self.target_var.get()
        if not target:
            self.dynamic_cutoff_label_var.set("Cutoff actual: -")
            self.dynamic_impact_label_var.set("Impacto: sin datos para preview")
            ctk.CTkLabel(parent, text="Selecciona variable numérica para preview.", text_color=TXT_MAIN).pack(anchor="w", padx=8, pady=8)
            return

        mode = "absolute" if self.dynamic_mode_var.get() == "Valor absoluto" else "percentile"
        try:
            preview = self.service.prepare_dynamic_cutoff_preview(target, mode, float(self.dynamic_slider_var.get()))
        except Exception as exc:
            self.dynamic_cutoff_label_var.set("Cutoff actual: -")
            self.dynamic_impact_label_var.set("Impacto: no disponible")
            ctk.CTkLabel(parent, text=f"No se pudo generar preview: {exc}", text_color=TXT_MAIN).pack(anchor="w", padx=8, pady=8)
            return

        cutoff = float(preview["cutoff_value"])
        self.dynamic_percentile_label_var.set(f"Percentil: P{float(self.dynamic_slider_var.get()):.1f}")
        self.dynamic_cutoff_label_var.set(f"Cutoff actual: {cutoff:.6g}")
        self.dynamic_impact_label_var.set(
            f"{preview['affected_pct']:.2f}% afectado · {preview['affected_count']} truncadas · Máx {preview['max_original']:.6g} → {preview['max_truncated']:.6g}"
        )

        chart = DashboardGrid(parent, 2, 2, figsize=(8.2, 6.2))
        ax_hist = chart.axis(0, 0)
        ax_cdf = chart.axis(1, 0)
        ax_before_after = chart.axis(1, 1)
        ax_prob = chart.axis(0, 1)

        ax_hist.hist(preview["retained_values"], bins="sturges", color=C_ORIGINAL, alpha=0.86, label="Original")
        if preview["truncated_values"]:
            ax_hist.hist(preview["truncated_values"], bins="sturges", color=C_TRUNCATED, alpha=0.82, label="Truncado")
        ax_hist.axvline(cutoff, color=C_CUTOFF, linestyle="--", linewidth=1.5, label="Cutoff")
        ax_hist.set_title("Histograma + cutoff", color=PLOT_TXT)
        ax_hist.legend(fontsize=8)

        retained_x, retained_y, trunc_x, trunc_y = [], [], [], []
        for x_val, y_val in zip(preview["sorted_values"], preview["theoretical_quantiles"]):
            if x_val <= cutoff:
                retained_x.append(x_val)
                retained_y.append(y_val)
            else:
                trunc_x.append(x_val)
                trunc_y.append(y_val)
        ax_prob.scatter(retained_x, retained_y, s=9, color=C_ORIGINAL, alpha=0.85)
        if trunc_x:
            ax_prob.scatter(trunc_x, trunc_y, s=9, color=C_TRUNCATED, alpha=0.85)
        ax_prob.axvline(cutoff, color=C_CUTOFF, linestyle="--", linewidth=1.4)
        ax_prob.set_title("Probabilidad", color=PLOT_TXT)

        original_sorted = sorted(preview["values"])
        capped_sorted = sorted(preview["capped_values"])
        original_cdf = [(idx + 1) / len(original_sorted) for idx in range(len(original_sorted))]
        capped_cdf = [(idx + 1) / len(capped_sorted) for idx in range(len(capped_sorted))]
        ax_cdf.plot(original_sorted, original_cdf, color=C_ORIGINAL, label="Original")
        ax_cdf.plot(capped_sorted, capped_cdf, color=C_ACTIVE, label="Capped")
        ax_cdf.axvline(cutoff, color=C_CUTOFF, linestyle="--", linewidth=1.2)
        ax_cdf.set_title("Curva acumulada", color=PLOT_TXT)
        ax_cdf.legend(fontsize=8)

        ax_before_after.boxplot([preview["values"], preview["capped_values"]], labels=["Original", "Capped"], patch_artist=True)
        ax_before_after.set_title("Antes vs después", color=PLOT_TXT)
        chart.render()

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
