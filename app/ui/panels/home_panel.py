"""Continuous geostat workflow dashboard with fixed-screen technical workspace."""

from __future__ import annotations

import math
from tkinter import filedialog, messagebox
import threading

import customtkinter as ctk

from app.services.geostat_service import GeostatService
from app.models.operational_state import GeostatOperationalState, WorkflowReadinessState
from app.ui.controllers.variography_controller import VariographyController
from app.ui.panels.dashboard_grid import DashboardGrid
from app.ui.panels.stages import VariographyStageView
from app.ui.renderers import (
    EDARenderContext,
    MatplotlibEDARenderer,
    MatplotlibSpatial2DRenderer,
    MatplotlibSpatial3DRenderer,
    PyVistaSpatial3DRenderer,
    Spatial2DRenderContext,
)
from app.ui.theme import (
    BG_CARD,
    BG_MAIN,
    BG_PANEL,
    BORDER_SOFT,
    BTN_PRIMARY_HOVER,
    BTN_SECONDARY_BG,
    BTN_SECONDARY_HOVER,
    CHART_BG,
    CHART_BORDER,
    CHART_TEXT,
    CHART_FONT_SIZE_LABEL,
    CHART_FONT_SIZE_LEGEND,
    CHART_FONT_SIZE_TICK,
    CHIP_BG,
    DIVIDER_SOFT,
    FONT_BODY,
    FONT_KPI,
    FONT_MICRO,
    FONT_SMALL,
    FONT_SUBTITLE,
    FONT_TITLE,
    FONT_TITLE_COMPACT,
    INPUT_HEIGHT,
    KPI_PRIMARY_BG,
    SEM_BLUE,
    SEM_BLUE_SOFT,
    SEM_GRAY,
    SEM_GREEN,
    SEM_ORANGE,
    SEM_RED,
    SEM_WHITE,
    SURFACE_ELEVATED,
    TEXT_MAIN,
    TEXT_MUTED,
    WF_ACTIVE,
    WF_BLOCKED,
    WF_IDLE,
    WF_READY,
    WF_WARNING,
    BTN_CORNER_RADIUS,
    BTN_DANGER_BG,
    BTN_DANGER_HOVER,
    BTN_DISABLED_BG,
    BTN_HEIGHT_AUX,
    BTN_HEIGHT_PRIMARY,
    BTN_HEIGHT_SECONDARY,
    BTN_PRIMARY_BG,
    BTN_TERTIARY_BG,
    BTN_TERTIARY_HOVER,
    add_reference_line,
    apply_axis_style,
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

PAD_MAIN_X = 7
PAD_CARD_X = 12
PAD_STACK_Y = 1
PAD_SECTION_Y = 4
SIDEBAR_WIDTH = 308
STEP_BUTTON_WIDTH = 106
STEP_BUTTON_HEIGHT = 24
ACTION_TOGGLE_WIDTH = 74
LOG_TOGGLE_WIDTH = 130
LOG_BOX_HEIGHT = 36
WRAP_STAGE_BLOCKED = 1020
WRAP_STAGE_SUMMARY = 1120
WRAP_DYNAMIC_IMPACT = 340
SPATIAL_GUARDRAIL_NOTE = "Uso: lectura exploratoria, no inferencia de continuidad."


def ui_font(token: dict[str, object]) -> ctk.CTkFont:
    return ctk.CTkFont(size=int(token["size"]), weight=str(token["weight"]))

STEP_TO_READINESS_KEY = {
    "Datos": "data",
    "EDA": "eda",
    "Cutoffs": "cutoffs",
    "Espacial": "spatial",
    "Dominios": "domains",
    "Variografía": "variography",
}
STEP_DISPLAY_NAMES = {
    "Cutoffs": "Control de Outliers",
}

def _build_workflow_stage_label(step_name: str, active_step: str, readiness: WorkflowReadinessState) -> str:
    labels = {
        "Datos": "01 Datos",
        "EDA": "02 EDA",
        "Cutoffs": "03 Control de Outliers",
        "Espacial": "04 Espacial",
        "Dominios": "05 Dominios",
        "Variografía": "06 Variografía",
    }
    stage_key = STEP_TO_READINESS_KEY.get(step_name, "")
    stage_state = readiness.stages.get(stage_key, None)
    is_ready = bool(stage_state.ready) if stage_state is not None else False
    has_warning = bool(stage_state.warnings) if stage_state is not None else False
    readiness_marker = "✓ LISTO" if is_ready else ("⚠ ALERTA" if has_warning else "! BLOQ")
    nav_marker = "●" if step_name == active_step else "○"
    return f"{nav_marker} {labels.get(step_name, step_name)} · {readiness_marker}"


def _display_step_name(step_name: str) -> str:
    return STEP_DISPLAY_NAMES.get(step_name, step_name)


def _build_active_step_hint(step_name: str, state: GeostatOperationalState) -> str:
    stage_key = STEP_TO_READINESS_KEY.get(step_name, "")
    stage_state = state.readiness.stages.get(stage_key, None)
    if stage_state is None:
        return "Etapa no lista."
    return stage_state.hint or "Etapa no lista."


def _build_context_chip_texts(state: GeostatOperationalState) -> dict[str, str]:
    resolved_target = str(state.analysis.resolved_target_column or "No definido")
    domain_col = str(state.analysis.active_domain_column or "No definido")
    domain_filter = str(state.analysis.active_domain_filter or "Todos")
    blocked = [name for name, stage in state.readiness.stages.items() if not bool(stage.ready)]
    status = "Listo" if not blocked else f"Bloqueos: {len(blocked)}"
    return {
        "dataset": f"Dataset: {state.analysis.dataset_name}",
        "target": f"Target activo: {resolved_target}",
        "domain": f"Dominio/filtro: {domain_col} · {domain_filter}",
        "status": f"Workflow: {status}",
    }


def _build_unified_context_text(state: GeostatOperationalState, capping_label: str) -> str:
    base = _build_context_chip_texts(state)
    return " · ".join([base["dataset"], base["target"], base["domain"], base["status"], capping_label])


def _build_visual_context_line(snapshot: object, *, local_override: str | None = None) -> str:
    if hasattr(snapshot, "resolved_target_column"):
        resolved_target = str(getattr(snapshot, "resolved_target_column") or "No definido")
        domain_col = str(getattr(snapshot, "active_domain_column") or "No definido")
        domain_filter = str(getattr(snapshot, "active_domain_filter") or "Todos")
    else:
        payload = snapshot if isinstance(snapshot, dict) else {}
        resolved_target = str(payload.get("resolved_target_column") or "No definido")
        domain_col = str(payload.get("active_domain_column") or "No definido")
        domain_filter = str(payload.get("active_domain_filter") or "Todos")
    parts = [f"Target global: {resolved_target}"]
    if local_override and local_override != resolved_target:
        parts.append(f"Override local: {local_override}")
    parts.append(f"Dominio/filtro: {domain_col} · {domain_filter}")
    return " | ".join(parts)


def _should_expand_stage_actions(step_name: str, readiness: WorkflowReadinessState) -> bool:
    if step_name != "Datos":
        return False
    stage_state = readiness.stages.get("data")
    blocking = list(stage_state.blocking_reasons) if stage_state is not None else []
    return "missing_dataset" in blocking


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
        self.dynamic_cutoff_label_var = ctk.StringVar(value="Umbral actual: -")
        self.dynamic_impact_label_var = ctk.StringVar(value="Impacto: -")
        self.eda_use_capping_var = ctk.BooleanVar(value=False)
        self.domain_base_var = ctk.StringVar(value="")
        self.domain_name_var = ctk.StringVar(value="")
        self.domain_confirm_var = ctk.StringVar(value="")
        self.spatial_color_var = ctk.StringVar(value="")
        self.spatial_view_mode_var = ctk.StringVar(value="2D")
        self.domain_filter_var = ctk.StringVar(value="Todos")
        self.domain_filter_lithology_var = ctk.StringVar(value="Todos")
        self.domain_filter_alteration_var = ctk.StringVar(value="Todos")
        self.domain_filter_mine_var = ctk.StringVar(value="Todos")
        self.domain_definition_local: dict[str, list[str]] = {}
        self.domain_feedback_var = ctk.StringVar(value="Define dominios para comenzar.")
        self.domain_selected_categories: set[str] = set()
        self.domain_category_checkbox_vars: dict[str, ctk.BooleanVar] = {}
        self.domain_assign_button: ctk.CTkButton | None = None
        self.domain_apply_button: ctk.CTkButton | None = None
        self.domain_records_var = ctk.StringVar(value="Selecciona una burbuja para visualizar resumen analítico e índices de registros.")
        self.domain_preview_var = ctk.StringVar(value="Previsualización: sin filtros activos.")
        self.domain_history_var = ctk.StringVar(value="Sin dominios confirmados.")

        self.log_visible = False
        self.controls_collapsed = False
        self.workflow_buttons: dict[str, ctk.CTkButton] = {}
        self.context_chip_vars: dict[str, ctk.StringVar] = {}
        self.kpi_value_vars: dict[str, ctk.StringVar] = {}
        self.kpi_cards: dict[str, ctk.CTkFrame] = {}
        self.eda_capping_switch: ctk.CTkSwitch | None = None
        self.domain_menu_widget: ctk.CTkOptionMenu | None = None
        self.column_menus: dict[str, ctk.CTkOptionMenu] = {}
        self.action_bar_body: ctk.CTkFrame | None = None
        self.action_bar_block: ctk.CTkFrame | None = None
        self.action_bar_toggle_button: ctk.CTkButton | None = None
        initial_readiness = self.service.get_workflow_readiness_state()
        self.stage_actions_collapsed = not _should_expand_stage_actions("Datos", initial_readiness)

        self.control_sections: dict[str, ctk.CTkFrame] = {}
        self.workspace_title_var = ctk.StringVar(value="Vista Datos")
        self.workspace_subtitle_var = ctk.StringVar(value="Carga y configura columnas para habilitar el flujo analítico.")
        self.workflow_hint_var = ctk.StringVar(value="Etapa lista.")
        self.unified_context_var = ctk.StringVar(value="Dataset: No cargado · Target activo: No definido · Dominio/filtro: No definido · Workflow: Listo · Capping inactivo")
        self.plot_frame: ctk.CTkFrame | None = None
        self.spatial_3d_widget: ctk.CTkFrame | None = None
        self.eda_renderer = MatplotlibEDARenderer()
        self.spatial_2d_renderer = MatplotlibSpatial2DRenderer(service=self.service)
        self.spatial_3d_renderer = MatplotlibSpatial3DRenderer()
        self.pyvista_spatial_3d_renderer = PyVistaSpatial3DRenderer()
        self.variography_controller = VariographyController(service=self.service)
        self.variography_stage_view = VariographyStageView(controller=self.variography_controller)
        self._spatial_3d_renderer_warning_cache: str = ""
        self._cutoff_preview_after_id: str | None = None
        self._last_cutoff_preview_signature: tuple[object, ...] | None = None
        self._stage_hosts: dict[str, ctk.CTkFrame] = {}
        self._rendered_stage_signatures: dict[str, tuple[object, ...]] = {}
        self._resize_after_id: str | None = None
        self._last_view_body_size: tuple[int, int] = (0, 0)
        self.domain_name_var.trace_add("write", self._on_domain_name_changed)

        self._build_layout()
        self._render_step("Datos")

    def _button_style(self, role: str = "secondary") -> dict[str, object]:
        if role == "primary":
            return {
                "height": BTN_HEIGHT_PRIMARY,
                "corner_radius": BTN_CORNER_RADIUS,
                "fg_color": BTN_PRIMARY_BG,
                "hover_color": BTN_PRIMARY_HOVER,
                "text_color": SEM_WHITE,
            }
        if role == "aux":
            return {
                "height": BTN_HEIGHT_AUX,
                "corner_radius": BTN_CORNER_RADIUS,
                "fg_color": BTN_TERTIARY_BG,
                "hover_color": BTN_TERTIARY_HOVER,
                "text_color": TEXT_MUTED,
            }
        if role == "danger":
            return {
                "height": BTN_HEIGHT_SECONDARY,
                "corner_radius": BTN_CORNER_RADIUS,
                "fg_color": BTN_DANGER_BG,
                "hover_color": BTN_DANGER_HOVER,
                "text_color": SEM_WHITE,
            }
        return {
            "height": BTN_HEIGHT_SECONDARY,
            "corner_radius": BTN_CORNER_RADIUS,
            "fg_color": BTN_NEUTRAL,
            "hover_color": BTN_NEUTRAL_HOVER,
            "text_color": TEXT_MAIN,
        }

    def _option_menu_style(self) -> dict[str, object]:
        return {
            "height": INPUT_HEIGHT,
            "fg_color": BG_CARD,
            "button_color": SURFACE_ELEVATED,
            "button_hover_color": BTN_NEUTRAL_HOVER,
            "dropdown_fg_color": BG_PANEL,
            "dropdown_hover_color": BTN_NEUTRAL_HOVER,
            "text_color": TEXT_MAIN,
        }

    def _build_layout(self) -> None:
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_header().grid(row=0, column=0, sticky="ew", padx=PAD_MAIN_X, pady=(2, 0))
        self._build_step_progress().grid(row=1, column=0, sticky="ew", padx=PAD_MAIN_X, pady=(0, 0))

        workspace = ctk.CTkFrame(self, fg_color=BG_MAIN)
        workspace.grid(row=2, column=0, sticky="nsew", padx=PAD_MAIN_X, pady=(0, PAD_STACK_Y))
        workspace.grid_columnconfigure(0, weight=1)
        workspace.grid_rowconfigure(0, weight=1)

        self.content_panel = ctk.CTkFrame(workspace, fg_color=BG_PANEL, corner_radius=8)
        self.content_panel.grid(row=0, column=0, sticky="nsew")
        self.content_panel.grid_columnconfigure(0, weight=1)
        self.content_panel.grid_rowconfigure(3, weight=1, minsize=420)

        top = ctk.CTkFrame(self.content_panel, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=PAD_MAIN_X, pady=(2, 0))
        top.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(top, textvariable=self.workspace_title_var, font=ui_font(FONT_SUBTITLE), text_color=TXT_MAIN).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(top, textvariable=self.status_text, font=ui_font(FONT_SMALL), text_color=TXT_MUTED).grid(row=0, column=1, sticky="e")
        ctk.CTkLabel(top, textvariable=self.workflow_hint_var, font=ui_font(FONT_MICRO), text_color=SEM_ORANGE).grid(row=1, column=0, sticky="w", pady=(0, 0))

        self._build_kpi_strip(self.content_panel)
        self._build_stage_action_bar(self.content_panel)

        self.view_body = ctk.CTkFrame(self.content_panel, fg_color=BG_SOFT, corner_radius=8, border_width=1, border_color=BORDER_SOFT)
        self.view_body.grid(row=3, column=0, sticky="nsew", padx=PAD_MAIN_X, pady=(1, 1))
        self.view_body.grid_columnconfigure(0, weight=1)
        self.view_body.grid_rowconfigure(0, weight=1)
        self.view_body.bind("<Configure>", self._on_view_body_configure, add="+")

        self.aux_controls_host = self._build_control_panel(self.content_panel)
        self.aux_controls_host.grid(row=4, column=0, sticky="ew", padx=PAD_MAIN_X, pady=(0, 2))
        self.aux_controls_host.grid_remove()

        self.log_panel = ctk.CTkFrame(self, fg_color=BG_PANEL)
        self.log_panel.grid(row=3, column=0, sticky="ew", padx=PAD_MAIN_X, pady=(0, 0))
        self.log_panel.grid_columnconfigure(1, weight=1)
        ctk.CTkButton(
            self.log_panel,
            text="Ocultar/Mostrar log",
            width=LOG_TOGGLE_WIDTH,
            **self._button_style("aux"),
            command=self._toggle_log,
        ).grid(row=0, column=0, sticky="w", padx=6, pady=4)
        self.log_box = ctk.CTkTextbox(self.log_panel, height=LOG_BOX_HEIGHT, fg_color=BG_SOFT, text_color=TXT_MAIN, font=ui_font(FONT_SMALL))
        self.log_box.grid(row=0, column=1, sticky="ew", padx=6, pady=3)
        self.log_box.insert("1.0", "Actividad reciente\n")
        self.log_box.configure(state="disabled")
        self.log_box.grid_remove()

    def _build_header(self) -> ctk.CTkFrame:
        header = ctk.CTkFrame(self, fg_color=BG_PANEL, corner_radius=8)
        header.grid_columnconfigure(0, weight=1)
        header.grid_columnconfigure(1, weight=0)
        identity = ctk.CTkFrame(header, fg_color="transparent")
        identity.grid(row=0, column=0, sticky="w", padx=PAD_CARD_X, pady=(1, 1))
        ctk.CTkLabel(identity, text="GeoStat Py", font=ui_font(FONT_TITLE_COMPACT), text_color=TXT_MAIN).pack(anchor="w")
        context_chip = ctk.CTkFrame(header, fg_color=CHIP_BG, corner_radius=7)
        context_chip.grid(row=1, column=0, sticky="ew", padx=PAD_CARD_X, pady=(0, 1))
        ctk.CTkLabel(
            context_chip,
            textvariable=self.unified_context_var,
            text_color=TXT_MAIN,
            font=ui_font(FONT_MICRO),
            anchor="w",
            justify="left",
        ).pack(fill="x", padx=7, pady=3)

        actions = ctk.CTkFrame(header, fg_color=SURFACE_ELEVATED, corner_radius=8)
        actions.grid(row=0, column=1, rowspan=2, sticky="e", padx=7, pady=1)
        actions_row = ctk.CTkFrame(actions, fg_color="transparent")
        actions_row.pack(fill="x", padx=5, pady=2)
        self.update_repo_button = ctk.CTkButton(actions_row, text="Actualizar", width=88, command=self._on_update_repo, **self._button_style("aux"))
        self.update_repo_button.pack(side="left", padx=3)
        ctk.CTkButton(actions_row, text="Log", width=64, command=self._on_export_log, **self._button_style("aux")).pack(side="left", padx=3)
        return header

    def _build_step_progress(self) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(self, fg_color=BG_PANEL, corner_radius=8)
        labels = {
            "Datos": "01 Datos",
            "EDA": "02 EDA",
            "Cutoffs": "03 Control de Outliers",
            "Espacial": "04 Espacial",
            "Dominios": "05 Dominios",
            "Variografía": "06 Variografía",
        }
        for step in ["Datos", "EDA", "Cutoffs", "Espacial", "Dominios", "Variografía"]:
            btn = ctk.CTkButton(
                frame,
                text=labels[step],
                width=STEP_BUTTON_WIDTH,
                height=STEP_BUTTON_HEIGHT,
                corner_radius=BTN_CORNER_RADIUS,
                fg_color=C_TAB_IDLE,
                hover_color=BTN_NEUTRAL_HOVER,
                border_width=1,
                border_color=BORDER_SOFT,
                font=ui_font(FONT_MICRO),
                command=lambda s=step: self._on_change_step(s),
            )
            btn.pack(side="left", padx=2, pady=1)
            self.workflow_buttons[step] = btn
        return frame

    def _build_control_panel(self, parent: ctk.CTkFrame) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(parent, width=SIDEBAR_WIDTH, fg_color=BG_PANEL, corner_radius=9)
        frame.grid_propagate(False)

        head = ctk.CTkFrame(frame, fg_color="transparent")
        head.pack(fill="x", padx=8, pady=(6, 3))
        ctk.CTkLabel(head, text="Panel auxiliar (avanzado)", text_color=TXT_MAIN, font=ui_font(FONT_SUBTITLE)).pack(side="left")
        ctk.CTkButton(head, text="Colapsar" if not self.controls_collapsed else "Expandir", width=90, command=self._toggle_controls, **self._button_style("aux")).pack(side="right")

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
        if not hasattr(self, "controls_container"):
            return
        for child in self.controls_container.winfo_children():
            child.destroy()
        self.column_menus = {}
        if self.controls_collapsed:
            ctk.CTkLabel(self.controls_container, text="Panel colapsado", text_color=TXT_MUTED, font=ui_font(FONT_SMALL)).pack(anchor="w", padx=8, pady=8)
            return

        sections = {
            "Datos": self._build_data_controls(self.controls_container),
            "EDA": self._build_eda_controls(self.controls_container),
            "Cutoffs": self._build_cutoff_controls(self.controls_container),
            "Espacial": self._build_spatial_controls(self.controls_container),
            "Dominios": self._build_domains_controls(self.controls_container),
            "Variografía": self._build_variography_controls(self.controls_container),
        }
        active = self.service.workflow_state.current_step
        if active in sections:
            sections[active].destroy()
            sections.pop(active, None)
        self.control_sections = sections
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
        ctk.CTkButton(section, text="Cargar CSV", command=self._on_load_csv, **self._button_style("secondary")).pack(fill="x", padx=6, pady=(0, 5))
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
        self.domain_menu_widget = ctk.CTkOptionMenu(grid, variable=self.domain_var, values=domain_candidates, state=domain_state, **self._option_menu_style())
        self.domain_menu_widget.grid(row=row, column=0, columnspan=2, sticky="ew", padx=4, pady=(0, 4))
        row += 1
        ctk.CTkLabel(grid, text="5) Hole ID (opcional)", text_color=TXT_MUTED, font=ui_font(FONT_SMALL)).grid(row=row, column=0, columnspan=2, sticky="w", padx=4, pady=(4, 2))
        row += 1
        self._selector(grid, "Hole ID", self.hole_var, cols, row, 0, key="hole")
        row += 2
        ctk.CTkLabel(grid, text="6) Confirmar", text_color=TXT_MAIN, font=ui_font(FONT_SMALL)).grid(row=row, column=0, columnspan=2, sticky="w", padx=4, pady=(6, 2))
        row += 1
        ctk.CTkButton(grid, text="Confirmar datos", command=self._on_apply_config, **self._button_style("primary")).grid(row=row, column=0, columnspan=2, sticky="ew", pady=(2, 0))
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
        ctk.CTkButton(section, text="Actualizar vista", command=self._on_refresh_eda, **self._button_style("secondary")).pack(fill="x", padx=6, pady=(0, 5))
        return section

    def _build_cutoff_controls(self, parent: ctk.CTkScrollableFrame) -> ctk.CTkFrame:
        section = self._section_shell(parent, "Control de Outliers")
        ctk.CTkLabel(section, text="Opciones locales de preview/aplicación", text_color=TXT_MUTED, font=ui_font(FONT_SMALL)).pack(anchor="w", padx=6, pady=(0, 2))
        numeric_columns = self.service.get_numeric_columns()
        ctk.CTkOptionMenu(section, variable=self.cutoff_target_var, values=numeric_columns or [""], state="normal" if numeric_columns else "disabled", command=lambda _v: self._schedule_cutoff_preview(), **self._option_menu_style()).pack(fill="x", padx=6, pady=(0, 4))
        ctk.CTkSwitch(section, text="Activar límites manuales", variable=self.cutoff_enabled_var, text_color=TXT_MAIN).pack(fill="x", padx=6, pady=(0, 4))
        ctk.CTkSwitch(section, text="Activar capping dinámico", variable=self.dynamic_cutoff_enabled_var, text_color=TXT_MAIN, command=self._schedule_cutoff_preview).pack(fill="x", padx=6, pady=(0, 4))
        ctk.CTkEntry(section, textvariable=self.cutoff_limits_var, height=INPUT_HEIGHT, placeholder_text="Límites manuales: 0.5, 1.2, 2.0").pack(fill="x", padx=6, pady=(0, 4))
        ctk.CTkButton(section, text="Aplicar límites manuales", command=self._on_apply_cutoffs, **self._button_style("secondary")).pack(fill="x", padx=6, pady=(0, 5))
        return section

    def _build_spatial_controls(self, parent: ctk.CTkScrollableFrame) -> ctk.CTkFrame:
        section = self._section_shell(parent, "Visualización espacial")
        ctk.CTkLabel(section, text="Opciones locales de la vista espacial", text_color=TXT_MUTED, font=ui_font(FONT_SMALL)).pack(anchor="w", padx=6, pady=(0, 2))
        ctk.CTkLabel(section, text="Vista fija XY / XZ / YZ + metadatos.", text_color=TXT_MUTED, font=ui_font(FONT_SMALL)).pack(anchor="w", padx=6, pady=(0, 5))
        ctk.CTkLabel(section, text="Modo vista", text_color=TXT_MUTED, font=ui_font(FONT_SMALL)).pack(anchor="w", padx=6, pady=(0, 2))
        ctk.CTkSegmentedButton(
            section,
            variable=self.spatial_view_mode_var,
            values=["2D", "3D"],
            command=self._on_spatial_mode_changed,
        ).pack(fill="x", padx=6, pady=(0, 4))
        color_options = self._get_spatial_color_options()
        if self.spatial_color_var.get() not in color_options:
            self.spatial_color_var.set(color_options[0] if color_options else "")
        ctk.CTkLabel(section, text="Color por", text_color=TXT_MUTED, font=ui_font(FONT_SMALL)).pack(anchor="w", padx=6, pady=(0, 2))
        ctk.CTkOptionMenu(
            section,
            variable=self.spatial_color_var,
            values=color_options or [""],
            state="normal" if color_options else "disabled",
            command=lambda _v: self._on_spatial_color_changed(),
            **self._option_menu_style(),
        ).pack(fill="x", padx=6, pady=(0, 4))
        ctk.CTkLabel(section, text="(Local) No cambia el target global del workflow.", text_color=TXT_MUTED, font=ui_font(FONT_SMALL)).pack(anchor="w", padx=6, pady=(0, 3))
        domain_filters = ["Todos", *self.service.get_domain_estimation_values()]
        if self.domain_filter_var.get() not in domain_filters:
            self.domain_filter_var.set("Todos")
        ctk.CTkLabel(section, text="Filtro global de dominio", text_color=TXT_MUTED, font=ui_font(FONT_SMALL)).pack(anchor="w", padx=6, pady=(0, 2))
        ctk.CTkOptionMenu(section, variable=self.domain_filter_var, values=domain_filters, state="normal", **self._option_menu_style()).pack(fill="x", padx=6, pady=(0, 4))
        ctk.CTkButton(section, text="Aplicar filtro dominio", command=self._on_apply_domain_filter, **self._button_style("secondary")).pack(fill="x", padx=6, pady=(0, 4))
        return section

    def _build_domains_controls(self, parent: ctk.CTkScrollableFrame) -> ctk.CTkFrame:
        section = self._section_shell(parent, "05 Dominios")
        ctk.CTkLabel(section, text="Módulo temporalmente deshabilitado", text_color=TXT_MUTED, font=ui_font(FONT_BODY)).pack(anchor="w", padx=6, pady=(4, 6))
        return section

    def _build_variography_controls(self, parent: ctk.CTkScrollableFrame) -> ctk.CTkFrame:
        section = self._section_shell(parent, "06 Variografía")
        ctk.CTkLabel(section, text="Configura parámetros y calcula variograma experimental en la vista principal.", text_color=TXT_MUTED, font=ui_font(FONT_BODY)).pack(anchor="w", padx=6, pady=(4, 6))
        return section

    def _focus_sidebar_sections(self, step_name: str) -> None:
        for name, frame in self.control_sections.items():
            frame.configure(fg_color=BG_SOFT if name == step_name else "transparent")

    def _build_kpi_strip(self, parent: ctk.CTkFrame) -> None:
        block = ctk.CTkFrame(parent, fg_color=BG_PANEL, corner_radius=0)
        block.grid(row=1, column=0, sticky="ew", padx=2, pady=(0, 1))
        ctk.CTkLabel(block, text="KPIs clave", text_color=TXT_MUTED, font=ui_font(FONT_MICRO)).pack(anchor="w", padx=8, pady=(1, 0))
        cards = ctk.CTkFrame(block, fg_color="transparent")
        cards.pack(fill="x", padx=4, pady=2)
        labels_by_key = {
            "valid_count": "N válido",
            "p90": "P90",
            "cv": "Coeficiente de variación (%)",
            "cutoff actual": "Umbral actual",
        }
        keys = list(labels_by_key.keys())
        primary_keys = {"cv"}
        for idx, key in enumerate(keys):
            cards.grid_columnconfigure(idx, weight=1 if key != "cv" else 2)
            card_color = KPI_PRIMARY if key in primary_keys else BG_CARD
            card = ctk.CTkFrame(cards, fg_color=card_color, corner_radius=5)
            card.grid(row=0, column=idx, padx=3, pady=1, sticky="nsew")
            border_width = 1 if key in primary_keys else 0
            card.configure(border_width=border_width, border_color=SEM_BLUE_SOFT if key in primary_keys else BORDER_SOFT)
            ctk.CTkLabel(card, text=labels_by_key[key], font=ui_font(FONT_MICRO), text_color=TXT_MUTED).pack(anchor="w", padx=6, pady=(2, 0))
            val = ctk.StringVar(value="-")
            self.kpi_value_vars[key] = val
            self.kpi_cards[key] = card
            value_font = ui_font(FONT_KPI if key in primary_keys else FONT_BODY)
            ctk.CTkLabel(card, textvariable=val, text_color=TXT_MAIN, font=value_font).pack(anchor="w", padx=6, pady=(0, 2))

    def _build_stage_action_bar(self, parent: ctk.CTkFrame) -> None:
        block = ctk.CTkFrame(parent, fg_color=BG_SOFT, corner_radius=7)
        block.grid(row=2, column=0, sticky="ew", padx=6, pady=(0, 0))
        block.grid_columnconfigure(0, weight=1)
        self.action_bar_block = block
        head = ctk.CTkFrame(block, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", padx=6, pady=(1, 0))
        head.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(head, text="Controles etapa activa", text_color=TXT_MUTED, font=ui_font(FONT_MICRO)).grid(row=0, column=0, sticky="w")
        toggle_text = "Expandir" if self.stage_actions_collapsed else "Ocultar"
        self.action_bar_toggle_button = ctk.CTkButton(head, text=toggle_text, width=ACTION_TOGGLE_WIDTH, command=self._toggle_stage_actions, **self._button_style("aux"))
        self.action_bar_toggle_button.grid(row=0, column=1, sticky="e")
        self.action_bar_body = ctk.CTkFrame(block, fg_color="transparent")
        self.action_bar_body.grid(row=1, column=0, sticky="ew", padx=6, pady=(0, 2))
        if self.stage_actions_collapsed:
            self.action_bar_body.grid_remove()

    def _toggle_stage_actions(self) -> None:
        self.stage_actions_collapsed = not self.stage_actions_collapsed
        if self.action_bar_toggle_button is not None:
            self.action_bar_toggle_button.configure(text="Expandir" if self.stage_actions_collapsed else "Ocultar")
        if self.action_bar_body is not None:
            if self.stage_actions_collapsed:
                self.action_bar_body.grid_remove()
            else:
                self.action_bar_body.grid()
                self._render_stage_action_bar(self.service.workflow_state.current_step)

    def _render_stage_action_bar(self, stage: str) -> None:
        if self.action_bar_body is None:
            return
        for child in self.action_bar_body.winfo_children():
            child.destroy()
        if self.stage_actions_collapsed:
            self.action_bar_body.grid_remove()
            return
        self.action_bar_body.grid()
        self.action_bar_body.grid_columnconfigure(0, weight=1)
        readiness = self.service.get_workflow_readiness_state()
        stage_key = STEP_TO_READINESS_KEY.get(stage, "")
        stage_state = readiness.stages.get(stage_key, None)
        if not bool(stage_state.ready) if stage_state is not None else True:
            self._build_blocked_message_card(self.action_bar_body, stage)

        if stage == "Datos":
            self._build_data_actions_inline(self.action_bar_body)
        elif stage == "EDA":
            self._build_eda_actions_inline(self.action_bar_body)
        elif stage == "Cutoffs":
            self._build_cutoff_actions_inline(self.action_bar_body)
        elif stage == "Espacial":
            self._build_spatial_actions_inline(self.action_bar_body)
        elif stage == "Dominios":
            self._build_domains_actions_inline(self.action_bar_body)
        else:
            self._build_variography_actions_inline(self.action_bar_body)

    def _build_blocked_message_card(self, parent: ctk.CTkFrame, stage: str) -> None:
        state = self.service.get_operational_state()
        message = _build_active_step_hint(stage, state)
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
        ctk.CTkButton(row, text="Cargar CSV", command=self._on_load_csv, **self._button_style("secondary")).grid(row=0, column=0, padx=3, pady=2, sticky="ew")
        self._selector_inline(row, "X", self.x_var, self.service.get_available_columns() or [""], 0, 1)
        self._selector_inline(row, "Y", self.y_var, self.service.get_available_columns() or [""], 0, 2)
        self._selector_inline(row, "Z", self.z_var, self.service.get_available_columns() or [""], 0, 3)
        self._selector_inline(row, "Target", self.target_var, self.service.get_numeric_columns() or [""], 0, 4)
        ctk.CTkCheckBox(row, text="Usar dominio", variable=self.use_domain_var, command=self._on_domain_mode_change).grid(row=0, column=5, padx=3, pady=2, sticky="w")
        domain_options = self.service.get_domain_candidate_columns() or [""]
        self._selector_inline(row, "Dominio", self.domain_var, domain_options, 0, 6, state="normal" if self.use_domain_var.get() else "disabled")
        ctk.CTkButton(row, text="Confirmar", command=self._on_apply_config, **self._button_style("primary")).grid(row=0, column=7, padx=3, pady=2, sticky="ew")

    def _selector_inline(self, parent: ctk.CTkFrame, label: str, variable: ctk.StringVar, values: list[str], row: int, col: int, *, state: str | None = None) -> None:
        group = ctk.CTkFrame(parent, fg_color="transparent")
        group.grid(row=row, column=col, padx=2, pady=1, sticky="ew")
        ctk.CTkLabel(group, text=label, text_color=TXT_MUTED, font=ui_font(FONT_SMALL)).pack(anchor="w")
        if values and variable.get() not in values:
            variable.set(values[0])
        computed_state = state or ("normal" if values and values[0] else "disabled")
        ctk.CTkOptionMenu(group, variable=variable, values=values or [""], state=computed_state, **self._option_menu_style()).pack(fill="x")

    def _build_eda_actions_inline(self, parent: ctk.CTkFrame) -> None:
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.grid(row=1, column=0, sticky="ew")
        row.grid_columnconfigure((0, 1), weight=0)
        row.grid_columnconfigure(2, weight=1)
        has_capping = self.service.has_confirmed_dynamic_capping()
        if not has_capping:
            self.eda_use_capping_var.set(False)
        cluster = ctk.CTkFrame(row, fg_color=BG_CARD, corner_radius=7)
        cluster.grid(row=0, column=0, columnspan=2, sticky="w", padx=(2, 6), pady=2)
        ctk.CTkSwitch(cluster, text="EDA con capping confirmado", variable=self.eda_use_capping_var, state="normal" if has_capping else "disabled", command=self._on_toggle_eda_capping).pack(side="left", padx=6, pady=4)
        ctk.CTkButton(cluster, text="Actualizar EDA", width=120, command=self._on_refresh_eda, **self._button_style("secondary")).pack(side="left", padx=(0, 6), pady=4)
        ctk.CTkLabel(row, text="Histograma · QQ · boxplots con foco en dispersión y sesgo.", text_color=TXT_MUTED, font=ui_font(FONT_SMALL)).grid(row=0, column=2, sticky="e", padx=2, pady=2)

    def _build_cutoff_actions_inline(self, parent: ctk.CTkFrame) -> None:
        band = ctk.CTkFrame(parent, fg_color=BG_CARD, corner_radius=7)
        band.grid(row=1, column=0, sticky="ew")
        for col in range(6):
            band.grid_columnconfigure(col, weight=1)
        ctk.CTkOptionMenu(
            band,
            variable=self.cutoff_target_var,
            values=self.service.get_numeric_columns() or [""],
            state="normal" if self.service.get_numeric_columns() else "disabled",
            command=lambda _v: self._schedule_cutoff_preview(),
            **self._option_menu_style(),
        ).grid(row=0, column=0, padx=4, pady=(4, 2), sticky="ew")
        ctk.CTkSwitch(band, text="Manual", variable=self.cutoff_enabled_var).grid(row=0, column=1, padx=4, pady=(4, 2), sticky="w")
        ctk.CTkSwitch(band, text="Dinámico", variable=self.dynamic_cutoff_enabled_var, command=self._schedule_cutoff_preview).grid(row=0, column=2, padx=4, pady=(4, 2), sticky="w")
        ctk.CTkOptionMenu(band, variable=self.dynamic_mode_var, values=["Percentil", "Valor absoluto"], command=lambda _v: self._schedule_cutoff_preview(), **self._option_menu_style()).grid(row=0, column=3, padx=4, pady=(4, 2), sticky="ew")
        ctk.CTkLabel(band, textvariable=self.dynamic_percentile_label_var, text_color=TXT_MUTED, font=ui_font(FONT_SMALL)).grid(row=0, column=4, padx=4, pady=(4, 2), sticky="e")
        ctk.CTkButton(band, text="Aplicar", command=self._on_apply_cutoff_primary, **self._button_style("primary")).grid(row=0, column=5, padx=4, pady=(4, 2), sticky="ew")
        ctk.CTkSlider(
            band,
            from_=0,
            to=100,
            variable=self.dynamic_slider_var,
            command=self._on_slider_change,
            button_color=SEM_BLUE_SOFT,
            progress_color=SEM_BLUE_SOFT,
        ).grid(row=1, column=0, columnspan=5, padx=4, pady=(0, 4), sticky="ew")
        ctk.CTkLabel(band, textvariable=self.dynamic_cutoff_label_var, text_color=TXT_MUTED, font=ui_font(FONT_SMALL)).grid(row=1, column=5, padx=4, pady=(0, 4), sticky="e")

    def _on_apply_cutoff_primary(self) -> None:
        if self.service.workflow_state.current_step != "Cutoffs":
            return
        if bool(self.dynamic_cutoff_enabled_var.get()):
            self._on_apply_dynamic_cutoff()
            return
        self._on_apply_cutoffs()

    def _build_spatial_actions_inline(self, parent: ctk.CTkFrame) -> None:
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.grid(row=1, column=0, sticky="ew")
        row.grid_columnconfigure((0, 1, 2, 3), weight=1)
        color_options = self._get_spatial_color_options()
        if self.spatial_color_var.get() not in color_options:
            self.spatial_color_var.set(color_options[0] if color_options else "")
        ctk.CTkSegmentedButton(
            row,
            variable=self.spatial_view_mode_var,
            values=["2D", "3D"],
            command=self._on_spatial_mode_changed,
        ).grid(row=0, column=0, padx=3, pady=2, sticky="ew")
        ctk.CTkOptionMenu(
            row,
            variable=self.spatial_color_var,
            values=color_options or [""],
            state="normal" if color_options else "disabled",
            command=lambda _v: self._on_spatial_color_changed(),
            **self._option_menu_style(),
        ).grid(row=0, column=1, padx=3, pady=2, sticky="ew")
        domain_filters = ["Todos", *self.service.get_domain_estimation_values()]
        if self.domain_filter_var.get() not in domain_filters:
            self.domain_filter_var.set("Todos")
        ctk.CTkOptionMenu(row, variable=self.domain_filter_var, values=domain_filters, state="normal", **self._option_menu_style()).grid(row=0, column=2, padx=3, pady=2, sticky="ew")
        ctk.CTkButton(row, text="Aplicar filtro dominio", command=self._on_apply_domain_filter, **self._button_style("secondary")).grid(row=0, column=3, padx=3, pady=2, sticky="ew")

    def _build_domains_actions_inline(self, parent: ctk.CTkFrame) -> None:
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.grid(row=1, column=0, sticky="ew")
        row.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(row, text="Módulo temporalmente deshabilitado", text_color=TXT_MUTED, font=ui_font(FONT_BODY)).grid(row=0, column=0, sticky="w", padx=4, pady=2)

    def _build_variography_actions_inline(self, parent: ctk.CTkFrame) -> None:
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.grid(row=1, column=0, sticky="ew")
        row.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(row, text="Variografía experimental activa: usa la vista para configurar y calcular.", text_color=TXT_MUTED, font=ui_font(FONT_BODY)).grid(row=0, column=0, sticky="w", padx=4, pady=2)

    def _apply_kpi_focus(self, step_name: str) -> None:
        focus_by_step = {
            "Datos": {"cv"},
            "EDA": {"cv"},
            "Cutoffs": {"cv"},
            "Espacial": {"cv"},
            "Dominios": {"cv"},
            "Variografía": {"cv"},
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

        ctk.CTkOptionMenu(parent, variable=self.dynamic_mode_var, values=["Percentil", "Valor absoluto"], command=lambda _v: self._schedule_cutoff_preview(), **self._option_menu_style()).grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 3))
        ctk.CTkEntry(parent, textvariable=self.dynamic_output_var, height=INPUT_HEIGHT, placeholder_text="salida capped").grid(row=2, column=1, sticky="ew", padx=8, pady=(0, 3))

        ctk.CTkSlider(parent, from_=0, to=100, variable=self.dynamic_slider_var, command=self._on_slider_change, button_color=SEM_BLUE_SOFT, progress_color=SEM_BLUE_SOFT).grid(row=3, column=0, columnspan=2, sticky="ew", padx=8, pady=(0, 3))
        ctk.CTkLabel(parent, textvariable=self.dynamic_percentile_label_var, text_color=TXT_MAIN).grid(row=4, column=0, sticky="w", padx=8)
        ctk.CTkLabel(parent, textvariable=self.dynamic_cutoff_label_var, text_color=TXT_MAIN).grid(row=4, column=1, sticky="e", padx=8)

        ctk.CTkFrame(parent, height=1, fg_color=DIVIDER_SOFT).grid(row=5, column=0, columnspan=2, sticky="ew", padx=8, pady=4)
        ctk.CTkLabel(parent, textvariable=self.dynamic_impact_label_var, text_color=TXT_MAIN, font=ui_font(FONT_SMALL), wraplength=WRAP_DYNAMIC_IMPACT, justify="left").grid(row=6, column=0, columnspan=2, sticky="w", padx=8)

        ctk.CTkSwitch(parent, text="Capping dinámico", variable=self.dynamic_cutoff_enabled_var, text_color=TXT_MAIN, command=self._schedule_cutoff_preview).grid(row=7, column=0, sticky="w", padx=8, pady=(5, 6))
        ctk.CTkButton(parent, text="Confirmar capping", command=self._on_apply_dynamic_cutoff, **self._button_style("primary")).grid(row=7, column=1, sticky="ew", padx=8, pady=(5, 6))

    def _on_view_body_configure(self, _event) -> None:
        if self._resize_after_id is not None:
            self.after_cancel(self._resize_after_id)
        self._resize_after_id = self.after(120, self._handle_view_resize)

    def _handle_view_resize(self) -> None:
        self._resize_after_id = None
        width = int(self.view_body.winfo_width())
        height = int(self.view_body.winfo_height())
        if width <= 20 or height <= 20:
            return
        current_size = (width, height)
        if current_size == self._last_view_body_size:
            return
        self._last_view_body_size = current_size
        current_step = self.service.workflow_state.current_step
        # Resize policy: avoid full stage rebuild on normal container resize.
        # DashboardGrid and embedded canvases handle their own responsive fitting.
        if current_step not in self._rendered_stage_signatures:
            self._show_stage_view(current_step, force_rebuild=False)

    def _get_stage_host(self, stage: str) -> ctk.CTkFrame:
        host = self._stage_hosts.get(stage)
        if host is not None and host.winfo_exists():
            return host
        host = ctk.CTkFrame(self.view_body, fg_color=BG_PANEL)
        host.grid(row=0, column=0, sticky="nsew")
        host.grid_remove()
        self._stage_hosts[stage] = host
        return host

    def _show_only_stage_host(self, stage: str) -> ctk.CTkFrame:
        for name, host in self._stage_hosts.items():
            if not host.winfo_exists():
                continue
            if name == stage:
                host.grid()
            else:
                host.grid_remove()
        return self._get_stage_host(stage)

    def _invalidate_stage_cache(self, stage: str | None = None) -> None:
        if stage is None:
            self._rendered_stage_signatures.clear()
            return
        self._rendered_stage_signatures.pop(stage, None)

    def _show_stage_view(self, stage: str, *, force_rebuild: bool = False) -> None:
        stage_host = self._show_only_stage_host(stage)
        stage_host.grid_columnconfigure(0, weight=1)
        stage_host.grid_rowconfigure(0, weight=1)
        readiness = self.service.get_workflow_readiness_state()
        stage_key = STEP_TO_READINESS_KEY.get(stage, "")
        stage_state = readiness.stages.get(stage_key, None)
        if stage != "Datos" and not bool(stage_state.ready) if stage_state is not None else False:
            self.workspace_title_var.set(f"{_display_step_name(stage)} – etapa bloqueada")
            self.workspace_subtitle_var.set("Completa la configuración indicada para habilitar esta vista.")
            DashboardGrid.clear(stage_host)
            self._render_blocked_stage_view(stage, stage_host)
            self._rendered_stage_signatures[stage] = ("blocked",)
            return

        if stage == "Datos":
            if not force_rebuild and self._rendered_stage_signatures.get(stage) == ("ready",):
                return
            DashboardGrid.clear(stage_host)
            self.workspace_title_var.set("Preparación de datos – habilitación del flujo")
            self.workspace_subtitle_var.set("Paso 1 de workflow: carga y validación estructural para habilitar todas las vistas.")
            card = ctk.CTkFrame(stage_host, fg_color=BG_SOFT, corner_radius=8)
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
            self._rendered_stage_signatures[stage] = ("ready",)
            return

        if stage == "EDA":
            self.workspace_title_var.set("Diagnóstico de distribución")
            self.workspace_subtitle_var.set("")
            self._render_eda_view(stage_host, force_rebuild=force_rebuild)
            return

        if stage == "Cutoffs":
            self.workspace_title_var.set("Impacto de capping – control de outliers")
            self.workspace_subtitle_var.set("Cuantifica cuánto cambia la distribución antes de confirmar el umbral operativo.")
            self._render_cutoff_view(stage_host, force_rebuild=force_rebuild)
            return

        if stage == "Espacial":
            self.workspace_title_var.set("Continuidad espacial – lectura exploratoria")
            self.workspace_subtitle_var.set("Contrasta continuidad visual en XY/XZ/YZ con el target activo.")
            self._render_spatial_view(stage_host, force_rebuild=force_rebuild)
            return

        if stage == "Dominios":
            self.workspace_title_var.set("05 Dominios")
            self.workspace_subtitle_var.set("")
            self._render_domains_view(stage_host, force_rebuild=force_rebuild)
            return
        self.workspace_title_var.set("06 Variografía")
        self.workspace_subtitle_var.set("")
        self._render_variography_view(stage_host, force_rebuild=force_rebuild)

    def _render_blocked_stage_view(self, stage: str, parent: ctk.CTkFrame) -> None:
        card = ctk.CTkFrame(parent, fg_color=BG_SOFT, corner_radius=8)
        card.grid(row=0, column=0, sticky="nsew")
        card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(card, text=f"Etapa {_display_step_name(stage)} bloqueada", text_color=TXT_MAIN, font=ui_font(FONT_SUBTITLE)).grid(row=0, column=0, sticky="w", padx=10, pady=(10, 4))
        hint = _build_active_step_hint(stage, self.service.get_operational_state())
        ctk.CTkLabel(card, text=hint, text_color=SEM_ORANGE, font=ui_font(FONT_BODY), wraplength=WRAP_STAGE_BLOCKED, justify="left").grid(row=1, column=0, sticky="w", padx=10, pady=(0, 4))
        ctk.CTkLabel(
            card,
            text="Usa la barra de acciones superior para completar la etapa requerida y desbloquear esta vista.",
            text_color=TXT_MUTED,
            font=ui_font(FONT_SMALL),
            wraplength=WRAP_STAGE_BLOCKED,
            justify="left",
        ).grid(row=2, column=0, sticky="w", padx=10, pady=(0, 10))

    def _render_eda_view(self, parent: ctk.CTkFrame, *, force_rebuild: bool = False) -> None:
        operational = self.service.get_operational_state()
        state = operational.cutoff
        snapshot = operational.analysis
        signature = (
            snapshot.resolved_target_column,
            snapshot.active_domain_column,
            snapshot.active_domain_filter,
            bool(self.eda_use_capping_var.get()),
            bool(state.dynamic_enabled),
            float(state.dynamic_cutoff_value or 0.0),
        )
        if not force_rebuild and self._rendered_stage_signatures.get("EDA") == signature:
            return
        DashboardGrid.clear(parent)
        self._rendered_stage_signatures["EDA"] = signature
        wrapper = ctk.CTkFrame(parent, fg_color=BG_PANEL)
        wrapper.grid(row=0, column=0, sticky="nsew")
        wrapper.grid_columnconfigure(0, weight=1)
        wrapper.grid_rowconfigure(0, weight=1)
        wrapper.grid_rowconfigure(1, weight=0)

        active_variable = str(state.effective_target_column if self.eda_use_capping_var.get() else self.target_var.get() or state.effective_target_column)
        capping_status = "capping confirmado" if state.dynamic_enabled else "sin capping confirmado"

        try:
            selected_domain_filter = self.domain_filter_var.get().strip()
            data = self.service.prepare_univariate_data(
                max_domain_categories=10,
                use_effective_target=bool(self.eda_use_capping_var.get()),
                domain_filter=selected_domain_filter if selected_domain_filter and selected_domain_filter != "Todos" else None,
            )
        except Exception as exc:
            ctk.CTkLabel(wrapper, text=f"Sin EDA disponible: {exc}", text_color=TXT_MAIN).grid(row=0, column=0, sticky="w", padx=8, pady=8)
            return

        stats_table = dict(self.service.get_target_statistics_table(use_effective_target=bool(self.eda_use_capping_var.get())))
        cv_text = str(stats_table.get("cv", "-"))
        trunc_text = str(stats_table.get("% truncated", "-"))
        skewness_text = str(stats_table.get("skewness", "-"))
        availability = data.get("availability", {})
        diagnostics = data.get("diagnostics", {})

        try:
            cv_ratio = float(stats_table.get("cv", "nan"))
            skewness = float(stats_table.get("skewness", "nan"))
            diagnostic = "Distribución estable."
            if cv_ratio >= 0.50 or abs(skewness) >= 0.75:
                diagnostic = "Sesgo/variabilidad moderados."
            if cv_ratio >= 0.75 or abs(skewness) >= 1.0:
                diagnostic = "Distribución problemática."
        except Exception:
            diagnostic = "Diagnóstico no disponible."

        evidence = ctk.CTkFrame(wrapper, fg_color=BG_PANEL)
        evidence.grid(row=0, column=0, sticky="nsew", padx=1, pady=(0, 0))
        evidence.grid_columnconfigure(0, weight=1)
        evidence.grid_rowconfigure(0, weight=0)
        evidence.grid_rowconfigure(1, weight=1)

        summary = ctk.CTkFrame(evidence, fg_color=BG_PANEL)
        summary.grid(row=0, column=0, sticky="ew", padx=1, pady=(0, 0))
        summary.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(summary, text=f"EDA · {active_variable}", text_color=TXT_MAIN, font=ui_font(FONT_SMALL)).grid(row=0, column=0, sticky="w", padx=2, pady=(0, 0))
        ctk.CTkLabel(
            summary,
            text=f"{snapshot.active_domain_column or 'Sin dominio'} · {snapshot.active_domain_filter or 'Todos'} · {capping_status}",
            text_color=TXT_MUTED,
            font=ui_font(FONT_MICRO),
            wraplength=WRAP_STAGE_SUMMARY,
            justify="left",
        ).grid(row=1, column=0, sticky="w", padx=2, pady=(0, 0))

        plot_card = ctk.CTkFrame(evidence, fg_color=CHART_BG, corner_radius=6, border_width=1, border_color=CHART_BORDER)
        plot_card.grid(row=1, column=0, sticky="nsew", padx=0, pady=(0, 0))
        plot_card.grid_rowconfigure(0, weight=1)
        plot_card.grid_rowconfigure(1, weight=0, minsize=58)
        plot_card.grid_columnconfigure(0, weight=11)
        plot_card.grid_columnconfigure(1, weight=7)

        main_row = ctk.CTkFrame(plot_card, fg_color=CHART_BG)
        main_row.grid(row=0, column=0, columnspan=2, sticky="nsew", padx=0, pady=0)
        main_row.grid_rowconfigure(0, weight=1)
        main_row.grid_columnconfigure(0, weight=11)
        main_row.grid_columnconfigure(1, weight=7)

        left_col = ctk.CTkFrame(main_row, fg_color=CHART_BG)
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 2), pady=0)
        left_col.grid_columnconfigure(0, weight=1)
        left_col.grid_rowconfigure(0, weight=1)

        hist_host = ctk.CTkFrame(left_col, fg_color=CHART_BG)
        hist_host.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        hist_host.grid_rowconfigure(0, weight=1)
        hist_host.grid_columnconfigure(0, weight=1)

        right_col = ctk.CTkFrame(main_row, fg_color=CHART_BG)
        right_col.grid(row=0, column=1, sticky="nsew", padx=(2, 0), pady=0)
        right_col.grid_rowconfigure(0, weight=13)
        right_col.grid_rowconfigure(1, weight=11)
        right_col.grid_columnconfigure(0, weight=1)

        qq_host = ctk.CTkFrame(right_col, fg_color=CHART_BG)
        qq_host.grid(row=0, column=0, sticky="nsew", padx=0, pady=(0, 2))
        qq_host.grid_rowconfigure(0, weight=1)
        qq_host.grid_columnconfigure(0, weight=1)

        box_host = ctk.CTkFrame(right_col, fg_color=CHART_BG)
        box_host.grid(row=1, column=0, sticky="nsew", padx=0, pady=(2, 0))
        box_host.grid_rowconfigure(0, weight=1)
        box_host.grid_columnconfigure(0, weight=1)

        iqr_host = ctk.CTkFrame(plot_card, fg_color=CHART_BG)
        iqr_host.grid(row=1, column=0, columnspan=2, sticky="ew", padx=0, pady=(2, 0))
        iqr_host.configure(height=58)
        iqr_host.grid_propagate(False)
        iqr_host.grid_rowconfigure(0, weight=1)
        iqr_host.grid_columnconfigure(0, weight=1)

        values = [float(v) for v in data["target_values"]]
        original_values: list[float] = values
        cutoff_val: float | None = None
        if self.service.current_dataset is not None and self.service.variable_config is not None:
            base_target = self.service.variable_config.target_column
            if base_target in self.service.current_dataset.dataframe.columns:
                raw_base = self.service.current_dataset.dataframe[base_target].dropna().tolist()
                original_values = [float(v) for v in raw_base if str(v).strip() != ""]
        if state.dynamic_enabled:
            cutoff_val = float(state.dynamic_cutoff_value)

        stage_alert = bool(
            not availability.get("probability", {}).get("available", True)
            or not availability.get("boxplot", {}).get("available", True)
            or "problemática" in diagnostic.lower()
        )
        insight_text = "Insight: mantener distribución actual." if not stage_alert else "Insight: revisar transformación/capping."
        ctk.CTkLabel(
            wrapper,
            text=f"{insight_text} · CV={cv_text} · n={diagnostics.get('target_valid_count', 0)} · no implica independencia espacial.",
            text_color=SEM_ORANGE if stage_alert else SEM_GREEN,
            font=ui_font(FONT_MICRO),
            justify="left",
            anchor="w",
        ).grid(row=1, column=0, sticky="w", padx=4, pady=(1, 0))

        hist_grid = DashboardGrid(hist_host, 1, 1, figsize=(8.6, 5.8), max_aspect_ratio=2.25)
        qq_grid = DashboardGrid(qq_host, 1, 1, figsize=(4.8, 3.2), max_aspect_ratio=1.65)
        box_grid = DashboardGrid(box_host, 1, 1, figsize=(4.8, 3.2), max_aspect_ratio=1.75)
        iqr_grid = DashboardGrid(iqr_host, 1, 1, figsize=(8.0, 0.9), max_aspect_ratio=4.0)
        try:
            self.eda_renderer.render_dashboard(
                histogram_grid=hist_grid,
                qq_grid=qq_grid,
                boxplot_grid=box_grid,
                iqr_grid=iqr_grid,
                data=data,
                context=EDARenderContext(
                    active_variable=active_variable,
                    skewness_text=skewness_text,
                    chart_text_color=CHART_TEXT,
                    chart_legend_size=CHART_FONT_SIZE_LEGEND + 1,
                    chart_label_size=CHART_FONT_SIZE_LABEL + 1,
                ),
                original_values=original_values,
                cutoff_value=cutoff_val,
            )
        except Exception as exc:
            for host in (hist_host, qq_host, box_host, iqr_host):
                DashboardGrid.clear(host)
            ctk.CTkLabel(
                plot_card,
                text=f"No se pudo renderizar el panel EDA ({type(exc).__name__}). Revisa el log técnico.",
                text_color=SEM_ORANGE,
                font=ui_font(FONT_SMALL),
            ).grid(row=0, column=0, columnspan=2, sticky="w", padx=8, pady=8)
            self.service.activity_log.log(
                "eda_render_failed",
                "error",
                "Fallo en render Matplotlib de EDA.",
                {
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "active_variable": active_variable,
                    "domain_filter": str(snapshot.active_domain_filter or "Todos"),
                },
            )
            self._append_activity(f"⚠️ Render EDA falló: {type(exc).__name__}: {exc}")

    def _render_cutoff_view(self, parent: ctk.CTkFrame, *, force_rebuild: bool = False) -> None:
        signature = (
            self.cutoff_target_var.get(),
            self.target_var.get(),
            self.dynamic_mode_var.get(),
            float(self.dynamic_slider_var.get()),
            bool(self.dynamic_cutoff_enabled_var.get()),
        )
        if not force_rebuild and self._rendered_stage_signatures.get("Cutoffs") == signature:
            self._refresh_cutoff_preview()
            return
        DashboardGrid.clear(parent)
        self._rendered_stage_signatures["Cutoffs"] = signature
        wrapper = ctk.CTkFrame(parent, fg_color=BG_PANEL)
        wrapper.grid(row=0, column=0, sticky="nsew")
        snapshot = self.service.get_analysis_context_state()
        ctk.CTkLabel(wrapper, text="Resumen ejecutivo", text_color=TXT_MAIN, font=ui_font(FONT_SUBTITLE)).pack(anchor="w", padx=6, pady=(0, 2))
        ctk.CTkLabel(wrapper, text=f"{_build_visual_context_line(snapshot)} · Ajustes de capping locales en esta vista.", text_color=TXT_MUTED, font=ui_font(FONT_SMALL)).pack(anchor="w", padx=6, pady=(0, 4))
        ctk.CTkLabel(wrapper, text="Microlectura: identifica cuánto porcentaje de muestras y máximos cambia por umbral.", text_color=TXT_MUTED, font=ui_font(FONT_SMALL)).pack(anchor="w", padx=6, pady=(0, 4))
        ctk.CTkLabel(wrapper, text="Detalle técnico", text_color=TXT_MAIN, font=ui_font(FONT_SUBTITLE)).pack(anchor="w", padx=6, pady=(0, 2))

        container = ctk.CTkFrame(wrapper, fg_color=BG_PANEL)
        container.pack(fill="both", expand=True)
        container.grid_columnconfigure(0, weight=0, minsize=440)
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

    def _render_spatial_view(self, parent: ctk.CTkFrame, *, force_rebuild: bool = False) -> None:
        signature = (
            self.spatial_view_mode_var.get(),
            self.spatial_color_var.get(),
            self.domain_filter_var.get(),
            self.service.get_analysis_context_state().active_domain_filter,
        )
        if not force_rebuild and self._rendered_stage_signatures.get("Espacial") == signature:
            return
        DashboardGrid.clear(parent)
        self._rendered_stage_signatures["Espacial"] = signature
        if self.spatial_view_mode_var.get() == "3D":
            self._render_spatial_3d_view(parent)
            return
        if self.spatial_3d_widget is not None and self.spatial_3d_widget.winfo_exists():
            self.spatial_3d_widget.grid_remove()
        self._render_spatial_2d_view(parent)

    def _render_spatial_2d_view(self, parent: ctk.CTkFrame) -> None:
        wrapper = ctk.CTkFrame(parent, fg_color=BG_PANEL)
        wrapper.grid(row=0, column=0, sticky="nsew")
        snapshot = self.service.get_analysis_context_snapshot()
        ctk.CTkLabel(wrapper, text="Resumen ejecutivo", text_color=TXT_MAIN, font=ui_font(FONT_SUBTITLE)).pack(anchor="w", padx=8, pady=(0, 2))
        ctk.CTkLabel(wrapper, text=f"{_build_visual_context_line(snapshot, local_override=self.spatial_color_var.get() or None)}", text_color=TXT_MUTED, font=ui_font(FONT_SMALL)).pack(anchor="w", padx=8, pady=(0, 5))
        ctk.CTkLabel(wrapper, text="Microlectura: continuidad visual estable sugiere dominios y variogramas más robustos.", text_color=TXT_MUTED, font=ui_font(FONT_SMALL)).pack(anchor="w", padx=8, pady=(0, 3))
        ctk.CTkLabel(wrapper, text="Detalle técnico", text_color=TXT_MAIN, font=ui_font(FONT_SUBTITLE)).pack(anchor="w", padx=8, pady=(0, 3))
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
            width_ratios=[1.45, 1.0],
            height_ratios=[1.2, 1.0],
        )
        self.spatial_2d_renderer.render(
            grid,
            spatial,
            Spatial2DRenderContext(
                color_by=color_by,
                snapshot=snapshot,
                guardrail_note=SPATIAL_GUARDRAIL_NOTE,
                info_text_color=TXT_MAIN,
                info_border_color=BORDER_SOFT,
                info_bg_color=BG_CARD,
                label_size=CHART_FONT_SIZE_LABEL,
            ),
        )

    def _render_spatial_3d_view(self, parent: ctk.CTkFrame) -> None:
        wrapper = ctk.CTkFrame(parent, fg_color=BG_PANEL)
        wrapper.grid(row=0, column=0, sticky="nsew")
        wrapper.grid_columnconfigure(0, weight=1)
        wrapper.grid_rowconfigure(1, weight=1)

        snapshot = self.service.get_analysis_context_snapshot()
        ctk.CTkLabel(wrapper, text="Resumen ejecutivo", text_color=TXT_MAIN, font=ui_font(FONT_SUBTITLE)).grid(row=0, column=0, sticky="w", padx=6, pady=(0, 2))
        ctk.CTkLabel(
            wrapper,
            text=f"{_build_visual_context_line(snapshot, local_override=self.spatial_color_var.get() or None)} · Modo 3D PoC",
            text_color=TXT_MUTED,
            font=ui_font(FONT_SMALL),
        ).grid(row=0, column=0, sticky="e", padx=6, pady=(0, 2))

        renderer, fallback_reason = self._select_spatial_3d_renderer()
        if fallback_reason and fallback_reason != self._spatial_3d_renderer_warning_cache:
            self._spatial_3d_renderer_warning_cache = fallback_reason
            self.service.activity_log.log(
                "spatial_3d_backend_fallback",
                "warning",
                "Fallback al renderer 3D Matplotlib.",
                {"reason": fallback_reason},
            )

        self.spatial_3d_widget = renderer.create_widget(wrapper)
        self.spatial_3d_widget.grid(row=1, column=0, sticky="nsew", padx=4, pady=(2, 0))

        available, reason = renderer.is_available()
        if not available:
            renderer.show_unavailable(self.spatial_3d_widget, f"{reason}. Volviendo automáticamente a 2D.")
            self.spatial_view_mode_var.set("2D")
            self.after(10, lambda: self._render_spatial_view(parent, force_rebuild=True))
            return

        color_by = self.spatial_color_var.get() or None
        result = self.service.prepare_visual_3d_data(color_by=color_by)
        if not result.success or result.spatial_3d_data is None:
            renderer.show_unavailable(self.spatial_3d_widget, f"No se pudo renderizar 3D: {result.message}. Volviendo a 2D.")
            self.spatial_view_mode_var.set("2D")
            self.after(10, lambda: self._render_spatial_view(parent, force_rebuild=True))
            return

        renderer.render(
            self.spatial_3d_widget,
            result.spatial_3d_data,
            color_by or snapshot["resolved_target_column"] or "No definido",
        )

    def _select_spatial_3d_renderer(self):
        available, reason = self.pyvista_spatial_3d_renderer.is_available()
        if available:
            return self.pyvista_spatial_3d_renderer, ""
        return self.spatial_3d_renderer, reason

    def _render_domains_view(self, parent: ctk.CTkFrame, *, force_rebuild: bool = False) -> None:
        signature = ("disabled",)
        if not force_rebuild and self._rendered_stage_signatures.get("Dominios") == signature:
            return
        DashboardGrid.clear(parent)
        self._rendered_stage_signatures["Dominios"] = signature
        wrapper = ctk.CTkFrame(parent, fg_color=BG_PANEL)
        wrapper.grid(row=0, column=0, sticky="nsew")
        ctk.CTkLabel(wrapper, text="Módulo temporalmente deshabilitado", text_color=TXT_MAIN, font=ui_font(FONT_SUBTITLE)).grid(row=0, column=0, sticky="w", padx=8, pady=8)

    def _render_variography_view(self, parent: ctk.CTkFrame, *, force_rebuild: bool = False) -> None:
        session = self.service.get_variography_session()
        snapshot = self.service.get_analysis_context_snapshot()
        signature = (
            "live",
            str(session.selected_target),
            str(snapshot.get("active_domain_column", "")),
            str(snapshot.get("active_domain_filter", "")),
            float(session.lag_distance),
            int(session.n_lags),
            float(session.lag_tolerance),
            float(session.max_distance),
            float(session.azimuth),
            float(session.dip),
            float(session.ang_tol_h),
            float(session.ang_tol_v),
            float(session.band_width),
            float(session.band_height),
            str(session.estimator),
            bool(session.compute_dirty),
            bool(session.last_response is not None),
            tuple(session.latest_blocker_codes),
            tuple(session.latest_warning_codes),
        )
        if not force_rebuild and self._rendered_stage_signatures.get("Variografía") == signature:
            return
        DashboardGrid.clear(parent)
        self._rendered_stage_signatures["Variografía"] = signature
        self.variography_stage_view.mount(parent)

    def _on_change_step(self, step_name: str) -> None:
        current_step = self.service.workflow_state.current_step
        if current_step == step_name:
            self._trace_ui_action("cambiar_vista", refresh_type="none", extra={"requested_step": step_name, "reason": "same_step_ignored"})
            return
        self.status_text.set(self.service.set_workflow_step(step_name))
        self.step_label.set(f"Paso actual: {_display_step_name(step_name)}")
        self._append_activity(self.status_text.get())
        self._trace_ui_action("cambiar_vista", refresh_type="dashboard_full", extra={"requested_step": step_name})
        self._render_step(step_name)

    def _render_step(self, step_name: str) -> None:
        readiness = self.service.get_workflow_readiness_state()
        if _should_expand_stage_actions(step_name, readiness):
            self.stage_actions_collapsed = False
            if self.action_bar_toggle_button is not None:
                self.action_bar_toggle_button.configure(text="Ocultar")
            if self.action_bar_body is not None:
                self.action_bar_body.grid()
        self._paint_workflow_state(step_name)
        self._focus_sidebar_sections(step_name)
        self._refresh_dashboard(reason="step_render")

    def _paint_workflow_state(self, active_step: str) -> None:
        ordered = ["Datos", "EDA", "Cutoffs", "Espacial", "Dominios", "Variografía"]
        readiness = self.service.get_workflow_readiness_state()
        active_idx = ordered.index(active_step) if active_step in ordered else 0
        for idx, step in enumerate(ordered):
            button_text = _build_workflow_stage_label(step, active_step, readiness)
            stage_key = STEP_TO_READINESS_KEY.get(step, "")
            stage_state = readiness.stages.get(stage_key, None)
            is_ready = bool(stage_state.ready) if stage_state is not None else False
            has_warning = bool(stage_state.warnings) if stage_state is not None else False
            if idx == active_idx:
                fg_color = WF_WARNING if has_warning else WF_ACTIVE
                border_color = SEM_ORANGE if has_warning else SEM_BLUE_SOFT
                hover_color = BTN_PRIMARY_HOVER
                text_color = SEM_WHITE
            elif idx < active_idx:
                fg_color = WF_WARNING if has_warning else WF_READY
                border_color = SEM_ORANGE if has_warning else BORDER_SOFT
                hover_color = BTN_NEUTRAL_HOVER
                text_color = TEXT_MAIN
            else:
                fg_color = WF_BLOCKED if not is_ready else WF_IDLE
                border_color = SEM_RED if not is_ready else BORDER_SOFT
                hover_color = BTN_NEUTRAL_HOVER
                text_color = TEXT_MUTED if not is_ready else TEXT_MAIN
            self.workflow_buttons[step].configure(
                text=button_text,
                fg_color=fg_color,
                hover_color=hover_color,
                border_color=border_color,
                text_color=text_color,
            )
        self.workflow_hint_var.set(_build_active_step_hint(active_step, self.service.get_operational_state()))

    def _refresh_dashboard(self, *, reason: str = "general", force: bool = False) -> None:
        self._trace_ui_action("refresh_dashboard", refresh_type="dashboard_full", extra={"reason": reason, "force": force})
        self._refresh_context_chips()
        self._sync_eda_capping_state()
        self._refresh_summary_cards()
        current_step = self.service.workflow_state.current_step
        self._apply_kpi_focus(current_step)
        self._render_stage_action_bar(current_step)
        self._show_stage_view(current_step, force_rebuild=force)

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
        state = self.service.get_operational_state()
        if state.cutoff.dynamic_enabled:
            capping_text = f"Capping activo P{state.cutoff.dynamic_percent:.0f}"
        elif state.cutoff.enabled:
            capping_text = "Cutoff manual activo"
        else:
            capping_text = "Capping inactivo"
        self.unified_context_var.set(_build_unified_context_text(state, capping_text))

    def _selector(self, parent: ctk.CTkFrame, label: str, variable: ctk.StringVar, values: list[str], row: int, col: int, key: str | None = None) -> None:
        ctk.CTkLabel(parent, text=label, text_color=TXT_MUTED, font=ui_font(FONT_SMALL)).grid(row=row, column=col, sticky="w", padx=4)
        state = "normal" if values and values[0] else "disabled"
        if values and variable.get() not in values:
            variable.set(values[0])
        menu = ctk.CTkOptionMenu(parent, variable=variable, values=values, state=state, **self._option_menu_style())
        menu.grid(row=row + 1, column=col, sticky="ew", padx=4, pady=(0, 4))
        if key:
            self.column_menus[key] = menu

    def _responsive_figsize(self, base_width: float, base_height: float) -> tuple[float, float]:
        width = max(int(self.view_body.winfo_width()), int(self.content_panel.winfo_width()), 1280)
        height = max(int(self.view_body.winfo_height()), 760)
        if width <= 20 or height <= 20:
            return (base_width, base_height)
        dpi = 100.0
        usable_w = max((width - 42) / dpi, 8.0)
        usable_h = max((height - 34) / dpi, 5.2)
        base_ratio = base_width / max(base_height, 1e-6)
        if usable_w / usable_h > base_ratio:
            usable_w = usable_h * base_ratio
        else:
            usable_h = usable_w / base_ratio
        return (usable_w, usable_h)

    def _get_spatial_color_options(self) -> list[str]:
        target = self.service.get_cutoff_state_typed().effective_target_column or self.target_var.get()
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
            self.domain_assign_button.configure(
                state=assign_state,
                fg_color=BTN_NEUTRAL if assign_state == "normal" else BTN_DISABLED_BG,
                hover_color=BTN_NEUTRAL_HOVER if assign_state == "normal" else BTN_DISABLED_BG,
            )
        if self.domain_apply_button is not None:
            self.domain_apply_button.configure(
                state=apply_state,
                fg_color=BTN_PRIMARY_BG if apply_state == "normal" else BTN_DISABLED_BG,
                hover_color=BTN_PRIMARY_HOVER if apply_state == "normal" else BTN_DISABLED_BG,
            )

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
            self._invalidate_stage_cache()
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
            self._invalidate_stage_cache()
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
        self.dynamic_cutoff_label_var.set("Umbral actual: -")
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
            self._invalidate_stage_cache("Cutoffs")
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
            self.dynamic_cutoff_label_var.set("Umbral actual: -")
            self.dynamic_impact_label_var.set("Impacto: sin datos para preview")
            ctk.CTkLabel(parent, text="Selecciona variable numérica para preview.", text_color=TXT_MAIN).pack(anchor="w", padx=8, pady=8)
            return

        mode = "absolute" if self.dynamic_mode_var.get() == "Valor absoluto" else "percentile"
        try:
            preview = self.service.prepare_dynamic_cutoff_preview(target, mode, float(self.dynamic_slider_var.get()))
        except Exception as exc:
            self.dynamic_cutoff_label_var.set("Umbral actual: -")
            self.dynamic_impact_label_var.set("Impacto: no disponible")
            ctk.CTkLabel(parent, text=f"No se pudo generar preview: {exc}", text_color=TXT_MAIN).pack(anchor="w", padx=8, pady=8)
            return

        cutoff = float(preview["cutoff_value"])
        self.dynamic_percentile_label_var.set(f"Percentil: P{float(self.dynamic_slider_var.get()):.1f}")
        self.dynamic_cutoff_label_var.set(f"Umbral actual: {cutoff:.6g}")
        self.dynamic_impact_label_var.set(
            f"{preview['affected_pct']:.2f}% afectado · {preview['affected_count']} truncadas · Máx {preview['max_original']:.6g} → {preview['max_truncated']:.6g}"
        )

        try:
            chart = DashboardGrid(parent, 2, 2)
            ax_hist = chart.axis(0, 0)
            ax_cdf = chart.axis(1, 0)
            ax_before_after = chart.axis(1, 1)
            ax_prob = chart.axis(0, 1)
            for axis in (ax_hist, ax_cdf, ax_before_after, ax_prob):
                apply_axis_style(axis)

            ax_hist.hist(preview["retained_values"], bins="sturges", color=SEM_GRAY, alpha=0.24, label="Base")
            if preview["truncated_values"]:
                ax_hist.hist(preview["truncated_values"], bins="sturges", color=SEM_BLUE, alpha=0.78, label="Cap")
            add_reference_line(ax_hist, cutoff, label=f"Umbral {cutoff:.3g}", color=SEM_ORANGE, y_pos=0.92)
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

            ax_before_after.boxplot([preview["values"], preview["capped_values"]], tick_labels=["Base", "Cap"], patch_artist=True, showfliers=False, widths=0.55)
            ax_before_after.set_title("Comparación resumen", color=TXT_MUTED)
            chart.render()
        except Exception as exc:
            DashboardGrid.clear(parent)
            ctk.CTkLabel(parent, text=f"No se pudo renderizar el panel de outliers ({type(exc).__name__}).", text_color=SEM_ORANGE).pack(anchor="w", padx=8, pady=8)
            self.service.activity_log.log(
                "cutoff_preview_render_failed",
                "error",
                "Fallo en render Matplotlib de Control de Outliers.",
                {
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "target": target,
                    "mode": mode,
                },
            )
            self._append_activity(f"⚠️ Render Control de Outliers falló: {type(exc).__name__}: {exc}")

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
            self._invalidate_stage_cache()
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
            self._invalidate_stage_cache()
            self._refresh_dashboard(reason="domain_filter_changed")

    def _on_domain_filters_changed(self) -> None:
        filters = {
            "lithology": self.domain_filter_lithology_var.get(),
            "alteration": self.domain_filter_alteration_var.get(),
            "mine": self.domain_filter_mine_var.get(),
        }
        self.service.set_domain_ui_filters(filters)
        self._invalidate_stage_cache("Dominios")
        self._refresh_dashboard(reason="domain_ui_filters_changed")

    def _update_domain_preview_and_history(self, payload: dict[str, object]) -> None:
        filters = payload.get("filters", {})
        filtered_desc = ", ".join(
            [
                f"{label}={value or 'Todos'}"
                for label, value in [
                    ("Litología", str(filters.get("lithology", ""))),
                    ("Alteración", str(filters.get("alteration", ""))),
                    ("Mina", str(filters.get("mine", ""))),
                ]
            ]
        )
        preview_count = int(payload.get("preview_count", 0))
        self.domain_preview_var.set(f"Previsualización: {filtered_desc} · muestras={preview_count}")

        history = payload.get("assignment_history", [])
        if not history:
            self.domain_history_var.set("Sin dominios confirmados.")
            return
        recent = history[-5:]
        lines: list[str] = []
        for event in recent:
            filters_map = event.get("filters", {})
            lines.append(
                f"#{event.get('sequence')} {event.get('domain')} · n={event.get('affected_count')} · "
                f"L={filters_map.get('lithology') or 'Todos'} / A={filters_map.get('alteration') or 'Todos'} / M={filters_map.get('mine') or 'Todos'}"
            )
        self.domain_history_var.set("Confirmados:\n" + "\n".join(lines))

    def _on_confirm_domain_assignment(self) -> None:
        result = self.service.confirm_domain_assignment(self.domain_confirm_var.get())
        self.status_text.set(result.message)
        self._append_activity(result.message)
        if result.success:
            self._invalidate_stage_cache()
            self.domain_label.set("Dominio: domain_estimation")
            self.domain_confirm_var.set("")
            self._refresh_dashboard(reason="domain_assignment_confirmed")

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
            self._invalidate_stage_cache()
            self.domain_label.set("Dominio: domain_estimation")
            self.domain_records_var.set("Selecciona una burbuja para ver índices y resumen del dominio.")
            self._refresh_dashboard(reason="domains_applied")

    def _on_toggle_eda_capping(self) -> None:
        if self.service.workflow_state.current_step != "EDA":
            return
        self._invalidate_stage_cache("EDA")
        self._trace_ui_action("actualizar_eda", refresh_type="dashboard_full", extra={"source": "eda_capping_switch"})
        self._refresh_dashboard(reason="eda_capping_switch")

    def _on_refresh_eda(self) -> None:
        if self.service.workflow_state.current_step != "EDA":
            return
        self._invalidate_stage_cache("EDA")
        self._trace_ui_action("actualizar_eda", refresh_type="dashboard_full", extra={"source": "eda_refresh_button"})
        self._refresh_dashboard(reason="eda_manual_button", force=True)

    def _on_spatial_mode_changed(self, _value: str) -> None:
        if self.service.workflow_state.current_step != "Espacial":
            return
        self._invalidate_stage_cache("Espacial")
        self._refresh_dashboard(reason="spatial_mode_changed", force=True)

    def _on_spatial_color_changed(self) -> None:
        if self.service.workflow_state.current_step != "Espacial":
            return
        self._invalidate_stage_cache("Espacial")
        self._refresh_dashboard(reason="spatial_color_changed", force=True)

    def _refresh_summary_cards(self) -> None:
        stats_table = self.service.get_target_statistics_table(use_effective_target=bool(self.eda_use_capping_var.get()))
        stats_map = {str(k).lower(): str(v) for k, v in stats_table}
        self.kpi_value_vars["valid_count"].set(self._format_kpi_value(stats_map.get("valid_count", stats_map.get("válidos", "-"))))
        self.kpi_value_vars["p90"].set(self._format_kpi_value(stats_map.get("p90", "-")))
        cv_raw = stats_map.get("cv", "-")
        try:
            self.kpi_value_vars["cv"].set(f"{float(str(cv_raw).replace('%', '')) * 100:.2f}%")
        except Exception:
            self.kpi_value_vars["cv"].set(cv_raw)
        state = self.service.get_cutoff_state_typed()
        cutoff_actual = "-"
        trunc_pct = "-"
        if state.dynamic_enabled:
            cutoff_actual = f"{state.dynamic_cutoff_value:.6g}"
            target = str(state.dynamic_target_column or self.target_var.get())
            mode = str(state.dynamic_mode)
            slider = float(state.dynamic_percent)
            try:
                preview = self.service.prepare_dynamic_cutoff_preview(target, mode, slider)
                trunc_pct = f"{preview['affected_pct']:.2f}%"
            except Exception:
                trunc_pct = "-"
        elif state.enabled and state.limits:
            cutoff_actual = ", ".join(f"{float(v):.4g}" for v in state.limits)
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
        state = self.service.get_cutoff_state_typed()
        details: dict[str, object] = {
            "action": action,
            "view": self.service.workflow_state.current_step,
            "target_active": str(state.effective_target_column or self.target_var.get() or ""),
            "capping_confirmed": bool(self.service.has_confirmed_dynamic_capping()),
            "refresh_type": refresh_type,
        }
        if extra:
            details.update(extra)
        self.service.activity_log.log("ui_trace", "info", f"UI acción: {action}", details)
