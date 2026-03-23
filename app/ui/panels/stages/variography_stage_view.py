"""Dedicated Variography stage view for first real experimental workflow slice."""

from __future__ import annotations

import customtkinter as ctk

from app.ui.controllers.variography_controller import VariographyController
from app.ui.panels.dashboard_grid import DashboardGrid
from app.ui.renderers import MatplotlibVariographyRenderer, VariographyRenderContext
from app.ui.theme import BG_CARD, BG_PANEL, CHART_FONT_SIZE_LABEL, CHART_FONT_SIZE_LEGEND, CHART_TEXT, SEM_ORANGE, SEM_RED, TEXT_MAIN, TEXT_MUTED


class VariographyStageView:
    def __init__(self, controller: VariographyController) -> None:
        self.controller = controller
        self.renderer = MatplotlibVariographyRenderer()
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
        self.status_var = ctk.StringVar(value="Configura parámetros y ejecuta cálculo experimental.")
        self.warning_var = ctk.StringVar(value="")
        self.blocker_var = ctk.StringVar(value="")
        self._plot_host: ctk.CTkFrame | None = None
        self._bind_dirty_traces()

    def mount(self, parent: ctk.CTkFrame) -> None:
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

        wrapper = ctk.CTkFrame(parent, fg_color=BG_PANEL)
        wrapper.grid(row=0, column=0, sticky="nsew")
        wrapper.grid_columnconfigure(1, weight=1)
        wrapper.grid_rowconfigure(0, weight=1)

        controls = ctk.CTkFrame(wrapper, fg_color=BG_CARD, width=320)
        controls.grid(row=0, column=0, sticky="nsw", padx=(0, 8), pady=0)
        controls.grid_propagate(False)
        self._build_controls(controls, [str(v) for v in init.get("target_options", [])])

        results = ctk.CTkFrame(wrapper, fg_color=BG_PANEL)
        results.grid(row=0, column=1, sticky="nsew")
        results.grid_columnconfigure(0, weight=1)
        results.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(results, text="Variografía experimental", text_color=TEXT_MAIN, font=ctk.CTkFont(size=15, weight="bold")).grid(row=0, column=0, sticky="w", pady=(0, 2))
        ctk.CTkLabel(results, textvariable=self.status_var, text_color=TEXT_MUTED, justify="left", wraplength=900).grid(row=1, column=0, sticky="w", pady=(0, 4))

        self._plot_host = ctk.CTkFrame(results, fg_color=BG_CARD)
        self._plot_host.grid(row=2, column=0, sticky="nsew")
        self._render_empty_plot()

        alerts = ctk.CTkFrame(results, fg_color="transparent")
        alerts.grid(row=3, column=0, sticky="ew", pady=(4, 0))
        ctk.CTkLabel(alerts, textvariable=self.warning_var, text_color=SEM_ORANGE, justify="left", wraplength=900).pack(anchor="w")
        ctk.CTkLabel(alerts, textvariable=self.blocker_var, text_color=SEM_RED, justify="left", wraplength=900).pack(anchor="w")

    def _build_controls(self, parent: ctk.CTkFrame, target_options: list[str]) -> None:
        row = 0
        entries: list[tuple[str, ctk.StringVar]] = [
            ("lag_distance", self.lag_distance_var),
            ("n_lags", self.n_lags_var),
            ("lag_tolerance", self.lag_tolerance_var),
            ("max_distance", self.max_distance_var),
            ("azimuth", self.azimuth_var),
            ("dip", self.dip_var),
            ("ang_tol_h", self.ang_tol_h_var),
            ("ang_tol_v", self.ang_tol_v_var),
            ("band_width", self.band_width_var),
            ("band_height", self.band_height_var),
        ]
        ctk.CTkLabel(parent, text="Variable objetivo", text_color=TEXT_MAIN).grid(row=row, column=0, sticky="w", padx=8, pady=(8, 2))
        row += 1
        ctk.CTkOptionMenu(parent, variable=self.target_var, values=target_options or [""], state="normal" if target_options else "disabled").grid(row=row, column=0, sticky="ew", padx=8, pady=(0, 6))
        row += 1
        ctk.CTkLabel(parent, text="Estimator", text_color=TEXT_MAIN).grid(row=row, column=0, sticky="w", padx=8, pady=(2, 2))
        row += 1
        ctk.CTkOptionMenu(parent, variable=self.estimator_var, values=["classical", "cressie_hawkins"]).grid(row=row, column=0, sticky="ew", padx=8, pady=(0, 6))
        row += 1

        for label, var in entries:
            ctk.CTkLabel(parent, text=label, text_color=TEXT_MUTED).grid(row=row, column=0, sticky="w", padx=8, pady=(2, 1))
            row += 1
            ctk.CTkEntry(parent, textvariable=var).grid(row=row, column=0, sticky="ew", padx=8, pady=(0, 4))
            row += 1

        ctk.CTkButton(parent, text="Compute experimental variogram", command=self._on_compute).grid(row=row, column=0, sticky="ew", padx=8, pady=(8, 8))
        parent.grid_columnconfigure(0, weight=1)

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
        ]
        for var in observed:
            var.trace_add("write", self._on_any_param_changed)

    def _on_any_param_changed(self, *_args) -> None:
        self.controller.mark_dirty(self.target_var.get().strip())
        if self.blocker_var.get():
            self.status_var.set("Parámetros modificados. Recalcula para validar estado.")

    def _on_compute(self) -> None:
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
            }
        except Exception as exc:
            self.warning_var.set("")
            self.blocker_var.set(f"[INVALID_INPUT_FORMAT] Revisa el formato numérico de parámetros: {exc}")
            self.status_var.set("No se pudo iniciar cálculo por parámetros inválidos.")
            self._render_empty_plot(message="Sin cálculo: formato inválido en parámetros.")
            return

        response = self.controller.compute(ui_state)
        self.status_var.set(str(response.get("message", "")))
        warnings = [f"[{item.get('code')}] {item.get('message')}" for item in response.get("warnings", [])]
        blockers = [f"[{item.get('code')}] {item.get('message')}" for item in response.get("blockers", [])]
        self.warning_var.set("\n".join(warnings) if warnings else "")
        self.blocker_var.set("\n".join(blockers) if blockers else "")
        result = response.get("result")
        if not isinstance(result, dict):
            self._render_empty_plot(message="Sin resultado para renderizar. Revisa bloqueos/advertencias.")
            return
        self._render_result_plot(result, bool(response.get("ok", False)))

    def _render_empty_plot(self, message: str = "Sin cálculo aún.") -> None:
        if self._plot_host is None:
            return
        DashboardGrid.clear(self._plot_host)
        ctk.CTkLabel(self._plot_host, text=message, text_color=TEXT_MUTED).pack(anchor="w", padx=8, pady=8)

    def _render_result_plot(self, result: dict[str, object], ok: bool) -> None:
        if self._plot_host is None:
            return
        DashboardGrid.clear(self._plot_host)
        grid = DashboardGrid(self._plot_host, 2, 2, figsize=(12.5, 7.0), width_ratios=[1.9, 1.0], height_ratios=[1.0, 1.0])
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

    @staticmethod
    def _parse_float(value: str) -> float:
        normalized = str(value).strip().replace(",", ".")
        return float(normalized)

    @staticmethod
    def _parse_int(value: str) -> int:
        return int(float(str(value).strip()))
