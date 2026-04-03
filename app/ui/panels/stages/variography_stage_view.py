"""Dedicated Variography stage view for first real experimental workflow slice."""

from __future__ import annotations

import logging
import threading
import customtkinter as ctk

from app.ui.controllers.variography_controller import VariographyController
from app.ui.panels.dashboard_grid import DashboardGrid
from app.ui.renderers import MatplotlibVariographyRenderer, VariographyRenderContext
from app.ui.theme import BG_CARD, BG_PANEL, CHART_FONT_SIZE_LABEL, CHART_FONT_SIZE_LEGEND, CHART_TEXT, SEM_ORANGE, SEM_RED, TEXT_MAIN, TEXT_MUTED

VARIOGRAPHY_CONTROLS_WIDTH = 340
VARIOGRAPHY_TEXT_WRAP = 980
logger = logging.getLogger(__name__)


class VariographyStageView:
    def __init__(self, controller: VariographyController) -> None:
        self.controller = controller
        self.renderer = MatplotlibVariographyRenderer()
        self._session = self.controller.service.get_variography_session()
        self.target_var = ctk.StringVar(value="")
        self.lag_distance_var = ctk.StringVar(value="10.0")
        self.n_lags_var = ctk.StringVar(value="16")
        self.lag_tolerance_var = ctk.StringVar(value="5.0")
        self.max_distance_var = ctk.StringVar(value="160.0")
        self.azimuth_var = ctk.StringVar(value="0.0")
        self.dip_var = ctk.StringVar(value="0.0")
        self.ang_tol_h_var = ctk.StringVar(value="90.0")
        self.ang_tol_v_var = ctk.StringVar(value="90.0")
        self.band_width_var = ctk.StringVar(value="0.0")
        self.band_height_var = ctk.StringVar(value="0.0")
        self.estimator_var = ctk.StringVar(value="classical")
        self.usage_target_var = ctk.StringVar(value="kriging")
        self.nugget_enabled_var = ctk.BooleanVar(value=True)
        self.nugget_value_var = ctk.StringVar(value="0.0")
        self.nugget_locked_var = ctk.BooleanVar(value=False)
        self.fit_method_var = ctk.StringVar(value="manual")
        self.min_pairs_var = ctk.StringVar(value="30")
        self.exclude_lags_var = ctk.StringVar(value="")
        self._structure_rows: list[dict[str, ctk.Variable]] = []
        self._structures_frame: ctk.CTkFrame | None = None
        self.status_var = ctk.StringVar(value="Configura parámetros y ejecuta cálculo experimental.")
        self.warning_var = ctk.StringVar(value="")
        self.blocker_var = ctk.StringVar(value="")
        self.usage_warning_var = ctk.StringVar(value="")
        self.leapfrog_output_var = ctk.StringVar(value="Sin salida para Leapfrog aún. Ejecute variografía para generar parámetros.")
        self.leapfrog_status_var = ctk.StringVar(value="Salida Leapfrog no disponible: falta cálculo variográfico.")
        self._plot_host: ctk.CTkFrame | None = None
        self._compute_button: ctk.CTkButton | None = None
        self._copy_button: ctk.CTkButton | None = None
        self._leapfrog_output_box: ctk.CTkTextbox | None = None
        self._compute_in_progress = False
        self._auto_compute_done = False
        self._auto_compute_context_signature: tuple[object, ...] | None = None
        self._pending_async_error: str = ""
        self._bind_dirty_traces()

    def mount(self, parent: ctk.CTkFrame) -> None:
        snapshot = self.controller.service.get_analysis_context_snapshot()
        context_signature = (
            self.controller.service.current_dataset.file_name if self.controller.service.current_dataset is not None else "",
            str(snapshot.get("resolved_target_column", "")),
            str(snapshot.get("active_domain_column", "")),
            str(snapshot.get("active_domain_filter", "")),
        )
        if self._auto_compute_context_signature != context_signature:
            self._auto_compute_done = False
            self._auto_compute_context_signature = context_signature
        init = self.controller.get_initial_state()
        self.target_var.set(str(init.get("target_col", "")))
        self.lag_distance_var.set(f"{float(init.get('lag_distance', 10.0)):.6g}")
        self.n_lags_var.set(str(int(init.get("n_lags", 16))))
        self.lag_tolerance_var.set(f"{float(init.get('lag_tolerance', 5.0)):.6g}")
        self.max_distance_var.set(f"{float(init.get('max_distance', 160.0)):.6g}")
        self.azimuth_var.set(f"{float(init.get('azimuth', 0.0)):.6g}")
        self.dip_var.set(f"{float(init.get('dip', 0.0)):.6g}")
        self.ang_tol_h_var.set(f"{float(init.get('ang_tol_h', 90.0)):.6g}")
        self.ang_tol_v_var.set(f"{float(init.get('ang_tol_v', 90.0)):.6g}")
        self.band_width_var.set(f"{float(init.get('band_width', 0.0)):.6g}")
        self.band_height_var.set(f"{float(init.get('band_height', 0.0)):.6g}")
        self.estimator_var.set(str(init.get("estimator", "classical")))
        model_init = init.get("model", {}) if isinstance(init.get("model"), dict) else {}
        nugget_init = model_init.get("nugget", {}) if isinstance(model_init.get("nugget"), dict) else {}
        self.usage_target_var.set(str(model_init.get("usage_target", "kriging")))
        self.nugget_enabled_var.set(bool(nugget_init.get("enabled", True)))
        self.nugget_value_var.set(f"{float(nugget_init.get('value', 0.0)):.6g}")
        self.nugget_locked_var.set(bool(nugget_init.get("locked", False)))
        fit_init = model_init.get("fit", {}) if isinstance(model_init.get("fit"), dict) else {}
        self.fit_method_var.set(str(fit_init.get("method", "manual")))
        self.min_pairs_var.set(str(int(fit_init.get("min_pairs", 30))))
        self.exclude_lags_var.set(",".join(str(v) for v in fit_init.get("exclude_lags", [])))
        self._set_structures(model_init.get("structures", []))

        wrapper = ctk.CTkFrame(parent, fg_color=BG_PANEL)
        wrapper.grid(row=0, column=0, sticky="nsew", padx=2, pady=1)
        wrapper.grid_columnconfigure(0, weight=0, minsize=VARIOGRAPHY_CONTROLS_WIDTH)
        wrapper.grid_columnconfigure(1, weight=2)
        wrapper.grid_rowconfigure(0, weight=1)

        controls = ctk.CTkScrollableFrame(
            wrapper,
            fg_color=BG_CARD,
            width=VARIOGRAPHY_CONTROLS_WIDTH,
            corner_radius=8,
            scrollbar_button_color=BG_PANEL,
            scrollbar_button_hover_color=BG_PANEL,
        )
        controls.grid(row=0, column=0, sticky="nsw", padx=(0, 5), pady=0)
        self._build_controls(controls, [str(v) for v in init.get("target_options", [])])

        results = ctk.CTkFrame(wrapper, fg_color=BG_PANEL)
        results.grid(row=0, column=1, sticky="nsew", padx=(1, 0))
        results.grid_columnconfigure(0, weight=1)
        results.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(results, text="Variografía experimental", text_color=TEXT_MAIN, font=ctk.CTkFont(size=15, weight="bold")).grid(row=0, column=0, sticky="w", pady=(0, 2))
        ctk.CTkLabel(results, textvariable=self.status_var, text_color=TEXT_MUTED, justify="left", wraplength=VARIOGRAPHY_TEXT_WRAP).grid(row=1, column=0, sticky="w", pady=(0, 4))

        self._plot_host = ctk.CTkFrame(results, fg_color=BG_CARD)
        self._plot_host.grid(row=2, column=0, sticky="nsew")
        self._render_empty_plot()
        if self._pending_async_error:
            self._render_plot_feedback(
                title="Error de actualización UI",
                message=self._pending_async_error,
                suggestion="Vuelva a abrir la etapa Variografía o recalcule manualmente.",
                severity="error",
            )
            self._pending_async_error = ""

        alerts = ctk.CTkFrame(results, fg_color="transparent")
        alerts.grid(row=3, column=0, sticky="ew", pady=(4, 0))
        ctk.CTkLabel(alerts, textvariable=self.warning_var, text_color=SEM_ORANGE, justify="left", wraplength=VARIOGRAPHY_TEXT_WRAP).pack(anchor="w")
        ctk.CTkLabel(alerts, textvariable=self.usage_warning_var, text_color=SEM_ORANGE, justify="left", wraplength=VARIOGRAPHY_TEXT_WRAP).pack(anchor="w")
        ctk.CTkLabel(alerts, textvariable=self.blocker_var, text_color=SEM_RED, justify="left", wraplength=VARIOGRAPHY_TEXT_WRAP).pack(anchor="w")
        self._build_leapfrog_export_panel(results)

        cached = self._session.last_response
        if cached is not None and cached.result is not None:
            self.status_var.set(str(cached.message))
            self.warning_var.set(self._join_sorted_issue_lines(cached.warnings))
            self.blocker_var.set(self._join_sorted_issue_lines(cached.blockers))
            result_payload = {
                "lag_centers": cached.result.lag_centers,
                "gamma_values": cached.result.gamma_values,
                "pair_counts": cached.result.pair_counts,
                "source_points": cached.result.source_points,
                "used_points": cached.result.used_points,
                "downsampled": cached.result.downsampled,
                "metadata": cached.result.metadata,
            }
            self._update_leapfrog_from_result(result_payload, bool(cached.ok))
            self._render_result_plot(result_payload, bool(cached.ok))
            return

        if self._is_ready_for_compute() and not self._auto_compute_done:
            self._auto_compute_done = True
            parent.after(60, self._on_compute)
            return
        self._render_empty_plot("Sin cálculo aún. Presione 'Calcular'.")

    def _build_controls(self, parent: ctk.CTkFrame | ctk.CTkScrollableFrame, target_options: list[str]) -> None:
        parent.grid_columnconfigure(0, weight=1)
        row = 0
        ctk.CTkLabel(parent, text="A) Variograma experimental", text_color=TEXT_MAIN, font=ctk.CTkFont(size=13, weight="bold")).grid(row=row, column=0, sticky="w", padx=8, pady=(6, 1))
        row += 1
        ctk.CTkLabel(parent, text="Configura lags, tolerancias, direcciones y npairs mínimos.", text_color=TEXT_MUTED, wraplength=318, justify="left").grid(row=row, column=0, sticky="w", padx=8, pady=(0, 3))
        row += 1

        ctk.CTkLabel(parent, text="Variable objetivo", text_color=TEXT_MAIN).grid(row=row, column=0, sticky="w", padx=8, pady=(1, 1))
        row += 1
        ctk.CTkOptionMenu(parent, variable=self.target_var, values=target_options or [""], state="normal" if target_options else "disabled").grid(row=row, column=0, sticky="ew", padx=8, pady=(0, 3))
        row += 1

        ctk.CTkLabel(parent, text="Estimator", text_color=TEXT_MAIN).grid(row=row, column=0, sticky="w", padx=8, pady=(1, 1))
        row += 1
        ctk.CTkOptionMenu(parent, variable=self.estimator_var, values=["classical", "cressie_hawkins"]).grid(row=row, column=0, sticky="ew", padx=8, pady=(0, 3))
        row += 1

        core_grid = ctk.CTkFrame(parent, fg_color="transparent")
        core_grid.grid(row=row, column=0, sticky="ew", padx=8, pady=(1, 3))
        core_grid.grid_columnconfigure((0, 1), weight=1)
        core_fields: list[tuple[str, ctk.StringVar]] = [
            ("lag_distance", self.lag_distance_var),
            ("n_lags", self.n_lags_var),
            ("lag_tolerance", self.lag_tolerance_var),
            ("max_distance", self.max_distance_var),
        ]
        for idx, (label, var) in enumerate(core_fields):
            self._build_compact_field(core_grid, row=idx // 2, col=idx % 2, label=label, var=var)
        row += 1

        directional_card = ctk.CTkFrame(parent, fg_color=BG_PANEL)
        directional_card.grid(row=row, column=0, sticky="ew", padx=8, pady=(1, 3))
        directional_card.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkLabel(
            directional_card,
            text="Direccionalidad real",
            text_color=TEXT_MUTED,
            font=ctk.CTkFont(size=11, weight="bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=6, pady=(4, 1))
        ctk.CTkLabel(
            directional_card,
            text="Direccional (pendiente backend) superado: direccionalidad aplicada al cálculo experimental de pares. Nota: tolerancias amplias no sustituyen análisis omnidireccional riguroso.",
            text_color=TEXT_MUTED,
            wraplength=318,
            justify="left",
        ).grid(row=1, column=0, columnspan=2, sticky="w", padx=6, pady=(0, 3))
        directional_fields: list[tuple[str, ctk.StringVar]] = [
            ("azimuth", self.azimuth_var),
            ("dip", self.dip_var),
            ("ang_tol_h", self.ang_tol_h_var),
            ("ang_tol_v", self.ang_tol_v_var),
            ("band_width", self.band_width_var),
            ("band_height", self.band_height_var),
        ]
        for idx, (label, var) in enumerate(directional_fields):
            self._build_compact_field(directional_card, row=2 + (idx // 2), col=idx % 2, label=label, var=var, state="normal")
        row += 1

        ctk.CTkLabel(parent, text="B) Modelado variográfico", text_color=TEXT_MAIN, font=ctk.CTkFont(size=13, weight="bold")).grid(row=row, column=0, sticky="w", padx=8, pady=(8, 1))
        row += 1
        model_card = ctk.CTkFrame(parent, fg_color=BG_PANEL)
        model_card.grid(row=row, column=0, sticky="ew", padx=8, pady=(1, 3))
        model_card.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkLabel(model_card, text="Objetivo final", text_color=TEXT_MAIN).grid(row=0, column=0, sticky="w", padx=6, pady=(4, 1))
        ctk.CTkOptionMenu(model_card, variable=self.usage_target_var, values=["kriging", "simulation"]).grid(row=0, column=1, sticky="ew", padx=6, pady=(4, 1))
        ctk.CTkCheckBox(model_card, text="Activar nugget c0", variable=self.nugget_enabled_var).grid(row=1, column=0, sticky="w", padx=6, pady=(2, 1))
        ctk.CTkCheckBox(model_card, text="Nugget fijo (locked)", variable=self.nugget_locked_var).grid(row=1, column=1, sticky="w", padx=6, pady=(2, 1))
        ctk.CTkLabel(model_card, text="Valor nugget", text_color=TEXT_MUTED).grid(row=2, column=0, sticky="w", padx=6, pady=(1, 1))
        ctk.CTkEntry(model_card, textvariable=self.nugget_value_var, width=120).grid(row=2, column=1, sticky="ew", padx=6, pady=(1, 1))
        ctk.CTkLabel(model_card, text="Ajuste", text_color=TEXT_MUTED).grid(row=3, column=0, sticky="w", padx=6, pady=(1, 1))
        ctk.CTkOptionMenu(model_card, variable=self.fit_method_var, values=["manual", "WLS"]).grid(row=3, column=1, sticky="ew", padx=6, pady=(1, 1))
        ctk.CTkLabel(model_card, text="min npairs", text_color=TEXT_MUTED).grid(row=4, column=0, sticky="w", padx=6, pady=(1, 1))
        ctk.CTkEntry(model_card, textvariable=self.min_pairs_var, width=120).grid(row=4, column=1, sticky="ew", padx=6, pady=(1, 1))
        ctk.CTkLabel(model_card, text="Excluir lags (1,2...)", text_color=TEXT_MUTED).grid(row=5, column=0, sticky="w", padx=6, pady=(1, 3))
        ctk.CTkEntry(model_card, textvariable=self.exclude_lags_var, width=120).grid(row=5, column=1, sticky="ew", padx=6, pady=(1, 3))
        row += 1
        self._structures_frame = ctk.CTkFrame(parent, fg_color=BG_PANEL)
        self._structures_frame.grid(row=row, column=0, sticky="ew", padx=8, pady=(1, 3))
        row += 1
        self._render_structures_table()

        self._compute_button = ctk.CTkButton(parent, text="Ejecutar variografía", command=self._on_compute, height=30)
        self._compute_button.grid(row=row, column=0, sticky="ew", padx=8, pady=(6, 6))

    def _build_leapfrog_export_panel(self, parent: ctk.CTkFrame) -> None:
        card = ctk.CTkFrame(parent, fg_color=BG_CARD)
        card.grid(row=4, column=0, sticky="ew", pady=(8, 0))
        card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(card, text="Salida para Leapfrog", text_color=TEXT_MAIN, font=ctk.CTkFont(size=13, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=8, pady=(8, 2)
        )
        ctk.CTkLabel(card, textvariable=self.leapfrog_status_var, text_color=TEXT_MUTED, justify="left", wraplength=VARIOGRAPHY_TEXT_WRAP).grid(
            row=1, column=0, sticky="w", padx=8, pady=(0, 4)
        )
        self._leapfrog_output_box = ctk.CTkTextbox(card, height=170, font=ctk.CTkFont(family="Courier", size=12))
        self._leapfrog_output_box.grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 6))
        self._copy_button = ctk.CTkButton(card, text="Copiar parámetros", command=self._on_copy_leapfrog_output, height=28)
        self._copy_button.grid(row=3, column=0, sticky="e", padx=8, pady=(0, 8))
        self._refresh_leapfrog_output_box()
        self._set_copy_button_enabled(bool(self.leapfrog_output_var.get().strip()))

    def _build_compact_field(self, parent: ctk.CTkFrame, *, row: int, col: int, label: str, var: ctk.StringVar, state: str = "normal") -> None:
        parent.grid_columnconfigure(col, weight=1)
        cell = ctk.CTkFrame(parent, fg_color="transparent")
        cell.grid(row=row, column=col, sticky="ew", padx=3, pady=1)
        cell.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(cell, text=label, text_color=TEXT_MUTED, anchor="w", justify="left").grid(row=0, column=0, sticky="w", pady=(0, 1))
        ctk.CTkEntry(cell, textvariable=var, state=state, width=124, height=30).grid(row=1, column=0, sticky="ew")

    def _set_structures(self, structures: object) -> None:
        self._structure_rows = []
        if isinstance(structures, list):
            for item in structures:
                if not isinstance(item, dict):
                    continue
                self._structure_rows.append(
                    {
                        "active": ctk.BooleanVar(value=bool(item.get("active", True))),
                        "type": ctk.StringVar(value=str(item.get("type", "spherical"))),
                        "contribution": ctk.StringVar(value=f"{float(item.get('contribution', 0.5)):.6g}"),
                        "range_major": ctk.StringVar(value=f"{float(item.get('range_major', 120.0)):.6g}"),
                        "range_minor": ctk.StringVar(value=f"{float(item.get('range_minor', 80.0)):.6g}"),
                        "range_vertical": ctk.StringVar(value=f"{float(item.get('range_vertical', 40.0)):.6g}"),
                        "azimuth": ctk.StringVar(value=f"{float(item.get('azimuth', 0.0)):.6g}"),
                        "dip": ctk.StringVar(value=f"{float(item.get('dip', 0.0)):.6g}"),
                        "lock_contribution": ctk.BooleanVar(value=bool(item.get("lock_contribution", False))),
                        "lock_range": ctk.BooleanVar(value=bool(item.get("lock_range", False))),
                    }
                )
        if not self._structure_rows:
            self._set_structures([{}])

    def _render_structures_table(self) -> None:
        if self._structures_frame is None:
            return
        DashboardGrid.clear(self._structures_frame)
        header = ctk.CTkLabel(self._structures_frame, text="Estructuras anidadas", text_color=TEXT_MAIN, font=ctk.CTkFont(size=12, weight="bold"))
        header.grid(row=0, column=0, sticky="w", padx=6, pady=(4, 2))
        btns = ctk.CTkFrame(self._structures_frame, fg_color="transparent")
        btns.grid(row=0, column=1, sticky="e", padx=6, pady=(4, 2))
        ctk.CTkButton(btns, text="+", width=30, command=lambda: self._mutate_structure("add", -1)).pack(side="left", padx=2)
        for idx, row_vars in enumerate(self._structure_rows):
            row = idx + 1
            line = ctk.CTkFrame(self._structures_frame, fg_color="transparent")
            line.grid(row=row, column=0, columnspan=2, sticky="ew", padx=4, pady=1)
            for col in range(10):
                line.grid_columnconfigure(col, weight=1)
            ctk.CTkCheckBox(line, text="", width=20, variable=row_vars["active"]).grid(row=0, column=0, padx=1)
            ctk.CTkOptionMenu(line, variable=row_vars["type"], values=["spherical", "exponential", "gaussian", "linear"], width=98).grid(row=0, column=1, padx=1)
            for col, key in enumerate(["contribution", "range_major", "range_minor", "range_vertical", "azimuth", "dip"], start=2):
                ctk.CTkEntry(line, textvariable=row_vars[key], width=62, height=28).grid(row=0, column=col, padx=1)
            locks = ctk.CTkFrame(line, fg_color="transparent")
            locks.grid(row=0, column=8, padx=1)
            ctk.CTkCheckBox(locks, text="Lc", width=24, variable=row_vars["lock_contribution"]).pack(side="left", padx=1)
            ctk.CTkCheckBox(locks, text="Lr", width=24, variable=row_vars["lock_range"]).pack(side="left", padx=1)
            ops = ctk.CTkFrame(line, fg_color="transparent")
            ops.grid(row=0, column=9, padx=1)
            ctk.CTkButton(ops, text="D", width=24, command=lambda i=idx: self._mutate_structure("dup", i)).pack(side="left", padx=1)
            ctk.CTkButton(ops, text="-", width=24, command=lambda i=idx: self._mutate_structure("del", i)).pack(side="left", padx=1)

    def _mutate_structure(self, action: str, idx: int) -> None:
        current_structs = [self._collect_structure_dict(v) for v in self._structure_rows]
        if action == "add":
            current_structs.append({})
            self._set_structures(current_structs)
        elif action == "dup" and 0 <= idx < len(current_structs):
            current_structs.insert(idx + 1, dict(current_structs[idx]))
            self._set_structures(current_structs)
        elif action == "del" and len(self._structure_rows) > 1 and 0 <= idx < len(self._structure_rows):
            current_structs.pop(idx)
            self._set_structures(current_structs)
        self._render_structures_table()

    def _collect_structure_dict(self, row_vars: dict[str, ctk.Variable]) -> dict[str, object]:
        return {
            "active": bool(row_vars["active"].get()),
            "type": str(row_vars["type"].get()),
            "contribution": self._parse_float(str(row_vars["contribution"].get())),
            "range_major": self._parse_float(str(row_vars["range_major"].get())),
            "range_minor": self._parse_float(str(row_vars["range_minor"].get())),
            "range_vertical": self._parse_float(str(row_vars["range_vertical"].get())),
            "azimuth": self._parse_float(str(row_vars["azimuth"].get())),
            "dip": self._parse_float(str(row_vars["dip"].get())),
            "lock_contribution": bool(row_vars["lock_contribution"].get()),
            "lock_range": bool(row_vars["lock_range"].get()),
        }

    def _bind_dirty_traces(self) -> None:
        observed = [
            self.target_var,
            self.lag_distance_var,
            self.n_lags_var,
            self.lag_tolerance_var,
            self.max_distance_var,
            self.azimuth_var,
            self.dip_var,
            self.ang_tol_h_var,
            self.ang_tol_v_var,
            self.band_width_var,
            self.band_height_var,
            self.estimator_var,
            self.usage_target_var,
            self.nugget_value_var,
            self.fit_method_var,
            self.min_pairs_var,
            self.exclude_lags_var,
            self.nugget_enabled_var,
            self.nugget_locked_var,
        ]
        for var in observed:
            var.trace_add("write", self._on_any_param_changed)

    def _on_any_param_changed(self, *_args) -> None:
        self.controller.mark_dirty(self.target_var.get().strip())
        if self.blocker_var.get():
            self.status_var.set("Parámetros modificados. Recalcula para validar estado.")

    def _on_compute(self) -> None:
        if self._compute_in_progress:
            self.status_var.set("Ya hay un cálculo en progreso. Espera a que termine.")
            return
        self._set_compute_busy(True)
        self.status_var.set("Calculando variograma experimental...")
        try:
            ui_state = {
                "target_col": self.target_var.get().strip(),
                "lag_distance": self._parse_float(self.lag_distance_var.get()),
                "n_lags": self._parse_int(self.n_lags_var.get()),
                "lag_tolerance": self._parse_float(self.lag_tolerance_var.get()),
                "max_distance": self._parse_float(self.max_distance_var.get()),
                "azimuth": self._parse_float(self.azimuth_var.get()),
                "dip": self._parse_float(self.dip_var.get()),
                "ang_tol_h": self._parse_float(self.ang_tol_h_var.get()),
                "ang_tol_v": self._parse_float(self.ang_tol_v_var.get()),
                "band_width": self._parse_float(self.band_width_var.get()),
                "band_height": self._parse_float(self.band_height_var.get()),
                "estimator": self.estimator_var.get().strip() or "classical",
                "model": {
                    "usage_target": self.usage_target_var.get().strip() or "kriging",
                    "nugget": {
                        "enabled": bool(self.nugget_enabled_var.get()),
                        "value": self._parse_float(self.nugget_value_var.get()),
                        "locked": bool(self.nugget_locked_var.get()),
                    },
                    "structures": [self._collect_structure_dict(row) for row in self._structure_rows],
                    "fit": {
                        "method": self.fit_method_var.get().strip() or "manual",
                        "min_pairs": self._parse_int(self.min_pairs_var.get()),
                        "exclude_lags": [int(v.strip()) for v in self.exclude_lags_var.get().split(",") if v.strip()],
                    },
                },
            }
        except Exception as exc:
            self.warning_var.set("")
            self.blocker_var.set(f"[INVALID_INPUT_FORMAT] Revisa el formato numérico de parámetros: {exc}")
            self.status_var.set("No se pudo iniciar cálculo por parámetros inválidos.")
            self._render_empty_plot(message="Sin cálculo: formato inválido en parámetros.")
            self._set_compute_busy(False)
            return

        def _worker() -> None:
            try:
                response = self.controller.compute(ui_state)
            except Exception as exc:  # defensive fallback for background execution
                logger.exception("Variography compute thread failure.")
                response = {
                    "ok": False,
                    "message": f"No se pudo calcular variograma experimental: {exc}",
                    "warnings": [],
                    "blockers": [{"code": "COMPUTE_THREAD_ERROR", "message": str(exc)}],
                    "result": None,
                }
            host = self._plot_host
            if host is not None:
                try:
                    host.after(0, lambda: self._on_compute_finished(response))
                    return
                except Exception as exc:
                    logger.exception("Variography marshal thread->UI failed.")
                    self._pending_async_error = f"No se pudo enviar el resultado al hilo UI: {exc}"
            if self._compute_in_progress:
                self._compute_in_progress = False

        threading.Thread(target=_worker, daemon=True).start()

    def _on_compute_finished(self, response: dict[str, object]) -> None:
        try:
            self.status_var.set(str(response.get("message", "")))
            self.warning_var.set(self._join_sorted_issue_lines(response.get("warnings", [])))
            self.blocker_var.set(self._join_sorted_issue_lines(response.get("blockers", [])))
            result = response.get("result")
            if not isinstance(result, dict):
                self.usage_warning_var.set("")
                self._set_leapfrog_output(
                    text="Sin salida para Leapfrog: el cálculo no devolvió resultado utilizable.",
                    status="Salida Leapfrog no disponible: resultado variográfico no renderizable.",
                )
                self._render_compute_failure_panel(response)
                return
            model_meta = result.get("metadata", {}).get("model", []) if isinstance(result.get("metadata", {}), dict) else {}
            usage_warnings = model_meta.get("usage_warnings", []) if isinstance(model_meta, dict) else []
            self.usage_warning_var.set(
                "\n".join([f"[USAGE] {str(item)}" for item in usage_warnings]) if isinstance(usage_warnings, list) and usage_warnings else ""
            )
            self._update_leapfrog_from_result(result, bool(response.get("ok", False)))
            self._render_result_plot(result, bool(response.get("ok", False)))
            logger.info(
                "Variography UI render success | ok=%s lag_len=%s gamma_len=%s pair_len=%s",
                bool(response.get("ok", False)),
                len(result.get("lag_centers", []) or []),
                len(result.get("gamma_values", []) or []),
                len(result.get("pair_counts", []) or []),
            )
        finally:
            self._set_compute_busy(False)

    def _set_compute_busy(self, busy: bool) -> None:
        self._compute_in_progress = bool(busy)
        if self._compute_button is None:
            return
        self._compute_button.configure(state="disabled" if busy else "normal")
        self._set_copy_button_enabled((not busy) and bool(self.leapfrog_output_var.get().strip()))

    def _render_empty_plot(self, message: str = "Sin cálculo aún.") -> None:
        if self._plot_host is None:
            return
        if not str(message or "").strip():
            message = self._default_empty_message()
        DashboardGrid.clear(self._plot_host)
        self._render_text_center(message)

    def _render_result_plot(self, result: dict[str, object], ok: bool) -> None:
        if self._plot_host is None:
            return
        try:
            if result is None:
                raise ValueError("Resultado de variografía es None")
            lag_values = result.get("lag_centers", result.get("lags", []))
            gamma_values = result.get("gamma_values", result.get("gamma", []))
            pair_counts = result.get("pair_counts", result.get("npairs", []))
            if not isinstance(lag_values, list) or not isinstance(gamma_values, list) or not isinstance(pair_counts, list):
                raise ValueError("Contrato inválido de resultado variográfico (lags/gamma/npairs).")
            if not lag_values or not gamma_values:
                raise ValueError("Resultado variográfico sin datos de lags/gamma.")
            DashboardGrid.clear(self._plot_host)
            grid = DashboardGrid(self._plot_host, 2, 2, figsize=(15.2, 8.2), width_ratios=[1.7, 1.0], height_ratios=[1.0, 1.0])
            info = "Resultado válido para lectura experimental." if ok else "Resultado generado con bloqueos de calidad."
            self.renderer.render(
                grid,
                result,
                VariographyRenderContext(
                    target_label=self.target_var.get() or "target",
                    info_text=info,
                    chart_text_color=CHART_TEXT,
                    chart_label_size=CHART_FONT_SIZE_LABEL,
                    chart_legend_size=CHART_FONT_SIZE_LEGEND,
                ),
            )
            if ok:
                self.status_var.set(f"{self.status_var.get()} · Estado: listo para análisis.")
            else:
                self.status_var.set(f"{self.status_var.get()} · Estado: revisar bloqueos antes de usar resultados.")
        except Exception as exc:
            logger.exception("Variography renderer failure.")
            self._render_plot_feedback(
                title="Error al renderizar variograma",
                message=str(exc),
                suggestion="Recalcule ajustando max_distance o n_lags.",
                severity="error",
            )

    @staticmethod
    def _parse_float(value: str) -> float:
        normalized = str(value).strip().replace(",", ".")
        return float(normalized)

    @staticmethod
    def _parse_int(value: str) -> int:
        return int(float(str(value).strip()))

    def _is_ready_for_compute(self) -> bool:
        snapshot = self.controller.service.get_analysis_context_snapshot()
        if str(snapshot.get("readiness", "")) == "blocked":
            return False
        target = str(snapshot.get("resolved_target_column", "")).strip()
        if not target:
            return False
        data = self.controller.service._get_filtered_dataframe(snapshot)
        if data is None or len(data) < 30:
            return False
        return bool(target in data.columns)

    def _default_empty_message(self) -> str:
        snapshot = self.controller.service.get_analysis_context_snapshot()
        if self.controller.service.current_dataset is None:
            return "Debe cargar un dataset."
        target = str(snapshot.get("resolved_target_column", "")).strip()
        if not target:
            return "Debe seleccionar variable objetivo."
        data = self.controller.service._get_filtered_dataframe(snapshot)
        if data is None or len(data) < 30:
            return "Datos insuficientes para variografía (<30 muestras)."
        return "Sin cálculo aún. Presione 'Calcular'."

    def _render_text_center(self, message: str) -> None:
        if self._plot_host is None:
            return
        ctk.CTkLabel(self._plot_host, text=message, text_color=TEXT_MUTED, justify="center").pack(fill="both", expand=True, padx=8, pady=8)

    def _render_compute_failure_panel(self, response: dict[str, object]) -> None:
        blockers = response.get("blockers", []) if isinstance(response.get("blockers", []), list) else []
        blocker_code = "NO_RENDERABLE_RESULT"
        blocker_message = str(response.get("message", "Sin resultado renderizable."))
        if blockers:
            first = blockers[0] if isinstance(blockers[0], dict) else {}
            blocker_code = str(first.get("code", blocker_code))
            blocker_message = str(first.get("message", blocker_message))
        metadata = response.get("metadata", {}) if isinstance(response.get("metadata", {}), dict) else {}
        recommended_max_distance = metadata.get("recommended_max_distance", "-")
        recommended_lag_distance = metadata.get("recommended_lag_distance", "-")
        effective_rows = metadata.get("effective_rows", "-")
        suggestion = "Ajuste max_distance y recalcule."
        if blocker_code == "NO_PAIRS_IN_RANGE":
            suggestion = f"Sin pares en rango. Sugerencia: max_distance≈{recommended_max_distance}, lag_distance≈{recommended_lag_distance}."
        elif blocker_code in {"INVALID_LAG_DISTANCE", "INVALID_N_LAGS", "INVALID_MAX_DISTANCE", "MAX_DISTANCE_TOO_SMALL"}:
            suggestion = "Revise parámetros de lag (distancia >0 y max_distance > lag_distance)."
        elif blocker_code in {"INSUFFICIENT_LAG_COVERAGE", "NO_ACTIVE_ROWS"}:
            suggestion = f"Datos activos insuficientes ({effective_rows} filas). Ajuste filtro de dominio o parámetros."
        self._render_plot_feedback(
            title=f"Variografía no renderizable [{blocker_code}]",
            message=blocker_message,
            suggestion=suggestion,
            severity="warning",
        )
        if self.leapfrog_status_var.get().strip():
            self.status_var.set(f"{self.status_var.get()} · {self.leapfrog_status_var.get()}")
        logger.info("Variography UI fallback panel | blocker=%s message=%s", blocker_code, blocker_message)

    def _render_plot_feedback(self, *, title: str, message: str, suggestion: str, severity: str = "warning") -> None:
        if self._plot_host is None:
            return
        DashboardGrid.clear(self._plot_host)
        container = ctk.CTkFrame(self._plot_host, fg_color=BG_CARD)
        container.pack(fill="both", expand=True, padx=8, pady=8)
        color = SEM_RED if severity == "error" else SEM_ORANGE
        ctk.CTkLabel(container, text=title, text_color=color, font=ctk.CTkFont(size=14, weight="bold"), justify="left").pack(anchor="w", padx=12, pady=(12, 6))
        ctk.CTkLabel(container, text=message, text_color=TEXT_MAIN, justify="left", wraplength=VARIOGRAPHY_TEXT_WRAP).pack(anchor="w", padx=12, pady=(0, 6))
        ctk.CTkLabel(container, text=suggestion, text_color=TEXT_MUTED, justify="left", wraplength=VARIOGRAPHY_TEXT_WRAP).pack(anchor="w", padx=12, pady=(0, 12))

    def _join_sorted_issue_lines(self, issues: object) -> str:
        if not isinstance(issues, list):
            return ""
        normalized: list[tuple[str, str]] = []
        for item in issues:
            if isinstance(item, dict):
                code = str(item.get("code", "")).strip()
                message = str(item.get("message", "")).strip()
            else:
                code = str(getattr(item, "code", "")).strip()
                message = str(getattr(item, "message", "")).strip()
            if code or message:
                normalized.append((code, message))
        normalized.sort(key=lambda x: (x[0], x[1]))
        return "\n".join([f"[{code}] {message}" if code else message for code, message in normalized])

    def _update_leapfrog_from_result(self, result: dict[str, object], ok: bool) -> None:
        metadata = result.get("metadata", {}) if isinstance(result.get("metadata", {}), dict) else {}
        model = metadata.get("model", {}) if isinstance(metadata.get("model", {}), dict) else {}
        direction_applied = bool(metadata.get("direction_applied", False))
        text, status = self._build_leapfrog_text(model, direction_applied=direction_applied, ok=ok)
        self._set_leapfrog_output(text=text, status=status)
        current_status = str(self.status_var.get()).strip()
        if current_status:
            self.status_var.set(f"{current_status} · {status}")
        else:
            self.status_var.set(status)

    def _build_leapfrog_text(self, model: dict[str, object], *, direction_applied: bool, ok: bool) -> tuple[str, str]:
        nugget_obj = model.get("nugget", {}) if isinstance(model.get("nugget", {}), dict) else {}
        nugget_val = self._as_float_or_none(nugget_obj.get("value"))
        sill_val = self._as_float_or_none(model.get("sill"))
        structures = model.get("structures", []) if isinstance(model.get("structures", []), list) else []
        active_structures = [s for s in structures if isinstance(s, dict) and bool(s.get("active", True))]
        selected = sorted(
            active_structures,
            key=lambda s: float(s.get("contribution", 0.0) or 0.0),
            reverse=True,
        )[0] if active_structures else None
        major_range = self._as_float_or_none(selected.get("range_major")) if isinstance(selected, dict) else None
        semi_range = self._as_float_or_none(selected.get("range_minor")) if isinstance(selected, dict) else None
        minor_range = self._as_float_or_none(selected.get("range_vertical")) if isinstance(selected, dict) else None
        structure_type = str(selected.get("type", "Pendiente")) if isinstance(selected, dict) else "Pendiente"
        contribution = self._as_float_or_none(selected.get("contribution")) if isinstance(selected, dict) else None
        azimuth = self._fmt_numeric(selected.get("azimuth")) if direction_applied and isinstance(selected, dict) else "Pendiente"
        dip = self._fmt_numeric(selected.get("dip")) if direction_applied and isinstance(selected, dict) else "Pendiente"
        lines = [
            "Major:",
            f"Azimuth: {azimuth}",
            f"Dip: {dip}",
            f"Range: {self._fmt_numeric(major_range)}",
            "",
            "Semi-major:",
            f"Azimuth: {azimuth}",
            f"Dip: {dip}",
            f"Range: {self._fmt_numeric(semi_range)}",
            "",
            "Minor:",
            f"Azimuth: {azimuth}",
            f"Dip: {dip}",
            f"Range: {self._fmt_numeric(minor_range)}",
            "",
            f"Structure type: {structure_type if structure_type else 'Pendiente'}",
            f"Contribution: {self._fmt_numeric(contribution)}",
            f"Nugget: {self._fmt_numeric(nugget_val)}",
            f"Sill: {self._fmt_numeric(sill_val)}",
        ]
        have_global = nugget_val is not None or sill_val is not None
        have_structure = isinstance(selected, dict)
        if have_global and have_structure and direction_applied and ok:
            status = "Salida Leapfrog utilizable: parámetros globales y estructura principal disponibles."
        elif have_global and have_structure:
            status = "Salida parcial disponible: estructura principal y parámetros globales; direccionalidad pendiente."
        elif have_global:
            status = "Solo parámetros globales disponibles para Leapfrog (sin estructura activa)."
        else:
            status = "Salida Leapfrog pendiente: faltan nugget/sill del resultado variográfico."
        return "\n".join(lines), status

    def _set_leapfrog_output(self, *, text: str, status: str) -> None:
        self.leapfrog_output_var.set(text)
        self.leapfrog_status_var.set(status)
        self._refresh_leapfrog_output_box()
        self._set_copy_button_enabled(bool(text.strip()))

    def _refresh_leapfrog_output_box(self) -> None:
        if self._leapfrog_output_box is None:
            return
        self._leapfrog_output_box.configure(state="normal")
        self._leapfrog_output_box.delete("1.0", "end")
        self._leapfrog_output_box.insert("1.0", self.leapfrog_output_var.get())
        self._leapfrog_output_box.configure(state="disabled")

    def _set_copy_button_enabled(self, enabled: bool) -> None:
        if self._copy_button is None:
            return
        self._copy_button.configure(state="normal" if enabled else "disabled")

    def _on_copy_leapfrog_output(self) -> None:
        text = str(self.leapfrog_output_var.get()).strip()
        if not text:
            self.leapfrog_status_var.set("No hay parámetros para copiar.")
            return
        if self._copy_button is None:
            return
        self._copy_button.clipboard_clear()
        self._copy_button.clipboard_append(text)
        base = str(self.leapfrog_status_var.get()).replace(" Copiado al portapapeles.", "").strip()
        self.leapfrog_status_var.set(f"{base} Copiado al portapapeles.")

    @staticmethod
    def _as_float_or_none(value: object) -> float | None:
        try:
            if value is None:
                return None
            return float(value)
        except Exception:
            return None

    def _fmt_numeric(self, value: object) -> str:
        parsed = self._as_float_or_none(value)
        if parsed is None:
            return "Pendiente"
        return f"{parsed:.6g}"
