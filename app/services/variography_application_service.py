"""Application service for experimental variography vertical slice."""

from __future__ import annotations

from dataclasses import asdict
import hashlib
import json

from app.models.variography import (
    AnalysisContextRef,
    DirectionDefinition,
    ExperimentalVariogramRequest,
    ExperimentalVariogramResult,
    LagDefinition,
    SCHEMA_VERSION,
    VariographyComputeResponse,
    VariographyIssue,
    VariographySession,
)
from app.services.visualization_service import compute_experimental_variogram


class VariographyApplicationService:
    """Orchestrates request validation, computation wrapping and response normalization."""

    def __init__(self, host_service) -> None:
        self.host_service = host_service
        self.session = VariographySession()

    def get_session(self) -> VariographySession:
        return self.session

    def build_request(self, params: dict[str, object]) -> ExperimentalVariogramRequest:
        snapshot = self.host_service.get_analysis_context_snapshot()
        dataset_name = self.host_service.current_dataset.file_name if self.host_service.current_dataset is not None else ""
        target = str(params.get("target_col") or snapshot.get("resolved_target_column") or "")
        context = AnalysisContextRef(
            dataset_file=dataset_name,
            resolved_target_column=str(snapshot.get("resolved_target_column") or ""),
            active_domain_column=str(snapshot.get("active_domain_column") or ""),
            active_domain_filter=str(snapshot.get("active_domain_filter") or ""),
            support=str(self.host_service.workflow_state.active_support or "Muestra original"),
        )
        request = ExperimentalVariogramRequest(
            schema_version=SCHEMA_VERSION,
            context=context,
            x_col=str(params.get("x_col") or self.host_service.variable_config.x_column),
            y_col=str(params.get("y_col") or self.host_service.variable_config.y_column),
            z_col=str(params.get("z_col") or self.host_service.variable_config.z_column),
            target_col=target,
            estimator=str(params.get("estimator") or "classical"),
            lag=LagDefinition(
                lag_distance=float(params.get("lag_distance", 0.0)),
                n_lags=int(params.get("n_lags", 0)),
                lag_tolerance=float(params.get("lag_tolerance", 0.0)),
                max_distance=float(params.get("max_distance", 0.0)),
            ),
            direction=DirectionDefinition(
                azimuth=float(params.get("azimuth", 0.0)),
                dip=float(params.get("dip", 0.0)),
                ang_tol_h=float(params.get("ang_tol_h", 90.0)),
                ang_tol_v=float(params.get("ang_tol_v", 90.0)),
                band_width=float(params.get("band_width", 0.0)),
                band_height=float(params.get("band_height", 0.0)),
            ),
        )
        return request

    def compute(self, params: dict[str, object]) -> VariographyComputeResponse:
        request = self.build_request(params)
        self.session.selected_target = request.target_col
        self.session.selected_domain_filter = request.context.active_domain_filter
        self.session.selected_support = request.context.support
        self.session.lag_distance = request.lag.lag_distance
        self.session.n_lags = request.lag.n_lags
        self.session.lag_tolerance = request.lag.lag_tolerance
        self.session.max_distance = request.lag.max_distance
        self.session.azimuth = request.direction.azimuth
        self.session.dip = request.direction.dip
        self.session.ang_tol_h = request.direction.ang_tol_h
        self.session.ang_tol_v = request.direction.ang_tol_v
        self.session.band_width = request.direction.band_width
        self.session.band_height = request.direction.band_height
        self.session.estimator = request.estimator
        blockers = self._validate_request(request)
        warnings: list[VariographyIssue] = []
        if request.direction.ang_tol_h <= 0 or request.direction.ang_tol_v <= 0:
            blockers.append(VariographyIssue("INVALID_DIRECTION_TOL", "Las tolerancias angulares deben ser > 0.", "blocker"))
        if request.direction.band_width < 0 or request.direction.band_height < 0:
            blockers.append(VariographyIssue("INVALID_BANDWIDTH", "Band width/band height no pueden ser negativos.", "blocker"))
        if request.direction.ang_tol_h > 90 or request.direction.ang_tol_v > 90:
            warnings.append(VariographyIssue("WIDE_DIRECTION_TOL", "Tolerancias angulares altas pueden mezclar direcciones.", "warning"))
        if request.estimator != "classical":
            warnings.append(VariographyIssue("ESTIMATOR_FALLBACK", "Estimator no soportado en este slice; se usa cálculo clásico.", "warning"))

        if blockers:
            response = VariographyComputeResponse(
                schema_version=SCHEMA_VERSION,
                ok=False,
                message="Solicitud inválida para variografía experimental.",
                request=request,
                result=None,
                warnings=warnings,
                blockers=blockers,
            )
            self.session.mark_computed(response)
            return response

        dataframe = self.host_service._get_filtered_dataframe()  # trusted internal source for active workflow filters
        if dataframe is None:
            response = VariographyComputeResponse(
                schema_version=SCHEMA_VERSION,
                ok=False,
                message="No hay dataset disponible para variografía.",
                request=request,
                result=None,
                warnings=warnings,
                blockers=[VariographyIssue("MISSING_DATASET", "No hay dataset cargado.", "blocker")],
            )
            self.session.mark_computed(response)
            return response

        try:
            raw = compute_experimental_variogram(
                dataframe,
                request.x_col,
                request.y_col,
                request.z_col,
                request.target_col,
                request.lag.lag_distance,
                request.lag.n_lags,
                request.lag.max_distance,
                max_points=2500,
            )
        except Exception as exc:
            response = VariographyComputeResponse(
                schema_version=SCHEMA_VERSION,
                ok=False,
                message=f"No se pudo calcular variograma experimental: {exc}",
                request=request,
                result=None,
                warnings=warnings,
                blockers=[VariographyIssue("COMPUTE_FAILED", str(exc), "blocker")],
            )
            self.session.mark_computed(response)
            return response

        pair_counts = [int(v) for v in raw.pair_counts]
        low_pair_lags = [idx + 1 for idx, count in enumerate(pair_counts) if count < 30]
        if low_pair_lags:
            warnings.append(
                VariographyIssue(
                    "LOW_NPAIRS_LAG",
                    f"Lags con npairs bajos (<30): {', '.join(str(v) for v in low_pair_lags[:6])}",
                    "warning",
                )
            )
        finite_gamma = [value for value in raw.gamma_values if value == value]
        if len(finite_gamma) < 2:
            blockers.append(VariographyIssue("INSUFFICIENT_LAG_COVERAGE", "Cobertura de pares insuficiente para interpretar el variograma.", "blocker"))

        metadata = {
            "computation_hash": self._compute_hash(request),
            "direction_applied": False,
            "direction_note": "Slice inicial: cálculo omni; parámetros direccionales validados y auditados, aún no aplicados al set de pares.",
            "lag_tolerance": request.lag.lag_tolerance,
            "estimator": request.estimator,
        }
        result = ExperimentalVariogramResult(
            schema_version=SCHEMA_VERSION,
            lag_centers=[float(v) for v in raw.lag_centers],
            gamma_values=[float(v) for v in raw.gamma_values],
            pair_counts=pair_counts,
            source_points=int(raw.source_points),
            used_points=int(raw.used_points),
            downsampled=bool(raw.downsampled),
            warnings=warnings,
            blockers=blockers,
            metadata=metadata,
        )
        ok = not blockers
        response = VariographyComputeResponse(
            schema_version=SCHEMA_VERSION,
            ok=ok,
            message="Variograma experimental calculado." if ok else "Variograma calculado con bloqueos de calidad.",
            request=request,
            result=result,
            warnings=warnings,
            blockers=blockers,
        )
        self.session.mark_computed(response)
        self.host_service.activity_log.log(
            "variography_compute",
            "success" if ok else "warning",
            response.message,
            {
                "target": request.target_col,
                "n_lags": request.lag.n_lags,
                "max_pairs": max(pair_counts, default=0),
                "warning_count": len(warnings),
                "blocker_count": len(blockers),
            },
        )
        return response

    def _validate_request(self, request: ExperimentalVariogramRequest) -> list[VariographyIssue]:
        issues: list[VariographyIssue] = []
        if self.host_service.variable_config is None:
            issues.append(VariographyIssue("MISSING_VARIABLE_CONFIG", "Configura X/Y/Z/target antes de variografía.", "blocker"))
        if self.host_service.current_dataset is None:
            issues.append(VariographyIssue("MISSING_DATASET", "Carga un dataset antes de variografía.", "blocker"))
            return issues
        df = self.host_service.current_dataset.dataframe
        for col in [request.x_col, request.y_col, request.z_col, request.target_col]:
            if not col or col not in df.columns:
                issues.append(VariographyIssue("INVALID_CONTEXT_COLUMNS", f"Columna inválida o faltante: {col}", "blocker"))
        if request.lag.lag_distance <= 0:
            issues.append(VariographyIssue("INVALID_LAG_DISTANCE", "lag_distance debe ser > 0.", "blocker"))
        if request.lag.n_lags <= 0:
            issues.append(VariographyIssue("INVALID_N_LAGS", "n_lags debe ser > 0.", "blocker"))
        if request.lag.max_distance <= 0:
            issues.append(VariographyIssue("INVALID_MAX_DISTANCE", "max_distance debe ser > 0.", "blocker"))
        if request.lag.lag_tolerance <= 0:
            issues.append(VariographyIssue("INVALID_LAG_TOLERANCE", "lag_tolerance debe ser > 0.", "blocker"))
        if request.lag.max_distance <= request.lag.lag_distance:
            issues.append(VariographyIssue("MAX_DISTANCE_TOO_SMALL", "max_distance debe ser mayor que lag_distance.", "blocker"))
        return issues

    def _compute_hash(self, request: ExperimentalVariogramRequest) -> str:
        payload = json.dumps(asdict(request), sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
