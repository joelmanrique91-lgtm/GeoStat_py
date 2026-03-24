"""Dedicated Variography stage view for first real experimental workflow slice."""

from __future__ import annotations

import logging
import threading
import customtkinter as ctk

from app.ui.controllers.variography_controller import VariographyController
from app.ui.panels.dashboard_grid import DashboardGrid
from app.ui.renderers import MatplotlibVariographyRenderer, VariographyRenderContext
from app.ui.theme import BG_CARD, BG_PANEL, CHART_FONT_SIZE_LABEL, CHART_FONT_SIZE_LEGEND, CHART_TEXT, SEM_ORANGE, SEM_RED, TEXT_MAIN, TEXT_MUTED

VARIOGRAPHY_CONTROLS_WIDTH = 338
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
        self.status_var = ctk.StringVar(value="Configura parámetros y ejecuta cálculo experimental.")
        self.warning_var = ctk.StringVar(value="")
        self.blocker_var = ctk.StringVar(value="")
        self._plot_host: ctk.CTkFrame | None = None
        self._compute_button: ctk.CTkButton | None = None
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

        wrapper = ctk.CTkFrame(parent, fg_color=BG_PANEL)
        wrapper.grid(row=0, column=0, sticky="nsew", padx=2, pady=1)
        wrapper.grid_columnconfigure(1, weight=1)
        wrapper.grid_rowconfigure(0, weight=1)

        controls = ctk.CTkFrame(wrapper, fg_color=BG_CARD, width=VARIOGRAPHY_CONTROLS_WIDTH)
        controls.grid(row=0, column=0, sticky="nsw", padx=(0, 5), pady=0)
        controls.grid_propagate(False)
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
        ctk.CTkLabel(alerts, textvariable=self.blocker_var, text_color=SEM_RED, justify="left", wraplength=VARIOGRAPHY_TEXT_WRAP).pack(anchor="w")

        cached = self._session.last_response
        if cached is not None and cached.result is not None:
            self.status_var.set(str(cached.message))
            self.warning_var.set("\n".join([f"[{item.code}] {item.message}" for item in cached.warnings]) if cached.warnings else "")
            self.blocker_var.set("\n".join([f"[{item.code}] {item.message}" for item in cached.blockers]) if cached.blockers else "")
            result_payload = {
                "lag_centers": cached.result.lag_centers,
                "gamma_values": cached.result.gamma_values,
                "pair_counts": cached.result.pair_counts,
                "source_points": cached.result.source_points,
                "used_points": cached.result.used_points,
                "downsampled": cached.result.downsampled,
                "metadata": cached.result.metadata,
            }
            self._render_result_plot(result_payload, bool(cached.ok))
            return

        if self._is_ready_for_compute() and not self._auto_compute_done:
            self._auto_compute_done = True
            parent.after(60, self._on_compute)
            return
        self._render_empty_plot("Sin cálculo aún. Presione 'Calcular'.")

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

        self._compute_button = ctk.CTkButton(parent, text="Compute experimental variogram", command=self._on_compute)
        self._compute_button.grid(row=row, column=0, sticky="ew", padx=8, pady=(8, 8))
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
            warnings = [f"[{item.get('code')}] {item.get('message')}" for item in response.get("warnings", [])]
            blockers = [f"[{item.get('code')}] {item.get('message')}" for item in response.get("blockers", [])]
            self.warning_var.set("\n".join(warnings) if warnings else "")
            self.blocker_var.set("\n".join(blockers) if blockers else "")
            result = response.get("result")
            if not isinstance(result, dict):
                self._render_compute_failure_panel(response)
                return
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
            grid = DashboardGrid(self._plot_host, 2, 2, figsize=(16.2, 8.8), width_ratios=[1.9, 1.0], height_ratios=[1.0, 1.0])
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
