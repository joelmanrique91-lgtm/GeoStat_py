"""Continuous geostat workflow dashboard with fixed-screen technical workspace."""

from __future__ import annotations

import math
from tkinter import filedialog, messagebox
import threading

import customtkinter as ctk
from matplotlib.ticker import ScalarFormatter

from app.services.geostat_service import GeostatService
from app.ui.panels.dashboard_grid import DashboardGrid
from app.ui.theme import (
    BG_CARD,
    BG_MAIN,
    BG_PANEL,
    BORDER_SOFT,
    BTN_PRIMARY_HOVER,
    BTN_SECONDARY_BG,
    BTN_SECONDARY_HOVER,
    CHART_FONT_SIZE_LABEL,
    CHART_FONT_SIZE_LEGEND,
    CHART_FONT_SIZE_TICK,
    CHIP_BG,
    DIVIDER_SOFT,
    FONT_BODY,
    FONT_KPI,
    FONT_SMALL,
    FONT_SUBTITLE,
    FONT_TITLE,
    KPI_PRIMARY_BG,
    SEM_BLUE,
    SEM_BLUE_SOFT,
    SEM_GRAY,
    SEM_GREEN,
    SEM_ORANGE,
    SEM_RED,
    SEM_WHITE,
    TEXT_MAIN,
    TEXT_MUTED,
    WF_ACTIVE,
    WF_BLOCKED,
    WF_IDLE,
    WF_READY,
    WF_WARNING,
    add_reference_line,
    apply_axis_style,
    get_continuous_colormap,
    get_domain_color,
)
BG_SOFT = BG_CARD
TXT_MAIN = TEXT_MAIN
TXT_MUTED = TEXT_MUTED
C_ORIGINAL = SEM_GRAY
C_TRUNCATED = SEM_BLUE
C_CUTOFF = SEM_ORANGE
C_ACTIVE = SEM_BLUE
C_SUCCESS = SEM_GREEN
C_TAB_IDLE = WF_IDLE
C_TAB_DONE = WF_READY
BTN_NEUTRAL = BTN_SECONDARY_BG
BTN_NEUTRAL_HOVER = BTN_SECONDARY_HOVER
KPI_PRIMARY = KPI_PRIMARY_BG
KPI_PRIMARY_FOCUS = WF_ACTIVE
PLOT_TXT = TEXT_MAIN

PAD_MAIN_X = 8
PAD_CARD_X = 10
PAD_STACK_Y = 4
PAD_SECTION_Y = 8
SIDEBAR_WIDTH = 298


def ui_font(token: dict[str, object]) -> ctk.CTkFont:
    return ctk.CTkFont(size=int(token["size"]), weight=str(token["weight"]))

STEP_TO_READINESS_KEY = {
    "Datos": "data",
    "EDA": "eda",
    "Cutoffs": "cutoffs",
    "Espacial": "spatial",
    "Dominios": "domains",
}

BLOCKING_REASON_HINTS = {
    "missing_dataset": "Carga un CSV para continuar.",
    "missing_variable_config": "Configura y confirma X/Y/Z/target.",
    "missing_resolved_target_column": "Revisa target/cutoffs y confirma la variable activa.",
    "missing_spatial_columns": "Reconfigura columnas espaciales X/Y/Z.",
    "missing_domain_column": "Aplica una definición de dominios para habilitar esta etapa.",
    "non_numeric_target_for_domain_stats": "Usa un target numérico para estadísticas de dominios.",
    "invalid_active_domain_filter_column": "Limpia o corrige el filtro de dominio activo.",
}


def _build_workflow_stage_label(step_name: str, active_step: str, readiness: dict[str, object]) -> str:
    labels = {"Datos": "Datos", "EDA": "EDA", "Cutoffs": "Control de outliers", "Espacial": "Espacial", "Dominios": "Dominios"}
    stage_key = STEP_TO_READINESS_KEY.get(step_name, "")
    stage_state = readiness.get("stages", {}).get(stage_key, {}) if isinstance(readiness, dict) else {}
    is_ready = bool(stage_state.get("ready"))
    has_warning = bool(stage_state.get("warnings"))
    readiness_marker = "✓" if is_ready else ("⚠" if has_warning else "!")
    nav_marker = "●" if step_name == active_step else "○"
    return f"{nav_marker} {labels.get(step_name, step_name)} {readiness_marker}"


def _build_active_step_hint(step_name: str, readiness: dict[str, object]) -> str:
    stage_key = STEP_TO_READINESS_KEY.get(step_name, "")
    stage_state = readiness.get("stages", {}).get(stage_key, {}) if isinstance(readiness, dict) else {}
    if bool(stage_state.get("ready")):
        warnings = [str(item) for item in stage_state.get("warnings", []) if str(item)]
        if warnings:
            return "Advertencia: hay filtros activos que reducen resultados."
        return "Etapa lista."
    blocking = [str(item) for item in stage_state.get("blocking_reasons", []) if str(item)]
    if not blocking:
        return "Etapa no lista."
    return BLOCKING_REASON_HINTS.get(blocking[0], "Completa la configuración requerida para desbloquear esta etapa.")


def _build_context_chip_texts(snapshot: dict[str, object], readiness: dict[str, object], dataset_name: str) -> dict[str, str]:
    resolved_target = str(snapshot.get("resolved_target_column") or "No definido")
    domain_col = str(snapshot.get("active_domain_column") or "No definido")
    domain_filter = str(snapshot.get("active_domain_filter") or "Todos")
    stages = readiness.get("stages", {}) if isinstance(readiness, dict) else {}
    blocked = [name for name, state in stages.items() if not bool(state.get("ready"))] if isinstance(stages, dict) else []
    status = "Listo" if not blocked else f"Bloqueos: {len(blocked)}"
    return {
        "dataset": f"Dataset: {dataset_name}",
        "target": f"Target activo: {resolved_target}",
        "domain": f"Dominio/filtro: {domain_col} · {domain_filter}",
        "status": f"Workflow: {status}",
    }


def _build_visual_context_line(snapshot: dict[str, object], *, local_override: str | None = None) -> str:
    resolved_target = str(snapshot.get("resolved_target_column") or "No definido")
    domain_col = str(snapshot.get("active_domain_column") or "No definido")
    domain_filter = str(snapshot.get("active_domain_filter") or "Todos")
    parts = [f"Target global: {resolved_target}"]
    if local_override and local_override != resolved_target:
        parts.append(f"Override local: {local_override}")
    parts.append(f"Dominio/filtro: {domain_col} · {domain_filter}")
    return " | ".join(parts)


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
        self.use_domain_var = ctk.BooleanVar(value=False)
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
        self.domain_base_var = ctk.StringVar(value="")
        self.domain_name_var = ctk.StringVar(value="")
        self.spatial_color_var = ctk.StringVar(value="")
        self.domain_filter_var = ctk.StringVar(value="Todos")
        self.domain_definition_local: dict[str, list[str]] = {}
        self.domain_feedback_var = ctk.StringVar(value="Define dominios para comenzar.")
        self.domain_selected_categories: set[str] = set()
        self.domain_category_checkbox_vars: dict[str, ctk.BooleanVar] = {}
        self.domain_assign_button: ctk.CTkButton | None = None
        self.domain_apply_button: ctk.CTkButton | None = None
        self.domain_records_var = ctk.StringVar(value="Selecciona una burbuja para visualizar resumen analítico e índices de registros.")

        self.log_visible = False
        self.controls_collapsed = False
        self.workflow_buttons: dict[str, ctk.CTkButton] = {}
        self.context_chip_vars: dict[str, ctk.StringVar] = {}
        self.kpi_value_vars: dict[str, ctk.StringVar] = {}
        self.kpi_cards: dict[str, ctk.CTkFrame] = {}
        self.eda_capping_switch: ctk.CTkSwitch | None = None
        self.domain_menu_widget: ctk.CTkOptionMenu | None = None
        self.column_menus: dict[str, ctk.CTkOptionMenu] = {}
        self.show_aux_controls_var = ctk.BooleanVar(value=False)
        self.action_bar_body: ctk.CTkFrame | None = None

        self.control_sections: dict[str, ctk.CTkFrame] = {}
        self.workspace_title_var = ctk.StringVar(value="Vista Datos")
        self.workspace_subtitle_var = ctk.StringVar(value="Carga y configura columnas para habilitar el flujo analítico.")
        self.workflow_hint_var = ctk.StringVar(value="Etapa lista.")
        self.plot_frame: ctk.CTkFrame | None = None
        self._cutoff_preview_after_id: str | None = None
        self._last_cutoff_preview_signature: tuple[object, ...] | None = None
        self.domain_name_var.trace_add("write", self._on_domain_name_changed)

        self._build_layout()
        self._render_step("Datos")

    def _build_layout(self) -> None:
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_header().grid(row=0, column=0, sticky="ew", padx=PAD_MAIN_X, pady=(7, 4))
        self._build_step_progress().grid(row=1, column=0, sticky="ew", padx=PAD_MAIN_X, pady=(0, 4))

        workspace = ctk.CTkFrame(self, fg_color=BG_MAIN)
        workspace.grid(row=2, column=0, sticky="nsew", padx=PAD_MAIN_X, pady=(0, PAD_STACK_Y))
        workspace.grid_columnconfigure(0, weight=1)
        workspace.grid_rowconfigure(0, weight=1)

        self.content_panel = ctk.CTkFrame(workspace, fg_color=BG_PANEL, corner_radius=10)
        self.content_panel.grid(row=0, column=0, sticky="nsew")
        self.content_panel.grid_columnconfigure(0, weight=1)
        self.content_panel.grid_rowconfigure(3, weight=1)

        top = ctk.CTkFrame(self.content_panel, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=PAD_MAIN_X, pady=(6, 4))
        top.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(top, textvariable=self.workspace_title_var, font=ui_font(FONT_TITLE), text_color=TXT_MAIN).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(top, textvariable=self.status_text, font=ui_font(FONT_SMALL), text_color=TXT_MUTED).grid(row=0, column=1, sticky="e")
        ctk.CTkLabel(top, textvariable=self.workspace_subtitle_var, font=ui_font(FONT_SMALL), text_color=TXT_MUTED).grid(row=1, column=0, sticky="w", pady=(1, 0))
        ctk.CTkLabel(top, textvariable=self.workflow_hint_var, font=ui_font(FONT_SMALL), text_color=SEM_ORANGE).grid(row=2, column=0, sticky="w", pady=(1, 0))

        self._build_kpi_strip(self.content_panel)
        self._build_stage_action_bar(self.content_panel)

        self.view_body = ctk.CTkFrame(self.content_panel, fg_color=BG_PANEL)
        self.view_body.grid(row=3, column=0, sticky="nsew", padx=PAD_MAIN_X, pady=(0, PAD_MAIN_X))
        self.view_body.grid_columnconfigure(0, weight=1)
        self.view_body.grid_rowconfigure(0, weight=1)

        self.aux_controls_host = self._build_control_panel(self.content_panel)
        self.aux_controls_host.grid(row=4, column=0, sticky="ew", padx=PAD_MAIN_X, pady=(0, 6))
        self.aux_controls_host.grid_remove()

        self.log_panel = ctk.CTkFrame(self, fg_color=BG_PANEL)
        self.log_panel.grid(row=3, column=0, sticky="ew", padx=PAD_MAIN_X, pady=(0, 6))
        self.log_panel.grid_columnconfigure(1, weight=1)
        ctk.CTkButton(
            self.log_panel,
            text="Ocultar/Mostrar log",
            width=130,
            height=22,
            fg_color=BG_SOFT,
            hover_color=BTN_NEUTRAL_HOVER,
            command=self._toggle_log,
        ).grid(row=0, column=0, sticky="w", padx=6, pady=4)
        self.log_box = ctk.CTkTextbox(self.log_panel, height=44, fg_color=BG_SOFT, text_color=TXT_MAIN, font=ui_font(FONT_SMALL))
        self.log_box.grid(row=0, column=1, sticky="ew", padx=6, pady=3)
        self.log_box.insert("1.0", "Actividad reciente\n")
        self.log_box.configure(state="disabled")
        self.log_box.grid_remove()

    def _build_header(self) -> ctk.CTkFrame:
        header = ctk.CTkFrame(self, fg_color=BG_PANEL, corner_radius=12)
        header.grid_columnconfigure(0, weight=1)
        header.grid_columnconfigure(1, weight=0)
        identity = ctk.CTkFrame(header, fg_color="transparent")
        identity.grid(row=0, column=0, sticky="w", padx=PAD_CARD_X, pady=(7, 1))
        ctk.CTkLabel(identity, text="GeoStat Py", font=ui_font(FONT_TITLE), text_color=TXT_MAIN).pack(anchor="w")
        ctk.CTkLabel(identity, text="Geoestadística aplicada · panel ejecutivo", text_color=TXT_MUTED, font=ui_font(FONT_SMALL)).pack(anchor="w", pady=(0, 1))

        ctk.CTkLabel(header, text="Contexto activo para decisión", text_color=TXT_MUTED, font=ui_font(FONT_SMALL)).grid(row=1, column=0, sticky="w", padx=PAD_CARD_X, pady=(2, 0))

        chip_frame = ctk.CTkFrame(header, fg_color="transparent")
        chip_frame.grid(row=2, column=0, sticky="ew", padx=PAD_CARD_X, pady=(0, 7))
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
                corner_radius=10,
                fg_color=CHIP_BG,
                text_color=TXT_MAIN,
                padx=PAD_CARD_X,
                pady=4,
                font=ui_font(FONT_SMALL),
            ).grid(row=0, column=idx, padx=3, sticky="w")

        actions = ctk.CTkFrame(header, fg_color=BG_SOFT, corner_radius=9)
        actions.grid(row=0, column=1, rowspan=3, sticky="e", padx=8, pady=6)
        ctk.CTkLabel(actions, text="Acciones globales", text_color=TXT_MUTED, font=ui_font(FONT_SMALL)).pack(anchor="w", padx=8, pady=(6, 2))
        actions_row = ctk.CTkFrame(actions, fg_color="transparent")
        actions_row.pack(fill="x", padx=6, pady=(0, 6))
        self.update_repo_button = ctk.CTkButton(actions_row, text="Actualizar repo", width=108, height=24, fg_color=BTN_NEUTRAL, hover_color=BTN_NEUTRAL_HOVER, command=self._on_update_repo)
        self.update_repo_button.pack(side="left", padx=3)
        ctk.CTkButton(actions_row, text="Exportar log", width=88, height=24, fg_color=BTN_NEUTRAL, hover_color=BTN_NEUTRAL_HOVER, command=self._on_export_log).pack(side="left", padx=3)
        return header

    def _build_step_progress(self) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(self, fg_color=BG_PANEL, corner_radius=10)
        ctk.CTkLabel(frame, text="Workflow y readiness", font=ui_font(FONT_SUBTITLE), text_color=TXT_MUTED).pack(side="left", padx=(PAD_MAIN_X, 6), pady=4)
        labels = {"Datos": "Datos", "EDA": "EDA", "Cutoffs": "Control de outliers", "Espacial": "Espacial", "Dominios": "Dominios"}
        for step in ["Datos", "EDA", "Cutoffs", "Espacial", "Dominios"]:
            btn = ctk.CTkButton(
                frame,
                text=labels[step],
                width=120,
                height=24,
                corner_radius=7,
                fg_color=C_TAB_IDLE,
                hover_color=BTN_NEUTRAL_HOVER,
                border_width=1,
                border_color=BORDER_SOFT,
                command=lambda s=step: self._on_change_step(s),
            )
            btn.pack(side="left", padx=3, pady=4)
            self.workflow_buttons[step] = btn
        return frame

    def _build_control_panel(self, parent: ctk.CTkFrame) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(parent, width=SIDEBAR_WIDTH, fg_color=BG_PANEL, corner_radius=9)
        frame.grid_propagate(False)

        head = ctk.CTkFrame(frame, fg_color="transparent")
        head.pack(fill="x", padx=8, pady=(6, 3))
        ctk.CTkLabel(head, text="Panel de control", text_color=TXT_MAIN, font=ui_font(FONT_SUBTITLE)).pack(side="left")
        ctk.CTkButton(head, text="Colapsar" if not self.controls_collapsed else "Expandir", width=78, height=22, fg_color=BTN_NEUTRAL, hover_color=BTN_NEUTRAL_HOVER, command=self._toggle_controls).pack(side="right")

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
        self.column_menus = {}
        if self.controls_collapsed:
            ctk.CTkLabel(self.controls_container, text="Panel colapsado", text_color=TXT_MUTED, font=ui_font(FONT_SMALL)).pack(anchor="w", padx=8, pady=8)
            return

        self.control_sections = {
            "Datos": self._build_data_controls(self.controls_container),
            "EDA": self._build_eda_controls(self.controls_container),
            "Cutoffs": self._build_cutoff_controls(self.controls_container),
            "Espacial": self._build_spatial_controls(self.controls_container),
            "Dominios": self._build_domains_controls(self.controls_container),
        }
        self._focus_sidebar_sections(self.service.workflow_state.current_step)

    def _section_shell(self, parent: ctk.CTkScrollableFrame, title: str) -> ctk.CTkFrame:
        section = ctk.CTkFrame(parent, fg_color=BG_SOFT, corner_radius=8)
        section.pack(fill="x", pady=(0, PAD_SECTION_Y))
        ctk.CTkLabel(section, text=title, text_color=TXT_MAIN, font=ui_font(FONT_SUBTITLE)).pack(anchor="w", padx=8, pady=(6, 3))
        ctk.CTkFrame(section, height=1, fg_color=DIVIDER_SOFT).pack(fill="x", padx=6, pady=(0, 4))
        return section

    def _build_data_controls(self, parent: ctk.CTkScrollableFrame) -> ctk.CTkFrame:
        section = self._section_shell(parent, "Datos y columnas")
        ctk.CTkLabel(section, text="1) Cargar dataset", text_color=TXT_MUTED, font=ui_font(FONT_SMALL)).pack(anchor="w", padx=6, pady=(0, 2))
        ctk.CTkButton(section, text="Cargar CSV", height=26, fg_color=BTN_NEUTRAL, hover_color=BTN_NEUTRAL_HOVER, command=self._on_load_csv).pack(fill="x", padx=6, pady=(0, 5))
        ctk.CTkLabel(section, textvariable=self.dataset_label, text_color=TXT_MUTED, font=ui_font(FONT_SMALL)).pack(anchor="w", padx=6, pady=(0, 6))

        grid = ctk.CTkFrame(section, fg_color="transparent")
        grid.pack(fill="x", padx=6, pady=(0, 5))
        grid.grid_columnconfigure((0, 1), weight=1)
        cols = self.service.get_available_columns() or [""]
        numeric_cols = self.service.get_numeric_columns() or [""]
        domain_candidates = self.service.get_domain_candidate_columns() or [""]
        row = 0
        ctk.CTkLabel(grid, text="2) Coordenadas (obligatorio)", text_color=SEM_ORANGE, font=ui_font(FONT_SMALL)).grid(row=row, column=0, columnspan=2, sticky="w", padx=4, pady=(0, 2))
        row += 1
        self._selector(grid, "X", self.x_var, cols, row, 0, key="x")
        self._selector(grid, "Y", self.y_var, cols, row, 1, key="y")
        row += 2
        self._selector(grid, "Z", self.z_var, cols, row, 0, key="z")
        row += 2
        ctk.CTkLabel(grid, text="3) Variable objetivo (obligatorio)", text_color=SEM_ORANGE, font=ui_font(FONT_SMALL)).grid(row=row, column=0, columnspan=2, sticky="w", padx=4, pady=(2, 2))
        row += 1
        self._selector(grid, "Target (ley)", self.target_var, numeric_cols, row, 0, key="target")
        row += 2
        ctk.CTkLabel(grid, text="4) Dominio (opcional)", text_color=TXT_MUTED, font=ui_font(FONT_SMALL)).grid(row=row, column=0, columnspan=2, sticky="w", padx=4, pady=(4, 2))
        row += 1
        ctk.CTkCheckBox(grid, text="Analizar por dominios", variable=self.use_domain_var, command=self._on_domain_mode_change).grid(row=row, column=0, columnspan=2, sticky="w", padx=4, pady=(0, 2))
        row += 1
        domain_state = "normal" if bool(self.use_domain_var.get()) else "disabled"
        self.domain_menu_widget = ctk.CTkOptionMenu(grid, variable=self.domain_var, values=domain_candidates, state=domain_state, height=24)
        self.domain_menu_widget.grid(row=row, column=0, columnspan=2, sticky="ew", padx=4, pady=(0, 4))
        row += 1
        ctk.CTkLabel(grid, text="5) Hole ID (opcional)", text_color=TXT_MUTED, font=ui_font(FONT_SMALL)).grid(row=row, column=0, columnspan=2, sticky="w", padx=4, pady=(4, 2))
        row += 1
        self._selector(grid, "Hole ID", self.hole_var, cols, row, 0, key="hole")
        row += 2
        ctk.CTkLabel(grid, text="6) Confirmar", text_color=TXT_MAIN, font=ui_font(FONT_SMALL)).grid(row=row, column=0, columnspan=2, sticky="w", padx=4, pady=(6, 2))
        row += 1
        ctk.CTkButton(grid, text="Confirmar datos", height=28, fg_color=C_ACTIVE, hover_color=BTN_PRIMARY_HOVER, command=self._on_apply_config).grid(row=row, column=0, columnspan=2, sticky="ew", pady=(2, 0))
        return section

    def _build_eda_controls(self, parent: ctk.CTkScrollableFrame) -> ctk.CTkFrame:
        section = self._section_shell(parent, "Vista analítica")
        ctk.CTkLabel(section, text="Opciones locales de la vista EDA", text_color=TXT_MUTED, font=ui_font(FONT_SMALL)).pack(anchor="w", padx=6, pady=(0, 2))
        has_capping = self.service.has_confirmed_dynamic_capping()
        if not has_capping:
            self.eda_use_capping_var.set(False)
        self.eda_capping_switch = ctk.CTkSwitch(
            section,
            text="EDA con capping confirmado",
            variable=self.eda_use_capping_var,
            state="normal" if has_capping else "disabled",
            text_color=TXT_MAIN,
            command=self._on_toggle_eda_capping,
        )
        self.eda_capping_switch.pack(fill="x", padx=6, pady=(0, 4))
        ctk.CTkButton(section, text="Actualizar vista", height=24, fg_color=BTN_NEUTRAL, hover_color=BTN_NEUTRAL_HOVER, command=self._on_refresh_eda).pack(fill="x", padx=6, pady=(0, 5))
        return section

    def _build_cutoff_controls(self, parent: ctk.CTkScrollableFrame) -> ctk.CTkFrame:
        section = self._section_shell(parent, "Control de outliers")
        ctk.CTkLabel(section, text="Opciones locales de preview/aplicación", text_color=TXT_MUTED, font=ui_font(FONT_SMALL)).pack(anchor="w", padx=6, pady=(0, 2))
        numeric_columns = self.service.get_numeric_columns()
        ctk.CTkOptionMenu(section, variable=self.cutoff_target_var, values=numeric_columns or [""], state="normal" if numeric_columns else "disabled", height=24, command=lambda _v: self._schedule_cutoff_preview()).pack(fill="x", padx=6, pady=(0, 4))
        ctk.CTkSwitch(section, text="Activar cutoffs manuales", variable=self.cutoff_enabled_var, text_color=TXT_MAIN).pack(fill="x", padx=6, pady=(0, 4))
        ctk.CTkSwitch(section, text="Activar capping dinámico", variable=self.dynamic_cutoff_enabled_var, text_color=TXT_MAIN, command=self._schedule_cutoff_preview).pack(fill="x", padx=6, pady=(0, 4))
        ctk.CTkEntry(section, textvariable=self.cutoff_limits_var, height=24, placeholder_text="Cutoffs manuales: 0.5, 1.2, 2.0").pack(fill="x", padx=6, pady=(0, 4))
        ctk.CTkButton(section, text="Aplicar cutoffs manuales", height=24, fg_color=BTN_NEUTRAL, hover_color=BTN_NEUTRAL_HOVER, command=self._on_apply_cutoffs).pack(fill="x", padx=6, pady=(0, 5))
        return section

    def _build_spatial_controls(self, parent: ctk.CTkScrollableFrame) -> ctk.CTkFrame:
        section = self._section_shell(parent, "Visualización espacial")
        ctk.CTkLabel(section, text="Opciones locales de la vista espacial", text_color=TXT_MUTED, font=ui_font(FONT_SMALL)).pack(anchor="w", padx=6, pady=(0, 2))
        ctk.CTkLabel(section, text="Vista fija XY / XZ / YZ + metadatos.", text_color=TXT_MUTED, font=ui_font(FONT_SMALL)).pack(anchor="w", padx=6, pady=(0, 5))
        color_options = self._get_spatial_color_options()
        if self.spatial_color_var.get() not in color_options:
            self.spatial_color_var.set(color_options[0] if color_options else "")
        ctk.CTkLabel(section, text="Color por", text_color=TXT_MUTED, font=ui_font(FONT_SMALL)).pack(anchor="w", padx=6, pady=(0, 2))
        ctk.CTkOptionMenu(section, variable=self.spatial_color_var, values=color_options or [""], state="normal" if color_options else "disabled", height=24).pack(fill="x", padx=6, pady=(0, 4))
        ctk.CTkLabel(section, text="(Local) No cambia el target global del workflow.", text_color=TXT_MUTED, font=ui_font(FONT_SMALL)).pack(anchor="w", padx=6, pady=(0, 3))
        domain_filters = ["Todos", *self.service.get_domain_estimation_values()]
        if self.domain_filter_var.get() not in domain_filters:
            self.domain_filter_var.set("Todos")
        ctk.CTkLabel(section, text="Filtro global de dominio", text_color=TXT_MUTED, font=ui_font(FONT_SMALL)).pack(anchor="w", padx=6, pady=(0, 2))
        ctk.CTkOptionMenu(section, variable=self.domain_filter_var, values=domain_filters, state="normal", height=24).pack(fill="x", padx=6, pady=(0, 4))
        ctk.CTkButton(section, text="Aplicar filtro dominio", height=24, fg_color=BTN_NEUTRAL, hover_color=BTN_NEUTRAL_HOVER, command=self._on_apply_domain_filter).pack(fill="x", padx=6, pady=(0, 4))
        return section

    def _build_domains_controls(self, parent: ctk.CTkScrollableFrame) -> ctk.CTkFrame:
        section = self._section_shell(parent, "Constructor explícito de dominios")
        ctk.CTkLabel(section, text="Opciones locales de definición de dominios", text_color=TXT_MUTED, font=ui_font(FONT_SMALL)).pack(anchor="w", padx=6, pady=(0, 2))
        candidates = self.service.get_domain_candidate_columns() or [""]
        if not self.domain_base_var.get() and candidates and candidates[0]:
            self.domain_base_var.set(candidates[0])
        if self.domain_base_var.get() not in candidates:
            self.domain_base_var.set(candidates[0] if candidates else "")
            self.domain_selected_categories = set()
        ctk.CTkLabel(section, text="Variable base", text_color=TXT_MUTED, font=ui_font(FONT_SMALL)).pack(anchor="w", padx=6, pady=(0, 2))
        ctk.CTkOptionMenu(
            section,
            variable=self.domain_base_var,
            values=candidates,
            state="normal" if candidates[0] else "disabled",
            height=24,
            command=lambda _value: self._on_domain_base_changed(),
        ).pack(fill="x", padx=6, pady=(0, 4))
        ctk.CTkLabel(section, text="Selecciona categorías", text_color=TXT_MUTED, font=ui_font(FONT_SMALL)).pack(anchor="w", padx=6, pady=(0, 2))
        categories_box = ctk.CTkScrollableFrame(section, height=140, fg_color=BG_SOFT)
        categories_box.pack(fill="x", padx=6, pady=(0, 4))
        self.domain_category_checkbox_vars = {}
        category_counts = self._get_domain_category_counts()
        if not category_counts:
            ctk.CTkLabel(categories_box, text="No hay categorías disponibles.", text_color=TXT_MUTED, font=ui_font(FONT_SMALL)).pack(anchor="w", padx=4, pady=4)
        for category, count in category_counts:
            var = ctk.BooleanVar(value=category in self.domain_selected_categories)
            self.domain_category_checkbox_vars[category] = var
            ctk.CTkCheckBox(
                categories_box,
                text=f"{category} (n={count})",
                variable=var,
                command=lambda cat=category: self._on_toggle_domain_category(cat),
                text_color=TXT_MAIN,
            ).pack(anchor="w", padx=4, pady=1)
        ctk.CTkLabel(section, text="Nombre dominio", text_color=TXT_MUTED, font=ui_font(FONT_SMALL)).pack(anchor="w", padx=6, pady=(0, 2))
        ctk.CTkEntry(section, textvariable=self.domain_name_var, height=24, placeholder_text="D1").pack(fill="x", padx=6, pady=(0, 4))
        self.domain_assign_button = ctk.CTkButton(section, text="Asignar dominio", height=24, fg_color=BTN_NEUTRAL, hover_color=BTN_NEUTRAL_HOVER, command=self._on_assign_domain)
        self.domain_assign_button.pack(fill="x", padx=6, pady=(0, 4))
        ctk.CTkLabel(section, text="Dominios definidos:", text_color=TXT_MAIN, font=ui_font(FONT_SMALL)).pack(anchor="w", padx=6, pady=(2, 2))
        summary = self._build_domain_definition_summary()
        ctk.CTkLabel(section, text=summary, text_color=TXT_MUTED, justify="left", wraplength=SIDEBAR_WIDTH - 72).pack(anchor="w", padx=6, pady=(0, 4))
        self.domain_apply_button = ctk.CTkButton(section, text="Aplicar dominios", height=26, fg_color=C_ACTIVE, hover_color=BTN_PRIMARY_HOVER, command=self._on_apply_domains)
        self.domain_apply_button.pack(fill="x", padx=6, pady=(2, 4))
        ctk.CTkLabel(section, textvariable=self.domain_feedback_var, text_color=TXT_MUTED, justify="left", wraplength=SIDEBAR_WIDTH - 72).pack(anchor="w", padx=6, pady=(0, 2))
        self._update_domain_action_states()
        return section

    def _focus_sidebar_sections(self, step_name: str) -> None:
        for name, frame in self.control_sections.items():
            frame.configure(fg_color=BG_SOFT if name == step_name else "transparent")

    def _build_kpi_strip(self, parent: ctk.CTkFrame) -> None:
        block = ctk.CTkFrame(parent, fg_color=BG_SOFT, corner_radius=9)
        block.grid(row=1, column=0, sticky="ew", padx=6, pady=(0, 4))
        ctk.CTkLabel(block, text="Resumen rápido (resultados de la vista actual)", text_color=TXT_MUTED, font=ui_font(FONT_SMALL)).pack(anchor="w", padx=7, pady=(4, 0))
        cards = ctk.CTkFrame(block, fg_color="transparent")
        cards.pack(fill="x", padx=5, pady=4)
        labels_by_key = {
            "samples": "Muestras",
            "valid_count": "N válido",
            "mean": "Media",
            "p50": "P50",
            "p90": "P90",
            "std": "Desviación estándar",
            "cv": "Coeficiente de variación (%)",
            "% truncado": "% truncado",
            "cutoff actual": "Cutoff actual",
        }
        keys = list(labels_by_key.keys())
        primary_keys = {"cv"}
        for idx, key in enumerate(keys):
            cards.grid_columnconfigure(idx, weight=1 if key != "cv" else 2)
            card_color = KPI_PRIMARY if key in primary_keys else BG_CARD
            card = ctk.CTkFrame(cards, fg_color=card_color, corner_radius=6)
            card.grid(row=0, column=idx, padx=4, pady=1, sticky="nsew")
            border_width = 1 if key in primary_keys else 0
            card.configure(border_width=border_width, border_color=SEM_BLUE_SOFT if key in primary_keys else BORDER_SOFT)
            ctk.CTkLabel(card, text=labels_by_key[key], font=ui_font(FONT_SMALL), text_color=TXT_MUTED).pack(anchor="w", padx=5, pady=(2, 0))
            val = ctk.StringVar(value="-")
            self.kpi_value_vars[key] = val
            self.kpi_cards[key] = card
            value_font = ui_font(FONT_KPI if key in primary_keys else FONT_BODY)
            ctk.CTkLabel(card, textvariable=val, text_color=TXT_MAIN, font=value_font).pack(anchor="w", padx=5, pady=(0, 2))

    def _build_stage_action_bar(self, parent: ctk.CTkFrame) -> None:
        block = ctk.CTkFrame(parent, fg_color=BG_SOFT, corner_radius=9)
        block.grid(row=2, column=0, sticky="ew", padx=6, pady=(0, 4))
        block.grid_columnconfigure(0, weight=1)
        block.grid_columnconfigure(1, weight=0)
        ctk.CTkLabel(block, text="Acciones de la etapa activa", text_color=TXT_MUTED, font=ui_font(FONT_SMALL)).grid(
            row=0, column=0, sticky="w", padx=7, pady=(5, 2)
        )
        ctk.CTkSwitch(
            block,
            text="Mostrar panel auxiliar",
            variable=self.show_aux_controls_var,
            command=self._toggle_aux_controls,
            text_color=TXT_MUTED,
        ).grid(row=0, column=1, sticky="e", padx=7, pady=(3, 2))
        self.action_bar_body = ctk.CTkFrame(block, fg_color="transparent")
        self.action_bar_body.grid(row=1, column=0, columnspan=2, sticky="ew", padx=6, pady=(0, 5))

    def _toggle_aux_controls(self) -> None:
        if bool(self.show_aux_controls_var.get()):
            self.aux_controls_host.grid()
        else:
            self.aux_controls_host.grid_remove()

    def _render_stage_action_bar(self, stage: str) -> None:
        if self.action_bar_body is None:
            return
        for child in self.action_bar_body.winfo_children():
            child.destroy()
        self.action_bar_body.grid_columnconfigure(0, weight=1)
        readiness = self.service.get_workflow_readiness()
        stage_key = STEP_TO_READINESS_KEY.get(stage, "")
        stage_state = readiness.get("stages", {}).get(stage_key, {}) if isinstance(readiness, dict) else {}
        if not bool(stage_state.get("ready")):
            self._build_blocked_message_card(self.action_bar_body, stage)

        if stage == "Datos":
            self._build_data_actions_inline(self.action_bar_body)
        elif stage == "EDA":
            self._build_eda_actions_inline(self.action_bar_body)
        elif stage == "Cutoffs":
            self._build_cutoff_actions_inline(self.action_bar_body)
        elif stage == "Espacial":
            self._build_spatial_actions_inline(self.action_bar_body)
        else:
            self._build_domains_actions_inline(self.action_bar_body)

    def _build_blocked_message_card(self, parent: ctk.CTkFrame, stage: str) -> None:
        readiness = self.service.get_workflow_readiness()
        message = _build_active_step_hint(stage, readiness)
        card = ctk.CTkFrame(parent, fg_color=WF_BLOCKED, corner_radius=8)
        card.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        ctk.CTkLabel(
            card,
            text=f"Etapa con bloqueo: {message}",
            text_color=SEM_WHITE,
            font=ui_font(FONT_SMALL),
        ).pack(anchor="w", padx=8, pady=5)

    def _build_data_actions_inline(self, parent: ctk.CTkFrame) -> None:
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.grid(row=1, column=0, sticky="ew")
        for col in range(8):
            row.grid_columnconfigure(col, weight=1)
        ctk.CTkButton(row, text="Cargar CSV", height=28, fg_color=BTN_NEUTRAL, hover_color=BTN_NEUTRAL_HOVER, command=self._on_load_csv).grid(row=0, column=0, padx=3, pady=2, sticky="ew")
        self._selector_inline(row, "X", self.x_var, self.service.get_available_columns() or [""], 0, 1)
        self._selector_inline(row, "Y", self.y_var, self.service.get_available_columns() or [""], 0, 2)
        self._selector_inline(row, "Z", self.z_var, self.service.get_available_columns() or [""], 0, 3)
        self._selector_inline(row, "Target", self.target_var, self.service.get_numeric_columns() or [""], 0, 4)
        ctk.CTkCheckBox(row, text="Usar dominio", variable=self.use_domain_var, command=self._on_domain_mode_change).grid(row=0, column=5, padx=3, pady=2, sticky="w")
        domain_options = self.service.get_domain_candidate_columns() or [""]
        self._selector_inline(row, "Dominio", self.domain_var, domain_options, 0, 6, state="normal" if self.use_domain_var.get() else "disabled")
        ctk.CTkButton(row, text="Confirmar", height=28, fg_color=C_ACTIVE, hover_color=BTN_PRIMARY_HOVER, command=self._on_apply_config).grid(row=0, column=7, padx=3, pady=2, sticky="ew")

    def _selector_inline(self, parent: ctk.CTkFrame, label: str, variable: ctk.StringVar, values: list[str], row: int, col: int, *, state: str | None = None) -> None:
        group = ctk.CTkFrame(parent, fg_color="transparent")
        group.grid(row=row, column=col, padx=2, pady=1, sticky="ew")
        ctk.CTkLabel(group, text=label, text_color=TXT_MUTED, font=ui_font(FONT_SMALL)).pack(anchor="w")
        if values and variable.get() not in values:
            variable.set(values[0])
        computed_state = state or ("normal" if values and values[0] else "disabled")
        ctk.CTkOptionMenu(group, variable=variable, values=values or [""], state=computed_state, height=24).pack(fill="x")

    def _build_eda_actions_inline(self, parent: ctk.CTkFrame) -> None:
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.grid(row=1, column=0, sticky="ew")
        row.grid_columnconfigure((0, 1, 2), weight=1)
        has_capping = self.service.has_confirmed_dynamic_capping()
        if not has_capping:
            self.eda_use_capping_var.set(False)
        ctk.CTkSwitch(row, text="EDA con capping confirmado", variable=self.eda_use_capping_var, state="normal" if has_capping else "disabled", command=self._on_toggle_eda_capping).grid(row=0, column=0, sticky="w", padx=4, pady=3)
        ctk.CTkButton(row, text="Actualizar EDA", height=26, fg_color=BTN_NEUTRAL, hover_color=BTN_NEUTRAL_HOVER, command=self._on_refresh_eda).grid(row=0, column=1, padx=4, pady=3, sticky="ew")
        ctk.CTkLabel(row, text="Vista central activa: histogramas, QQ y boxplots.", text_color=TXT_MUTED, font=ui_font(FONT_SMALL)).grid(row=0, column=2, sticky="e", padx=4, pady=3)

    def _build_cutoff_actions_inline(self, parent: ctk.CTkFrame) -> None:
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.grid(row=1, column=0, sticky="ew")
        for col in range(7):
            row.grid_columnconfigure(col, weight=1)
        ctk.CTkOptionMenu(row, variable=self.cutoff_target_var, values=self.service.get_numeric_columns() or [""], state="normal" if self.service.get_numeric_columns() else "disabled", height=24, command=lambda _v: self._schedule_cutoff_preview()).grid(row=0, column=0, padx=3, pady=2, sticky="ew")
        ctk.CTkSwitch(row, text="Cutoff manual", variable=self.cutoff_enabled_var).grid(row=0, column=1, padx=3, pady=2, sticky="w")
        ctk.CTkSwitch(row, text="Capping dinámico", variable=self.dynamic_cutoff_enabled_var, command=self._schedule_cutoff_preview).grid(row=0, column=2, padx=3, pady=2, sticky="w")
        ctk.CTkOptionMenu(row, variable=self.dynamic_mode_var, values=["Percentil", "Valor absoluto"], height=24, command=lambda _v: self._schedule_cutoff_preview()).grid(row=0, column=3, padx=3, pady=2, sticky="ew")
        ctk.CTkSlider(row, from_=0, to=100, variable=self.dynamic_slider_var, command=self._on_slider_change, button_color=SEM_BLUE_SOFT, progress_color=SEM_BLUE_SOFT).grid(row=0, column=4, padx=3, pady=2, sticky="ew")
        ctk.CTkButton(row, text="Aplicar manual", height=26, fg_color=BTN_NEUTRAL, hover_color=BTN_NEUTRAL_HOVER, command=self._on_apply_cutoffs).grid(row=0, column=5, padx=3, pady=2, sticky="ew")
        ctk.CTkButton(row, text="Confirmar capping", height=26, fg_color=C_ACTIVE, hover_color=BTN_PRIMARY_HOVER, command=self._on_apply_dynamic_cutoff).grid(row=0, column=6, padx=3, pady=2, sticky="ew")

    def _build_spatial_actions_inline(self, parent: ctk.CTkFrame) -> None:
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.grid(row=1, column=0, sticky="ew")
        row.grid_columnconfigure((0, 1, 2, 3), weight=1)
        color_options = self._get_spatial_color_options()
        if self.spatial_color_var.get() not in color_options:
            self.spatial_color_var.set(color_options[0] if color_options else "")
        ctk.CTkOptionMenu(row, variable=self.spatial_color_var, values=color_options or [""], state="normal" if color_options else "disabled", height=24).grid(row=0, column=0, padx=3, pady=2, sticky="ew")
        domain_filters = ["Todos", *self.service.get_domain_estimation_values()]
        if self.domain_filter_var.get() not in domain_filters:
            self.domain_filter_var.set("Todos")
        ctk.CTkOptionMenu(row, variable=self.domain_filter_var, values=domain_filters, state="normal", height=24).grid(row=0, column=1, padx=3, pady=2, sticky="ew")
        ctk.CTkButton(row, text="Aplicar filtro dominio", height=26, fg_color=BTN_NEUTRAL, hover_color=BTN_NEUTRAL_HOVER, command=self._on_apply_domain_filter).grid(row=0, column=2, padx=3, pady=2, sticky="ew")
        ctk.CTkLabel(row, text="El color es un override local de esta vista.", text_color=TXT_MUTED, font=ui_font(FONT_SMALL)).grid(row=0, column=3, sticky="e", padx=4, pady=2)

    def _build_domains_actions_inline(self, parent: ctk.CTkFrame) -> None:
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.grid(row=1, column=0, sticky="ew")
        row.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)
        candidates = self.service.get_domain_candidate_columns() or [""]
        if self.domain_base_var.get() not in candidates:
            self.domain_base_var.set(candidates[0] if candidates else "")
        ctk.CTkOptionMenu(row, variable=self.domain_base_var, values=candidates, state="normal" if candidates and candidates[0] else "disabled", height=24, command=lambda _v: self._on_domain_base_changed()).grid(row=0, column=0, padx=3, pady=2, sticky="ew")
        ctk.CTkEntry(row, textvariable=self.domain_name_var, height=24, placeholder_text="Nombre dominio").grid(row=0, column=1, padx=3, pady=2, sticky="ew")
        ctk.CTkButton(row, text="Asignar dominio", height=26, fg_color=BTN_NEUTRAL, hover_color=BTN_NEUTRAL_HOVER, command=self._on_assign_domain).grid(row=0, column=2, padx=3, pady=2, sticky="ew")
        ctk.CTkButton(row, text="Aplicar dominios", height=26, fg_color=C_ACTIVE, hover_color=BTN_PRIMARY_HOVER, command=self._on_apply_domains).grid(row=0, column=3, padx=3, pady=2, sticky="ew")
        ctk.CTkLabel(row, textvariable=self.domain_feedback_var, text_color=TXT_MUTED, font=ui_font(FONT_SMALL)).grid(row=0, column=4, sticky="e", padx=4, pady=2)

    def _apply_kpi_focus(self, step_name: str) -> None:
        focus_by_step = {
            "Datos": {"cv"},
            "EDA": {"cv"},
            "Cutoffs": {"cv"},
            "Espacial": {"cv"},
            "Dominios": {"cv"},
        }
        focus = focus_by_step.get(step_name, set())
        for key, card in self.kpi_cards.items():
            card.configure(fg_color=KPI_PRIMARY_FOCUS if key in focus else BG_CARD)

    def _build_cutoff_decision_controls(self, parent: ctk.CTkFrame) -> None:
        parent.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkLabel(parent, text="Control de capping", text_color=TXT_MAIN, font=ui_font(FONT_SUBTITLE)).grid(row=0, column=0, columnspan=2, sticky="w", padx=8, pady=(7, 3))
        ctk.CTkLabel(
            parent,
            text="Screening exploratorio: no reemplaza decisión minera final.",
            text_color=TXT_MUTED,
            font=ui_font(FONT_SMALL),
        ).grid(row=1, column=0, columnspan=2, sticky="w", padx=8, pady=(0, 3))

        ctk.CTkOptionMenu(parent, variable=self.dynamic_mode_var, values=["Percentil", "Valor absoluto"], height=26, command=lambda _v: self._schedule_cutoff_preview()).grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 3))
        ctk.CTkEntry(parent, textvariable=self.dynamic_output_var, height=26, placeholder_text="salida capped").grid(row=2, column=1, sticky="ew", padx=8, pady=(0, 3))

        ctk.CTkSlider(parent, from_=0, to=100, variable=self.dynamic_slider_var, command=self._on_slider_change, button_color=SEM_BLUE_SOFT, progress_color=SEM_BLUE_SOFT).grid(row=3, column=0, columnspan=2, sticky="ew", padx=8, pady=(0, 3))
        ctk.CTkLabel(parent, textvariable=self.dynamic_percentile_label_var, text_color=TXT_MAIN).grid(row=4, column=0, sticky="w", padx=8)
        ctk.CTkLabel(parent, textvariable=self.dynamic_cutoff_label_var, text_color=TXT_MAIN).grid(row=4, column=1, sticky="e", padx=8)

        ctk.CTkFrame(parent, height=1, fg_color=DIVIDER_SOFT).grid(row=5, column=0, columnspan=2, sticky="ew", padx=8, pady=4)
        ctk.CTkLabel(parent, textvariable=self.dynamic_impact_label_var, text_color=TXT_MAIN, font=ui_font(FONT_SMALL), wraplength=350, justify="left").grid(row=6, column=0, columnspan=2, sticky="w", padx=8)

        ctk.CTkSwitch(parent, text="Capping dinámico", variable=self.dynamic_cutoff_enabled_var, text_color=TXT_MAIN, command=self._schedule_cutoff_preview).grid(row=7, column=0, sticky="w", padx=8, pady=(5, 6))
        ctk.CTkButton(parent, text="Confirmar capping", height=28, fg_color=C_ACTIVE, hover_color=BTN_PRIMARY_HOVER, command=self._on_apply_dynamic_cutoff).grid(row=7, column=1, sticky="ew", padx=8, pady=(5, 6))

    def _show_stage_view(self, stage: str) -> None:
        DashboardGrid.clear(self.view_body)
        self.view_body.grid_columnconfigure(0, weight=1)
        self.view_body.grid_rowconfigure(0, weight=1)
        readiness = self.service.get_workflow_readiness()
        stage_key = STEP_TO_READINESS_KEY.get(stage, "")
        stage_state = readiness.get("stages", {}).get(stage_key, {}) if isinstance(readiness, dict) else {}
        if stage != "Datos" and not bool(stage_state.get("ready")):
            self.workspace_title_var.set(f"{stage} – etapa bloqueada")
            self.workspace_subtitle_var.set("Completa la configuración indicada para habilitar esta vista.")
            self._render_blocked_stage_view(stage)
            return

        if stage == "Datos":
            self.workspace_title_var.set("Preparación de datos – habilitación del flujo")
            self.workspace_subtitle_var.set("Paso 1 de workflow: carga y validación estructural para habilitar todas las vistas.")
            card = ctk.CTkFrame(self.view_body, fg_color=BG_SOFT, corner_radius=8)
            card.grid(row=0, column=0, sticky="nsew")
            card.grid_rowconfigure(2, weight=1)
            card.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(card, text="Inicio de configuración", text_color=TXT_MAIN, font=ui_font(FONT_SUBTITLE)).grid(row=0, column=0, sticky="w", padx=10, pady=(10, 3))
            ctk.CTkLabel(card, text="Progreso: 1) Cargar CSV  ·  2) Asignar columnas  ·  3) Confirmar configuración", text_color=TXT_MUTED, font=ui_font(FONT_BODY)).grid(row=1, column=0, sticky="w", padx=10, pady=(0, 8))
            summary = ctk.CTkFrame(card, fg_color=BG_PANEL, corner_radius=7)
            summary.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 8))
            ctk.CTkLabel(summary, textvariable=self.dataset_label, text_color=TXT_MAIN, font=ui_font(FONT_BODY)).pack(anchor="w", padx=8, pady=(6, 2))
            ctk.CTkLabel(summary, textvariable=self.target_label, text_color=TXT_MAIN, font=ui_font(FONT_BODY)).pack(anchor="w", padx=8, pady=2)
            ctk.CTkLabel(summary, textvariable=self.domain_label, text_color=TXT_MAIN, font=ui_font(FONT_BODY)).pack(anchor="w", padx=8, pady=(2, 6))
            return

        if stage == "EDA":
            self.workspace_title_var.set("Diagnóstico de distribución – MagSus")
            self.workspace_subtitle_var.set("Evalúa sesgo y dispersión para decidir transformación previa al modelado.")
            self._render_eda_view()
            return

        if stage == "Cutoffs":
            self.workspace_title_var.set("Impacto de capping – control de outliers")
            self.workspace_subtitle_var.set("Cuantifica cuánto cambia la distribución antes de confirmar cutoff operativo.")
            self._render_cutoff_view()
            return

        if stage == "Espacial":
            self.workspace_title_var.set("Continuidad espacial – lectura exploratoria")
            self.workspace_subtitle_var.set("Contrasta continuidad visual en XY/XZ/YZ con el target activo.")
            self._render_spatial_view()
            return

        self.workspace_title_var.set("Estabilidad por dominios – media vs variabilidad")
        self.workspace_subtitle_var.set("Prioriza dominios consistentes según CV y media para soporte de decisión.")
        self._render_domains_view()

    def _render_blocked_stage_view(self, stage: str) -> None:
        card = ctk.CTkFrame(self.view_body, fg_color=BG_SOFT, corner_radius=8)
        card.grid(row=0, column=0, sticky="nsew")
        card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(card, text=f"Etapa {stage} bloqueada", text_color=TXT_MAIN, font=ui_font(FONT_SUBTITLE)).grid(row=0, column=0, sticky="w", padx=10, pady=(10, 4))
        hint = _build_active_step_hint(stage, self.service.get_workflow_readiness())
        ctk.CTkLabel(card, text=hint, text_color=SEM_ORANGE, font=ui_font(FONT_BODY), wraplength=1020, justify="left").grid(row=1, column=0, sticky="w", padx=10, pady=(0, 4))
        ctk.CTkLabel(
            card,
            text="Usa la barra de acciones superior para completar la etapa requerida y desbloquear esta vista.",
            text_color=TXT_MUTED,
            font=ui_font(FONT_SMALL),
            wraplength=1020,
            justify="left",
        ).grid(row=2, column=0, sticky="w", padx=10, pady=(0, 10))

    def _render_eda_view(self) -> None:
        wrapper = ctk.CTkFrame(self.view_body, fg_color=BG_PANEL)
        wrapper.grid(row=0, column=0, sticky="nsew")
        state = self.service.get_cutoff_state()
        snapshot = self.service.get_analysis_context_snapshot()
        active_variable = str(state["effective_target_column"] if self.eda_use_capping_var.get() else self.target_var.get() or state["effective_target_column"])
        capping_status = "capping confirmado" if state["dynamic_enabled"] else "sin capping confirmado"
        ctk.CTkLabel(wrapper, text="Resumen ejecutivo", text_color=TXT_MAIN, font=ui_font(FONT_SUBTITLE)).pack(anchor="w", padx=6, pady=(0, 2))
        ctk.CTkLabel(
            wrapper,
            text=f"{_build_visual_context_line(snapshot, local_override=active_variable)} · {capping_status}",
            text_color=TXT_MUTED,
            font=ui_font(FONT_SMALL),
        ).pack(anchor="w", padx=6, pady=(0, 4))
        ctk.CTkLabel(
            wrapper,
            text="Microlectura: no implica independencia espacial; si sesgo y CV son altos, conviene transformar (log/normal score) antes del variograma.",
            text_color=TXT_MUTED,
            font=ui_font(FONT_SMALL),
        ).pack(anchor="w", padx=6, pady=(0, 4))
        try:
            data = self.service.prepare_univariate_data(max_domain_categories=10, use_effective_target=bool(self.eda_use_capping_var.get()))
        except Exception as exc:
            ctk.CTkLabel(wrapper, text=f"Sin EDA disponible: {exc}", text_color=TXT_MAIN).pack(anchor="w", padx=8, pady=8)
            return

        ctk.CTkLabel(wrapper, text="Detalle técnico", text_color=TXT_MAIN, font=ui_font(FONT_SUBTITLE)).pack(anchor="w", padx=6, pady=(0, 2))
        grid = DashboardGrid(wrapper, 2, 2, figsize=self._responsive_figsize(13.4, 6.8))
        ax_hist = grid.axis(0, 0)
        ax_box = grid.axis(0, 1)
        ax_prob = grid.axis(1, 0)
        ax_domain = grid.axis(1, 1)

        for axis in (ax_hist, ax_box, ax_prob, ax_domain):
            apply_axis_style(axis)

        values = [float(v) for v in data["target_values"]]
        sorted_values = sorted(values)
        n_values = len(sorted_values)
        bins = min(55, max(18, int(math.sqrt(n_values) * 2)))
        p50 = sorted_values[int(0.50 * (n_values - 1))]
        p90 = sorted_values[int(0.90 * (n_values - 1))]
        mean_val = sum(sorted_values) / n_values

        original_values: list[float] = values
        cutoff_val: float | None = None
        if self.service.current_dataset is not None and self.service.variable_config is not None:
            base_target = self.service.variable_config.target_column
            if base_target in self.service.current_dataset.dataframe.columns:
                raw_base = self.service.current_dataset.dataframe[base_target].dropna().tolist()
                original_values = [float(v) for v in raw_base if str(v).strip() != ""]
        if state["dynamic_enabled"]:
            cutoff_val = float(state["dynamic_cutoff_value"])

        if original_values != values:
            ax_hist.hist(original_values, bins=bins, color=SEM_GRAY, edgecolor="none", alpha=0.22, label="Base")
        ax_hist.hist(values, bins=bins, color=SEM_BLUE, edgecolor="none", alpha=0.74, label="Activa")
        add_reference_line(ax_hist, mean_val, label="Media", color=SEM_BLUE_SOFT, y_pos=0.97)
        add_reference_line(ax_hist, p50, label="P50", color=SEM_GREEN, y_pos=0.90)
        add_reference_line(ax_hist, p90, label="P90", color=SEM_ORANGE, y_pos=0.83)
        if cutoff_val is not None:
            add_reference_line(ax_hist, cutoff_val, label=f"Cutoff {cutoff_val:.3g}", color=SEM_ORANGE, y_pos=0.76)
        ax_hist.set_title(f"Distribución de {active_variable}", color=PLOT_TXT)
        ax_hist.text(0.01, 1.02, "Base vs activa con referencias clave", transform=ax_hist.transAxes, color=TXT_MUTED, fontsize=CHART_FONT_SIZE_LEGEND)
        ax_hist.set_xlabel("Ley Cu (%)")
        ax_hist.set_ylabel("Frecuencia (n)")
        ax_hist.legend(loc="upper right", fontsize=CHART_FONT_SIZE_LEGEND, frameon=False)

        box = ax_box.boxplot(values, vert=False, patch_artist=True, widths=0.52, showfliers=True)
        for patch in box["boxes"]:
            patch.set_facecolor(KPI_PRIMARY)
            patch.set_alpha(0.64)
            patch.set_edgecolor(SEM_BLUE_SOFT)
        for whisker in box["whiskers"]:
            whisker.set_color(BORDER_SOFT)
            whisker.set_alpha(0.9)
        for cap in box["caps"]:
            cap.set_color(BORDER_SOFT)
            cap.set_alpha(0.9)
        for median in box["medians"]:
            median.set_color(SEM_GREEN)
            median.set_linewidth(1.8)
        for flier in box["fliers"]:
            flier.set_alpha(0.30)
            flier.set_markerfacecolor(SEM_GRAY)
            flier.set_markeredgecolor(SEM_GRAY)
        jitter_y = [1 + ((idx % 9) - 4) * 0.012 for idx in range(n_values)]
        ax_box.scatter(values, jitter_y, s=6, color=SEM_BLUE_SOFT, alpha=0.20, edgecolors="none")
        ax_box.axvline(p50, color=SEM_GREEN, linestyle="-", linewidth=1.1, alpha=0.9)
        ax_box.axvline(p90, color=SEM_ORANGE, linestyle="--", linewidth=1.1, alpha=0.9)
        ax_box.set_yticks([])
        ax_box.set_title(f"Rango y outliers de {active_variable}", color=PLOT_TXT)
        ax_box.set_xlabel("Ley Cu (%)")

        if data.get("probplot_x") and data.get("probplot_y") and not data.get("probability_failed"):
            prob_x = [float(v) for v in data["probplot_x"]]
            prob_y = [float(v) for v in data["probplot_y"]]
            qmin, qmax = min(prob_x), max(prob_x)
            ymin, ymax = min(prob_y), max(prob_y)
            slope = (ymax - ymin) / (qmax - qmin) if qmax != qmin else 1.0
            intercept = ymin - slope * qmin
            ref_line = [slope * q + intercept for q in prob_x]
            high_cut = sorted(prob_y)[int(0.90 * (len(prob_y) - 1))]
            core_x = [x for x, y in zip(prob_x, prob_y) if y <= high_cut]
            core_y = [y for y in prob_y if y <= high_cut]
            tail_x = [x for x, y in zip(prob_x, prob_y) if y > high_cut]
            tail_y = [y for y in prob_y if y > high_cut]
            ax_prob.scatter(core_x, core_y, s=12, color=SEM_BLUE, alpha=0.75, label="Cuerpo")
            if tail_x:
                ax_prob.scatter(tail_x, tail_y, s=16, color=SEM_ORANGE, alpha=0.85, label="Cola")
                ax_prob.annotate("Desvío de cola", xy=(tail_x[-1], tail_y[-1]), xytext=(8, 8), textcoords="offset points", color=SEM_ORANGE, fontsize=CHART_FONT_SIZE_LEGEND)
            ax_prob.plot(prob_x, ref_line, color=SEM_GRAY, linestyle="--", linewidth=1.0, label="Ref")
            ax_prob.set_title(f"QQ Plot de {active_variable}", color=PLOT_TXT)
            ax_prob.set_xlabel("Cuantiles normales")
            ax_prob.set_ylabel("Ley Cu (%)")
            ax_prob.legend(loc="upper left", fontsize=CHART_FONT_SIZE_LEGEND, frameon=False)
        else:
            ax_prob.axis("off")
            ax_prob.text(0.5, 0.5, "No disponible", ha="center", va="center", color=PLOT_TXT)

        domain_data = data.get("domain_boxplot", {})
        if domain_data.get("enabled"):
            paired = list(zip(domain_data["labels"], domain_data["values"]))
            paired.sort(key=lambda item: (sum(item[1]) / len(item[1])) if item[1] else float("-inf"), reverse=True)
            ordered_labels = [f"{label} (n={len(vals)})" for label, vals in paired]
            ordered_values = [vals for _label, vals in paired]
            box = ax_domain.boxplot(ordered_values, labels=ordered_labels, patch_artist=True)
            for patch, (label, _vals) in zip(box["boxes"], paired):
                patch.set_facecolor(get_domain_color(label))
                patch.set_alpha(0.72)
                patch.set_edgecolor(BORDER_SOFT)
            ax_domain.tick_params(axis="x", rotation=22)
            ax_domain.set_ylabel("Ley Cu (%)")
            ax_domain.set_title(f"Comparativo por dominio ({active_variable})", color=PLOT_TXT)
        else:
            ax_domain.axis("off")
            ax_domain.text(0.5, 0.5, domain_data.get("message", "No disponible"), ha="center", va="center", color=PLOT_TXT, wrap=True)

        stats_table = dict(self.service.get_target_statistics_table(use_effective_target=bool(self.eda_use_capping_var.get())))
        try:
            cv_ratio = float(stats_table.get("cv", "nan"))
            skewness = float(stats_table.get("skewness", "nan"))
            diagnostic = "Distribución aproximadamente simétrica."
            if cv_ratio >= 0.75 or abs(skewness) >= 1.0:
                diagnostic = f"Distribución sesgada/variable (CV={cv_ratio*100:.1f}%, skew={skewness:.2f}). Recomendada transformación (log o normal score) antes de kriging."
            ctk.CTkLabel(wrapper, text=diagnostic, text_color=TXT_MUTED, font=ui_font(FONT_SMALL), wraplength=900, justify="left").pack(anchor="w", padx=6, pady=(2, 0))
        except Exception:
            pass
        grid.render()

    def _render_cutoff_view(self) -> None:
        wrapper = ctk.CTkFrame(self.view_body, fg_color=BG_PANEL)
        wrapper.grid(row=0, column=0, sticky="nsew")
        snapshot = self.service.get_analysis_context_snapshot()
        ctk.CTkLabel(wrapper, text="Resumen ejecutivo", text_color=TXT_MAIN, font=ui_font(FONT_SUBTITLE)).pack(anchor="w", padx=6, pady=(0, 2))
        ctk.CTkLabel(wrapper, text=f"{_build_visual_context_line(snapshot)} · Ajustes de capping locales en esta vista.", text_color=TXT_MUTED, font=ui_font(FONT_SMALL)).pack(anchor="w", padx=6, pady=(0, 4))
        ctk.CTkLabel(wrapper, text="Microlectura: identifica cuánto porcentaje de muestras y máximos cambia por cutoff.", text_color=TXT_MUTED, font=ui_font(FONT_SMALL)).pack(anchor="w", padx=6, pady=(0, 4))
        ctk.CTkLabel(wrapper, text="Detalle técnico", text_color=TXT_MAIN, font=ui_font(FONT_SUBTITLE)).pack(anchor="w", padx=6, pady=(0, 2))

        container = ctk.CTkFrame(wrapper, fg_color=BG_PANEL)
        container.pack(fill="both", expand=True)
        container.grid_columnconfigure(0, weight=0, minsize=360)
        container.grid_columnconfigure(1, weight=1)
        container.grid_rowconfigure((0, 1), weight=1)

        control_card = ctk.CTkFrame(container, fg_color=BG_SOFT, corner_radius=8)
        control_card.grid(row=0, column=0, sticky="nsew", padx=(0, 4), pady=(0, 4))
        self._build_cutoff_decision_controls(control_card)

        plot_card = ctk.CTkFrame(container, fg_color=BG_SOFT, corner_radius=8)
        plot_card.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=(4, 0), pady=(0, 0))
        self.plot_frame = plot_card
        self._last_cutoff_preview_signature = None
        self._refresh_cutoff_preview()

    def _render_spatial_view(self) -> None:
        wrapper = ctk.CTkFrame(self.view_body, fg_color=BG_PANEL)
        wrapper.grid(row=0, column=0, sticky="nsew")
        snapshot = self.service.get_analysis_context_snapshot()
        ctk.CTkLabel(wrapper, text="Resumen ejecutivo", text_color=TXT_MAIN, font=ui_font(FONT_SUBTITLE)).pack(anchor="w", padx=6, pady=(0, 2))
        ctk.CTkLabel(wrapper, text=f"{_build_visual_context_line(snapshot, local_override=self.spatial_color_var.get() or None)}", text_color=TXT_MUTED, font=ui_font(FONT_SMALL)).pack(anchor="w", padx=6, pady=(0, 4))
        ctk.CTkLabel(wrapper, text="Microlectura: continuidad visual estable sugiere dominios y variogramas más robustos.", text_color=TXT_MUTED, font=ui_font(FONT_SMALL)).pack(anchor="w", padx=6, pady=(0, 2))
        ctk.CTkLabel(wrapper, text="Detalle técnico", text_color=TXT_MAIN, font=ui_font(FONT_SUBTITLE)).pack(anchor="w", padx=6, pady=(0, 2))
        try:
            color_by = self.spatial_color_var.get() or None
            result = self.service.prepare_visual_data(color_by=color_by)
            if not result.success or result.spatial_data is None:
                raise ValueError(result.message)
            spatial = result.spatial_data
        except Exception as exc:
            ctk.CTkLabel(wrapper, text=f"No se pudo renderizar Espacial: {exc}", text_color=TXT_MAIN).pack(anchor="w", padx=8, pady=8)
            return

        grid = DashboardGrid(
            wrapper,
            2,
            2,
            figsize=self._responsive_figsize(14.2, 7.4),
            width_ratios=[1.45, 1.0],
            height_ratios=[1.2, 1.0],
        )
        ax_xy = grid.axis(0, 0)
        ax_xz = grid.axis(0, 1)
        ax_yz = grid.axis(1, 0)
        ax_info = grid.axis(1, 1)

        for axis in (ax_xy, ax_xz, ax_yz, ax_info):
            apply_axis_style(axis)
        cmap = "tab20" if spatial.target_tick_labels else get_continuous_colormap()
        point_kwargs = {"s": 11, "alpha": 0.64, "edgecolors": "none"}
        sc_xy = ax_xy.scatter(spatial.x, spatial.y, c=spatial.target, cmap=cmap, **point_kwargs)
        sc_xz = ax_xz.scatter(spatial.x, spatial.z, c=spatial.target, cmap=cmap, **point_kwargs)
        sc_yz = ax_yz.scatter(spatial.y, spatial.z, c=spatial.target, cmap=cmap, **point_kwargs)

        ax_xy.set_title("Planta XY (principal)", color=PLOT_TXT)
        ax_xz.set_title("Sección XZ", color=PLOT_TXT)
        ax_yz.set_title("Sección YZ", color=PLOT_TXT)
        ax_xy.set_xlabel("X")
        ax_xy.set_ylabel("Y")
        ax_xz.set_xlabel("X")
        ax_xz.set_ylabel("Z")
        ax_yz.set_xlabel("Y")
        ax_yz.set_ylabel("Z")
        plain_formatter = ScalarFormatter(useOffset=False)
        plain_formatter.set_scientific(False)
        for axis in [ax_xy.xaxis, ax_xy.yaxis, ax_xz.xaxis, ax_xz.yaxis, ax_yz.xaxis, ax_yz.yaxis]:
            axis.set_major_formatter(plain_formatter)

        for sc, ax in [(sc_xy, ax_xy)]:
            colorbar = grid.figure.colorbar(sc, ax=ax, shrink=0.68, pad=0.02, label=spatial.target_label)
            if spatial.target_tick_positions and spatial.target_tick_labels:
                colorbar.set_ticks(spatial.target_tick_positions)
                colorbar.set_ticklabels(spatial.target_tick_labels)
            colorbar.ax.tick_params(labelsize=CHART_FONT_SIZE_TICK, colors=TXT_MUTED)
            colorbar.ax.yaxis.label.set_color(TXT_MUTED)
            colorbar.outline.set_edgecolor(BORDER_SOFT)

        ax_info.axis("off")
        msg = "Ficha espacial\n• Vistas: XY / XZ / YZ"
        msg += f"\n• Target resuelto global: {snapshot['resolved_target_column'] or 'No definido'}"
        msg += f"\n• Color mostrado (local): {color_by or snapshot['resolved_target_column'] or 'No definido'}"
        msg += "\n• Uso: lectura exploratoria, no inferencia de continuidad."
        state = self.service.get_cutoff_state()
        if state["dynamic_enabled"]:
            msg += f"\n• Capping confirmado: {state['dynamic_cutoff_value']:.6g}"
        if spatial.downsampled:
            msg += f"\n• Muestreo mostrado: {spatial.plotted_points:,}/{spatial.source_points:,}"
        msg += "\n• Preparado para lectura por ley o por dominio."
        ax_info.text(0.05, 0.95, msg, va="top", color=TXT_MAIN, fontsize=CHART_FONT_SIZE_LABEL, bbox={"facecolor": BG_CARD, "edgecolor": BORDER_SOFT, "boxstyle": "round,pad=0.45"})
        grid.render()

    def _render_domains_view(self) -> None:
        wrapper = ctk.CTkFrame(self.view_body, fg_color=BG_PANEL)
        wrapper.grid(row=0, column=0, sticky="nsew")
        wrapper.grid_rowconfigure(0, weight=0)
        wrapper.grid_rowconfigure(1, weight=1)
        wrapper.grid_rowconfigure(2, weight=0)
        wrapper.grid_columnconfigure(0, weight=1)
        snapshot = self.service.get_analysis_context_snapshot()
        ctk.CTkLabel(wrapper, text="Resumen ejecutivo", text_color=TXT_MAIN, font=ui_font(FONT_SUBTITLE)).grid(row=0, column=0, sticky="w", padx=6, pady=(0, 2))
        ctk.CTkLabel(wrapper, text=_build_visual_context_line(snapshot), text_color=TXT_MUTED, font=ui_font(FONT_SMALL)).grid(row=0, column=0, sticky="w", padx=6, pady=(18, 2))
        ctk.CTkLabel(wrapper, text="Microlectura: dominios con CV menor y media consistente son más estables para estimación.", text_color=TXT_MUTED, font=ui_font(FONT_SMALL)).grid(row=0, column=0, sticky="w", padx=6, pady=(34, 2))
        try:
            payload = self.service.prepare_domain_statistics()
        except Exception as exc:
            ctk.CTkLabel(wrapper, text=f"No se pudo renderizar Dominios: {exc}", text_color=TXT_MAIN).pack(anchor="w", padx=8, pady=8)
            return

        rows = payload.get("items", [])
        if not rows:
            ctk.CTkLabel(wrapper, text="Define al menos un dominio para comenzar", text_color=TXT_MAIN).pack(anchor="w", padx=8, pady=8)
            return

        ctk.CTkLabel(wrapper, text="Detalle técnico", text_color=TXT_MAIN, font=ui_font(FONT_SUBTITLE)).grid(row=0, column=0, sticky="e", padx=6, pady=(0, 2))
        plot_card = ctk.CTkFrame(wrapper, fg_color=BG_SOFT, corner_radius=8)
        plot_card.grid(row=1, column=0, sticky="nsew", padx=4, pady=(0, 4))
        records_card = ctk.CTkFrame(wrapper, fg_color=BG_SOFT, corner_radius=8)
        records_card.grid(row=2, column=0, sticky="ew", padx=4, pady=(0, 0))
        ctk.CTkLabel(records_card, text="Detalle del dominio seleccionado", text_color=TXT_MAIN, font=ui_font(FONT_SUBTITLE)).pack(anchor="w", padx=8, pady=(6, 2))
        ctk.CTkLabel(records_card, textvariable=self.domain_records_var, text_color=TXT_MUTED, justify="left", wraplength=980, font=ui_font(FONT_SMALL)).pack(anchor="w", padx=8, pady=(0, 6))

        chart = DashboardGrid(plot_card, 1, 1, figsize=self._responsive_figsize(14.0, 7.6))
        ax = chart.axis(0, 0)
        apply_axis_style(ax)
        x_values = [float(row["mean"]) for row in rows]
        y_values = [float(row["cv"]) for row in rows]
        names = [str(row["domain"]) for row in rows]
        counts = [int(row["count"]) for row in rows]
        min_n = min(counts)
        max_n = max(counts)
        size_min = 70.0
        size_max = 550.0
        if max_n == min_n:
            sizes = [220.0 for _ in counts]
        else:
            sizes = [size_min + ((size_max - size_min) * ((value**0.5 - min_n**0.5) / ((max_n**0.5 - min_n**0.5) or 1.0))) for value in counts]

        groups = [str(row.get("primary_group", "Otros")) for row in rows]
        unique_groups = sorted(set(groups))
        color_map = {group: get_domain_color(group) for group in unique_groups}
        colors = [color_map[group] for group in groups]

        points = ax.scatter(x_values, y_values, s=sizes, c=colors, alpha=0.78, edgecolors=BORDER_SOFT, linewidths=0.6, picker=True)
        ax.set_title("Comparación exploratoria de dominios", color=PLOT_TXT)
        ax.text(0.01, 1.02, "Coherencia estadística de dominios", transform=ax.transAxes, color=TXT_MUTED, fontsize=CHART_FONT_SIZE_LEGEND)
        ax.set_xlabel("Media de ley Cu (%)")
        ax.set_ylabel("Coeficiente de variación")
        ax.tick_params(labelsize=CHART_FONT_SIZE_TICK)
        chart.figure.subplots_adjust(right=0.78, top=0.90, left=0.08, bottom=0.11)
        global_mean = sum(x_values) / len(x_values)
        global_cv = sum(y_values) / len(y_values)
        ax.axvline(global_mean, color=SEM_GRAY, linestyle="--", linewidth=1.0, alpha=0.75)
        ax.axhline(0.5, color=SEM_RED, linestyle=":", linewidth=1.0, alpha=0.8)
        ax.axhline(global_cv, color=SEM_BLUE_SOFT, linestyle="--", linewidth=1.0, alpha=0.75)
        ax.text(global_mean, 0.98, " media global", transform=ax.get_xaxis_transform(), color=SEM_GRAY, fontsize=CHART_FONT_SIZE_LEGEND, va="top")
        ax.text(0.01, 0.5, "umbral CV 0.50", transform=ax.transAxes, color=SEM_RED, fontsize=CHART_FONT_SIZE_LEGEND)

        from matplotlib.lines import Line2D
        legend_handles = [Line2D([0], [0], marker="o", color="w", label=group, markerfacecolor=color_map[group], markeredgecolor=BORDER_SOFT, markersize=8) for group in unique_groups]
        ax.legend(handles=legend_handles, title="Grupo dominio", loc="center left", bbox_to_anchor=(1.01, 0.5), frameon=False, fontsize=CHART_FONT_SIZE_LEGEND, title_fontsize=CHART_FONT_SIZE_LEGEND)
        for idx, (xv, yv, label) in enumerate(zip(x_values, y_values, names)):
            dx = 0.012 * (max(x_values) - min(x_values) + 1e-6)
            dy = 0.012 * (max(y_values) - min(y_values) + 1e-6) * (1 if idx % 2 == 0 else -1)
            ax.text(
                xv + dx,
                yv + dy,
                label,
                fontsize=CHART_FONT_SIZE_LEGEND,
                color=SEM_WHITE,
                alpha=0.82,
                bbox={"facecolor": BG_PANEL, "edgecolor": BORDER_SOFT, "alpha": 0.85, "boxstyle": "round,pad=0.18"},
            )

        tooltip = ax.annotate("", xy=(0, 0), xytext=(10, 10), textcoords="offset points", bbox={"boxstyle": "round", "fc": BG_CARD, "ec": BORDER_SOFT}, color=TXT_MAIN, fontsize=CHART_FONT_SIZE_LEGEND)
        tooltip.set_visible(False)

        def on_move(event) -> None:
            if event.inaxes != ax:
                tooltip.set_visible(False)
                chart.canvas.draw_idle()
                return
            contains, details = points.contains(event)
            if not contains:
                tooltip.set_visible(False)
                chart.canvas.draw_idle()
                return
            point_index = int(details["ind"][0])
            row = rows[point_index]
            tooltip.xy = (x_values[point_index], y_values[point_index])
            tooltip.set_text(
                f"{row['domain']}\nN={row['count']} · mean={row['mean']:.4g}\nstd={row['std']:.4g} · CV={row['cv']:.4g}\n% total={row['pct_total']:.2f}"
            )
            tooltip.set_visible(True)
            chart.canvas.draw_idle()

        def on_pick(event) -> None:
            if not hasattr(event, "ind") or not event.ind:
                return
            idx = int(event.ind[0])
            row = rows[idx]
            preview_indexes = ", ".join(str(value) for value in row["indexes"][:24])
            self.domain_records_var.set(
                f"Dominio: {row['domain']} | N={row['count']} | Media={row['mean']:.4g} | CV={row['cv']:.4g} | Índices: {preview_indexes}"
            )

        chart.canvas.mpl_connect("motion_notify_event", on_move)
        chart.canvas.mpl_connect("pick_event", on_pick)
        chart.render()

    def _on_change_step(self, step_name: str) -> None:
        current_step = self.service.workflow_state.current_step
        if current_step == step_name:
            self._trace_ui_action("cambiar_vista", refresh_type="none", extra={"requested_step": step_name, "reason": "same_step_ignored"})
            return
        self.status_text.set(self.service.set_workflow_step(step_name))
        self.step_label.set(f"Paso actual: {step_name}")
        self._append_activity(self.status_text.get())
        self._trace_ui_action("cambiar_vista", refresh_type="dashboard_full", extra={"requested_step": step_name})
        self._render_step(step_name)

    def _render_step(self, step_name: str) -> None:
        self._paint_workflow_state(step_name)
        self._focus_sidebar_sections(step_name)
        self._render_stage_action_bar(step_name)
        self._refresh_dashboard(reason="step_render")

    def _paint_workflow_state(self, active_step: str) -> None:
        ordered = ["Datos", "EDA", "Cutoffs", "Espacial", "Dominios"]
        readiness = self.service.get_workflow_readiness()
        active_idx = ordered.index(active_step) if active_step in ordered else 0
        for idx, step in enumerate(ordered):
            button_text = _build_workflow_stage_label(step, active_step, readiness)
            stage_key = STEP_TO_READINESS_KEY.get(step, "")
            stage_state = readiness.get("stages", {}).get(stage_key, {}) if isinstance(readiness, dict) else {}
            is_ready = bool(stage_state.get("ready"))
            has_warning = bool(stage_state.get("warnings"))
            if idx == active_idx:
                fg_color = WF_WARNING if has_warning else WF_ACTIVE
                border_color = SEM_ORANGE if has_warning else SEM_BLUE_SOFT
                hover_color = BTN_PRIMARY_HOVER
            elif idx < active_idx:
                fg_color = WF_WARNING if has_warning else WF_READY
                border_color = SEM_ORANGE if has_warning else BORDER_SOFT
                hover_color = BTN_NEUTRAL_HOVER
            else:
                fg_color = WF_BLOCKED if not is_ready else WF_IDLE
                border_color = SEM_RED if not is_ready else BORDER_SOFT
                hover_color = BTN_NEUTRAL_HOVER
            self.workflow_buttons[step].configure(
                text=button_text,
                fg_color=fg_color,
                hover_color=hover_color,
                border_color=border_color,
            )
        self.workflow_hint_var.set(_build_active_step_hint(active_step, readiness))

    def _refresh_dashboard(self, *, reason: str = "general", force: bool = False) -> None:
        self._trace_ui_action("refresh_dashboard", refresh_type="dashboard_full", extra={"reason": reason, "force": force})
        self._refresh_context_chips()
        self._sync_eda_capping_state()
        self._refresh_summary_cards()
        current_step = self.service.workflow_state.current_step
        self._apply_kpi_focus(current_step)
        self._render_stage_action_bar(current_step)
        self._show_stage_view(current_step)

    def _sync_eda_capping_state(self) -> None:
        has_capping = self.service.has_confirmed_dynamic_capping()
        if self.eda_capping_switch is not None:
            self.eda_capping_switch.configure(state="normal" if has_capping else "disabled")
        if not has_capping:
            self.eda_use_capping_var.set(False)

    def _format_kpi_value(self, value: str, *, as_percent: bool = False) -> str:
        try:
            numeric = float(str(value).replace("%", ""))
        except Exception:
            return value
        if as_percent:
            return f"{numeric:,.2f}%"
        return f"{numeric:,.2f}"

    def _refresh_context_chips(self) -> None:
        snapshot = self.service.get_analysis_context_snapshot()
        readiness = self.service.get_workflow_readiness()
        state = self.service.get_cutoff_state()
        dataset_name = self.service.current_dataset.file_name if self.service.current_dataset is not None else "No cargado"
        texts = _build_context_chip_texts(snapshot, readiness, dataset_name)
        self.context_chip_vars["dataset"].set(texts["dataset"])
        self.context_chip_vars["target"].set(texts["target"])
        self.context_chip_vars["domain"].set(texts["domain"])
        self.context_chip_vars["status"].set(texts["status"])
        if state["dynamic_enabled"]:
            self.context_chip_vars["capping"].set(f"Capping activo P{state['dynamic_percent']:.0f}")
        elif state["enabled"]:
            self.context_chip_vars["capping"].set("Cutoff manual activo")
        else:
            self.context_chip_vars["capping"].set("Capping inactivo")

    def _selector(self, parent: ctk.CTkFrame, label: str, variable: ctk.StringVar, values: list[str], row: int, col: int, key: str | None = None) -> None:
        ctk.CTkLabel(parent, text=label, text_color=TXT_MUTED, font=ui_font(FONT_SMALL)).grid(row=row, column=col, sticky="w", padx=4)
        state = "normal" if values and values[0] else "disabled"
        if values and variable.get() not in values:
            variable.set(values[0])
        menu = ctk.CTkOptionMenu(parent, variable=variable, values=values, state=state, height=24)
        menu.grid(row=row + 1, column=col, sticky="ew", padx=4, pady=(0, 4))
        if key:
            self.column_menus[key] = menu

    def _responsive_figsize(self, base_width: float, base_height: float) -> tuple[float, float]:
        self.update_idletasks()
        content_width = max(self.content_panel.winfo_width(), self.view_body.winfo_width(), 1280)
        scale = min(1.65, max(1.0, content_width / 1500.0))
        return (base_width * scale, base_height * scale)

    def _get_spatial_color_options(self) -> list[str]:
        target = self.service.get_cutoff_state().get("effective_target_column", "") or self.target_var.get()
        categorical = self.service.get_categorical_columns()
        options = [value for value in [target, "domain_estimation", *categorical] if value]
        unique: list[str] = []
        for option in options:
            if option not in unique:
                unique.append(option)
        return unique

    def _get_domain_category_counts(self) -> list[tuple[str, int]]:
        dataset = self.service.current_dataset
        base = self.domain_base_var.get().strip()
        if dataset is None or not base or base not in dataset.dataframe.columns:
            return []
        counts = dataset.dataframe[base].dropna().astype(str).str.strip().value_counts()
        return [(str(cat), int(count)) for cat, count in counts.items() if str(cat)]

    def _domain_inputs_valid(self) -> bool:
        return bool(self.domain_base_var.get().strip() and self.domain_name_var.get().strip() and self.domain_selected_categories)

    def _update_domain_action_states(self) -> None:
        assign_state = "normal" if self._domain_inputs_valid() else "disabled"
        apply_state = "normal" if self.domain_definition_local else "disabled"
        if self.domain_assign_button is not None:
            self.domain_assign_button.configure(state=assign_state)
        if self.domain_apply_button is not None:
            self.domain_apply_button.configure(state=apply_state)

    def _on_domain_name_changed(self, *_args) -> None:
        self._update_domain_action_states()

    def _on_domain_mode_change(self) -> None:
        if self.domain_menu_widget is not None:
            self.domain_menu_widget.configure(state="normal" if bool(self.use_domain_var.get()) else "disabled")
        if not self.use_domain_var.get():
            self.domain_var.set("")
        self._render_stage_action_bar(self.service.workflow_state.current_step)

    def _on_load_csv(self) -> None:
        self._trace_ui_action("cargar_csv", refresh_type="none")
        path = filedialog.askopenfilename(title="Seleccionar CSV", filetypes=[("CSV", "*.csv"), ("All", "*.*")])
        if not path:
            self.service.activity_log.log("csv_load_cancelled", "info", "Carga cancelada.", {})
            return
        result = self.service.load_csv(path)
        self.status_text.set(result.message)
        self._append_activity(result.message)
        if result.success and result.dataset:
            self.dataset_label.set(f"Dataset: {result.dataset.file_name}")
            self.domain_definition_local = {}
            self.domain_selected_categories = set()
            self.domain_feedback_var.set("Selecciona categorías y asigna un nombre de dominio.")
            self._apply_autodetected_columns()
            self._sync_cutoff_defaults()
            self._render_control_sections()
            self._sync_column_selectors()
            self._refresh_dashboard(reason="csv_loaded")

    def _apply_autodetected_columns(self) -> None:
        suggestions = self.service.get_autodetected_columns()
        self.x_var.set(suggestions.get("x", ""))
        self.y_var.set(suggestions.get("y", ""))
        self.z_var.set(suggestions.get("z", ""))
        self.target_var.set(suggestions.get("target", ""))
        self.hole_var.set(suggestions.get("hole_id", ""))
        self.domain_var.set(suggestions.get("domain", ""))
        self.use_domain_var.set(False)
        self._on_domain_mode_change()
        self._sync_column_selectors()

    def _sync_column_selectors(self) -> None:
        cols = self.service.get_available_columns() or [""]
        numeric_cols = self.service.get_numeric_columns() or [""]
        mapping = {
            "x": (self.x_var, cols),
            "y": (self.y_var, cols),
            "z": (self.z_var, cols),
            "hole": (self.hole_var, cols),
            "target": (self.target_var, numeric_cols),
        }
        for key, (var, values) in mapping.items():
            if var.get() not in values:
                var.set(values[0] if values else "")
            menu = self.column_menus.get(key)
            if menu is not None:
                menu.configure(values=values, state="normal" if values and values[0] else "disabled")

    def _on_apply_config(self) -> None:
        self._trace_ui_action("aplicar_configuracion", refresh_type="none")
        selected_domain = self.domain_var.get() if bool(self.use_domain_var.get()) and self.domain_var.get() else None
        result = self.service.set_variable_config(
            self.x_var.get(), self.y_var.get(), self.z_var.get(), self.target_var.get(), self.hole_var.get() or None, selected_domain
        )
        self.status_text.set(result.message)
        self._append_activity(result.message)
        if result.success:
            self.target_label.set(f"Target: {self.target_var.get()}")
            self.domain_label.set(f"Dominio: {selected_domain or 'No definido'}")
            self.spatial_color_var.set(self.target_var.get())
            self._sync_cutoff_defaults()
            self._refresh_dashboard(reason="config_applied")

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
        self.spatial_color_var.set(self.target_var.get())

    def _on_apply_cutoffs(self) -> None:
        self._trace_ui_action("aplicar_cutoffs_manuales", refresh_type="none")
        result = self.service.apply_cutoffs(
            enabled=bool(self.cutoff_enabled_var.get()),
            target_column=self.cutoff_target_var.get(),
            limits_text=self.cutoff_limits_var.get(),
            output_column=self.cutoff_output_var.get() or None,
        )
        self.status_text.set(result.message)
        self._append_activity(result.message)
        if result.success:
            self._refresh_dashboard(reason="manual_cutoffs_applied")

    def _schedule_cutoff_preview(self) -> None:
        if self._cutoff_preview_after_id is not None:
            self.after_cancel(self._cutoff_preview_after_id)
        self._cutoff_preview_after_id = self.after(80, self._refresh_cutoff_preview)

    def _on_slider_change(self, _value: float) -> None:
        self.dynamic_percentile_label_var.set(f"Percentil: P{float(self.dynamic_slider_var.get()):.1f}")
        self._schedule_cutoff_preview()

    def _refresh_cutoff_preview(self) -> None:
        self._cutoff_preview_after_id = None
        if self.service.workflow_state.current_step != "Cutoffs" or self.plot_frame is None:
            return
        preview_signature = (
            self.cutoff_target_var.get(),
            self.target_var.get(),
            self.dynamic_mode_var.get(),
            float(self.dynamic_slider_var.get()),
            bool(self.dynamic_cutoff_enabled_var.get()),
        )
        if preview_signature == self._last_cutoff_preview_signature:
            self._trace_ui_action("refresh_vista_puntual", refresh_type="cutoff_preview_skipped", extra={"reason": "no_state_change"})
            return
        self._last_cutoff_preview_signature = preview_signature
        self._trace_ui_action("refresh_vista_puntual", refresh_type="cutoff_preview")
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

        chart = DashboardGrid(parent, 2, 2, figsize=self._responsive_figsize(9.2, 6.8))
        ax_hist = chart.axis(0, 0)
        ax_cdf = chart.axis(1, 0)
        ax_before_after = chart.axis(1, 1)
        ax_prob = chart.axis(0, 1)
        for axis in (ax_hist, ax_cdf, ax_before_after, ax_prob):
            apply_axis_style(axis)

        ax_hist.hist(preview["retained_values"], bins="sturges", color=SEM_GRAY, alpha=0.24, label="Base")
        if preview["truncated_values"]:
            ax_hist.hist(preview["truncated_values"], bins="sturges", color=SEM_BLUE, alpha=0.78, label="Cap")
        add_reference_line(ax_hist, cutoff, label=f"Cutoff {cutoff:.3g}", color=SEM_ORANGE, y_pos=0.92)
        ax_hist.set_title("Distribución original vs operativa", color=PLOT_TXT)
        ax_hist.set_xlabel("Ley Cu (%)")
        ax_hist.set_ylabel("Frecuencia (n)")
        ax_hist.legend(fontsize=CHART_FONT_SIZE_LEGEND, frameon=False)

        retained_x, retained_y, trunc_x, trunc_y = [], [], [], []
        for x_val, y_val in zip(preview["sorted_values"], preview["theoretical_quantiles"]):
            if x_val <= cutoff:
                retained_x.append(x_val)
                retained_y.append(y_val)
            else:
                trunc_x.append(x_val)
                trunc_y.append(y_val)
        ax_prob.scatter(retained_x, retained_y, s=9, color=SEM_BLUE, alpha=0.70)
        if trunc_x:
            ax_prob.scatter(trunc_x, trunc_y, s=10, color=SEM_ORANGE, alpha=0.9)
        ax_prob.axvline(cutoff, color=SEM_ORANGE, linestyle="--", linewidth=1.2)
        ax_prob.set_title("QQ diagnóstico (secundario)", color=TXT_MUTED)
        ax_prob.set_xlabel("Ley Cu (%)")
        ax_prob.set_ylabel("Cuantiles teóricos")

        original_sorted = sorted(preview["values"])
        capped_sorted = sorted(preview["capped_values"])
        original_cdf = [(idx + 1) / len(original_sorted) for idx in range(len(original_sorted))]
        capped_cdf = [(idx + 1) / len(capped_sorted) for idx in range(len(capped_sorted))]
        ax_cdf.plot(original_sorted, original_cdf, color=SEM_GRAY, label="Original", linewidth=1.4)
        ax_cdf.plot(capped_sorted, capped_cdf, color=SEM_BLUE, label="Operativa", linewidth=1.6)
        ax_cdf.axvline(cutoff, color=SEM_ORANGE, linestyle="--", linewidth=1.2)
        ax_cdf.set_title("Impacto acumulado del capping", color=PLOT_TXT)
        ax_cdf.set_xlabel("Ley Cu (%)")
        ax_cdf.set_ylabel("F(x)")
        ax_cdf.legend(fontsize=CHART_FONT_SIZE_LEGEND, frameon=False)

        ax_before_after.boxplot([preview["values"], preview["capped_values"]], labels=["Base", "Cap"], patch_artist=True, showfliers=False, widths=0.55)
        ax_before_after.set_title("Comparación resumen", color=TXT_MUTED)
        chart.render()

    def _on_apply_dynamic_cutoff(self) -> None:
        self._trace_ui_action("confirmar_capping", refresh_type="none")
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
            self.eda_use_capping_var.set(bool(self.service.has_confirmed_dynamic_capping()))
            self._refresh_dashboard(reason="dynamic_cutoff_confirmed")

    def _build_domain_definition_summary(self) -> str:
        if not self.domain_definition_local:
            return "Define al menos un dominio para comenzar"
        counts_map = dict(self._get_domain_category_counts())
        lines: list[str] = []
        for domain_name, categories in self.domain_definition_local.items():
            total = sum(int(counts_map.get(cat, 0)) for cat in categories)
            lines.append(f"{domain_name} → [{', '.join(categories)}] (n={total})")
        return "\n".join(lines)

    def _on_domain_base_changed(self) -> None:
        self.domain_selected_categories = set()
        self.domain_feedback_var.set("Selecciona categorías y asigna un nombre de dominio.")
        self._render_control_sections()

    def _on_toggle_domain_category(self, category: str) -> None:
        var = self.domain_category_checkbox_vars.get(category)
        if var is None:
            return
        if bool(var.get()):
            self.domain_selected_categories.add(category)
        else:
            self.domain_selected_categories.discard(category)
        self._update_domain_action_states()

    def _on_assign_domain(self) -> None:
        domain_name = self.domain_name_var.get().strip()
        categories = sorted(self.domain_selected_categories)
        if not self.domain_base_var.get().strip() or not domain_name or not categories:
            self.status_text.set("Debes seleccionar categorías y asignar un nombre al dominio")
            self.domain_feedback_var.set("Debes seleccionar categorías y asignar un nombre al dominio")
            return
        merged = list(dict.fromkeys([*self.domain_definition_local.get(domain_name, []), *categories]))
        self.domain_definition_local[domain_name] = merged
        self.domain_name_var.set("")
        self.domain_selected_categories = set()
        self.status_text.set(f"Dominio {domain_name} creado correctamente")
        self.domain_feedback_var.set(f"Dominio {domain_name} creado correctamente")
        self._render_control_sections()

    def _on_apply_domain_filter(self) -> None:
        result = self.service.set_active_domain(self.domain_filter_var.get())
        self.status_text.set(result.message)
        self._append_activity(result.message)
        if result.success:
            self._refresh_dashboard(reason="domain_filter_changed")

    def _on_apply_domains(self) -> None:
        self._trace_ui_action("aplicar_dominios", refresh_type="none")
        if not self.domain_definition_local:
            self.status_text.set("Define al menos un dominio para comenzar")
            self.domain_feedback_var.set("Define al menos un dominio para comenzar")
            return
        definition = {"variable_base": self.domain_base_var.get().strip(), "domains": dict(self.domain_definition_local)}
        result = self.service.apply_domain_definition(definition)
        if result.success:
            self.status_text.set("Dominios aplicados al dataset")
            self.domain_feedback_var.set("Dominios aplicados al dataset")
            self._append_activity("Dominios aplicados al dataset")
        else:
            self.status_text.set(result.message)
            self.domain_feedback_var.set(result.message)
            self._append_activity(result.message)
        if result.success:
            self.domain_label.set("Dominio: domain_estimation")
            self.domain_records_var.set("Selecciona una burbuja para ver índices y resumen del dominio.")
            self._refresh_dashboard(reason="domains_applied")

    def _on_toggle_eda_capping(self) -> None:
        self._trace_ui_action("actualizar_eda", refresh_type="dashboard_full", extra={"source": "eda_capping_switch"})
        self._refresh_dashboard(reason="eda_capping_switch")

    def _on_refresh_eda(self) -> None:
        self._trace_ui_action("actualizar_eda", refresh_type="dashboard_full", extra={"source": "eda_refresh_button"})
        self._refresh_dashboard(reason="eda_manual_button", force=True)

    def _refresh_summary_cards(self) -> None:
        stats_table = self.service.get_target_statistics_table(use_effective_target=bool(self.eda_use_capping_var.get()))
        stats_map = {str(k).lower(): str(v) for k, v in stats_table}
        self.kpi_value_vars["samples"].set(self._format_kpi_value(stats_map.get("samples", stats_map.get("muestras", "-"))))
        self.kpi_value_vars["valid_count"].set(self._format_kpi_value(stats_map.get("valid_count", stats_map.get("válidos", "-"))))
        self.kpi_value_vars["mean"].set(self._format_kpi_value(stats_map.get("mean", stats_map.get("media", "-"))))
        self.kpi_value_vars["p50"].set(self._format_kpi_value(stats_map.get("p50", "-")))
        self.kpi_value_vars["p90"].set(self._format_kpi_value(stats_map.get("p90", "-")))
        cv_raw = stats_map.get("cv", "-")
        try:
            self.kpi_value_vars["cv"].set(f"{float(str(cv_raw).replace('%', '')) * 100:.2f}%")
        except Exception:
            self.kpi_value_vars["cv"].set(cv_raw)
        self.kpi_value_vars["std"].set(self._format_kpi_value(stats_map.get("std", stats_map.get("desv", "-"))))

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
        self.kpi_value_vars["% truncado"].set(self._format_kpi_value(trunc_pct, as_percent=True) if trunc_pct != "-" else "-")
        self.kpi_value_vars["cutoff actual"].set(self._format_kpi_value(cutoff_actual) if cutoff_actual != "-" and "," not in cutoff_actual else cutoff_actual)

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

    def _trace_ui_action(self, action: str, *, refresh_type: str, extra: dict[str, object] | None = None) -> None:
        state = self.service.get_cutoff_state()
        details: dict[str, object] = {
            "action": action,
            "view": self.service.workflow_state.current_step,
            "target_active": str(state.get("effective_target_column") or self.target_var.get() or ""),
            "capping_confirmed": bool(self.service.has_confirmed_dynamic_capping()),
            "refresh_type": refresh_type,
        }
        if extra:
            details.update(extra)
        self.service.activity_log.log("ui_trace", "info", f"UI acción: {action}", details)
