"""Application service for experimental variography vertical slice."""

from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
import logging
import math

from pandas.api.types import is_numeric_dtype

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
    FitDiagnosticsContract,
    ReliabilityContract,
    StructureContract,
    VariogramModelContract,
)
from app.services.variogram_modeling_service import (
    ALLOWED_STRUCTURE_TYPES,
    auto_fit_wls,
    evaluate_model,
    evaluate_quality,
)
from app.services.visualization_service import compute_experimental_variogram
from app.services.variography_validation_service import assess_fit_reliability, classify_operational_reliability

logger = logging.getLogger(__name__)


def _safe_float(value: object, default: float) -> float:
    try:
        if value is None:
            return default
        normalized = str(value).strip()
        if not normalized:
            return default
        return float(normalized)
    except (TypeError, ValueError):
        return default


def _safe_int(value: object, default: int) -> int:
    try:
        if value is None:
            return default
        normalized = str(value).strip()
        if not normalized:
            return default
        return int(float(normalized))
    except (TypeError, ValueError):
        return default


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
        variable_config = self.host_service.variable_config
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
            x_col=str(params.get("x_col") or (variable_config.x_column if variable_config else "")),
            y_col=str(params.get("y_col") or (variable_config.y_column if variable_config else "")),
            z_col=str(params.get("z_col") or (variable_config.z_column if variable_config else "")),
            target_col=target,
            estimator=str(params.get("estimator") or "classical"),
            lag=LagDefinition(
                lag_distance=_safe_float(params.get("lag_distance", 0.0), 0.0),
                n_lags=_safe_int(params.get("n_lags", 0), 0),
                lag_tolerance=_safe_float(params.get("lag_tolerance", 0.0), 0.0),
                max_distance=_safe_float(params.get("max_distance", 0.0), 0.0),
            ),
            direction=DirectionDefinition(
                azimuth=_safe_float(params.get("azimuth", 0.0), 0.0),
                dip=_safe_float(params.get("dip", 0.0), 0.0),
                ang_tol_h=_safe_float(params.get("ang_tol_h", 90.0), 90.0),
                ang_tol_v=_safe_float(params.get("ang_tol_v", 90.0), 90.0),
                band_width=_safe_float(params.get("band_width", 0.0), 0.0),
                band_height=_safe_float(params.get("band_height", 0.0), 0.0),
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
        if request.direction.band_width < 0 or request.direction.band_height < 0:
            blockers.append(VariographyIssue("INVALID_BANDWIDTH", "Band width/band height no pueden ser negativos.", "blocker"))
        if request.direction.ang_tol_h >= 85 or request.direction.ang_tol_v >= 85:
            warnings.append(
                VariographyIssue(
                    "NEAR_OMNIDIRECTIONAL_WINDOW",
                    "Tolerancias angulares cercanas a 90°: análisis prácticamente omnidireccional.",
                    "warning",
                )
            )
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
        if dataframe.empty:
            response = VariographyComputeResponse(
                schema_version=SCHEMA_VERSION,
                ok=False,
                message="No hay filas activas para calcular variografía (revisa filtros/contexto).",
                request=request,
                result=None,
                warnings=warnings,
                blockers=[VariographyIssue("NO_ACTIVE_ROWS", "El conjunto activo quedó vacío por filtros/contexto.", "blocker")],
            )
            self.session.mark_computed(response)
            return response
        effective_rows = int(len(dataframe))
        logger.info(
            "Variography compute request | target=%s rows=%s x=%s y=%s z=%s n_lags=%s lag=%s max_distance=%s domain_filter=%s",
            request.target_col,
            effective_rows,
            request.x_col,
            request.y_col,
            request.z_col,
            request.lag.n_lags,
            request.lag.lag_distance,
            request.lag.max_distance,
            request.context.active_domain_filter,
        )

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
                lag_tolerance=request.lag.lag_tolerance,
                azimuth=request.direction.azimuth,
                dip=request.direction.dip,
                ang_tol_h=request.direction.ang_tol_h,
                ang_tol_v=request.direction.ang_tol_v,
                band_width=request.direction.band_width,
                band_height=request.direction.band_height,
                max_points=2500,
            )
        except Exception as exc:
            message = str(exc)
            blocker_code = "NO_PAIRS_IN_RANGE" if "No se encontraron pares dentro de max_distance" in message else "COMPUTE_FAILED"
            response = VariographyComputeResponse(
                schema_version=SCHEMA_VERSION,
                ok=False,
                message=f"No se pudo calcular variograma experimental: {exc}",
                request=request,
                result=None,
                warnings=warnings,
                blockers=[VariographyIssue(blocker_code, str(exc), "blocker")],
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

        model_payload = self._build_model_payload(params, raw.lag_centers, raw.gamma_values, pair_counts, warnings, blockers)
        model_classification = (
            model_payload.get("reliability", {}).get("classification", "")
            if isinstance(model_payload.get("reliability", {}), dict)
            else ""
        )
        if model_classification == "EXPLORATORY_ONLY":
            warnings.append(
                VariographyIssue(
                    "MODEL_EXPLORATORY_ONLY",
                    "Modelo disponible sólo para diagnóstico exploratorio (no para decisiones de estimación).",
                    "warning",
                )
            )
        if model_classification == "LOW_RELIABILITY":
            warnings.append(
                VariographyIssue(
                    "MODEL_LOW_RELIABILITY",
                    "Modelo calculado con baja confiabilidad operativa.",
                    "warning",
                )
            )
        if model_classification == "BLOCKED":
            blockers.append(
                VariographyIssue(
                    "MODEL_BLOCKED",
                    "Modelo bloqueado por criterios operativos de confiabilidad.",
                    "blocker",
                )
            )

        estimated_defaults = self.host_service.estimate_variography_defaults(
            n_lags=request.lag.n_lags,
            context_snapshot=self.host_service.get_analysis_context_snapshot(),
            dataframe=dataframe,
        )
        dominant_blocker = blockers[0].code if blockers else ""
        dominant_warning = warnings[0].code if warnings else ""
        metadata = {
            "computation_hash": self._compute_hash(request),
            "direction_applied": True,
            "direction_mode": "directional" if (request.direction.ang_tol_h < 90.0 or request.direction.ang_tol_v < 90.0 or request.direction.band_width > 0.0 or request.direction.band_height > 0.0) else "omnidirectional",
            "direction_note": "Parámetros direccionales aplicados al set de pares.",
            "lag_tolerance": request.lag.lag_tolerance,
            "estimator": request.estimator,
            "effective_rows": effective_rows,
            "total_pairs": int(sum(pair_counts)),
            "dominant_blocker": dominant_blocker,
            "dominant_warning": dominant_warning,
            "spatial_extent": float(estimated_defaults.get("spatial_extent", 0.0)),
            "recommended_max_distance": float(estimated_defaults.get("max_distance", request.lag.max_distance)),
            "recommended_lag_distance": float(estimated_defaults.get("lag_distance", request.lag.lag_distance)),
            "effective_params": {
                "lag_distance": float(request.lag.lag_distance),
                "n_lags": int(request.lag.n_lags),
                "max_distance": float(request.lag.max_distance),
                "lag_tolerance": float(request.lag.lag_tolerance),
            },
            "model": model_payload,
            "estimation_contract": {
                "schema": "variogram_model.v1",
                "classification": model_classification or "BLOCKED",
                "model": model_payload,
            },
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
        logger.info(
            "Variography compute done | ok=%s blocker=%s warning=%s lags=%s pairs=%s",
            ok,
            dominant_blocker or "-",
            dominant_warning or "-",
            len(result.lag_centers),
            sum(result.pair_counts),
        )
        return response

    def _build_model_payload(
        self,
        params: dict[str, object],
        lag_centers: list[float],
        gamma_values: list[float],
        pair_counts: list[int],
        warnings: list[VariographyIssue],
        blockers: list[VariographyIssue],
    ) -> dict[str, object]:
        model = params.get("model") if isinstance(params.get("model"), dict) else {}
        nugget_raw = model.get("nugget") if isinstance(model.get("nugget"), dict) else {}
        nugget = {
            "enabled": bool(nugget_raw.get("enabled", True)),
            "value": float(nugget_raw.get("value", 0.0) or 0.0),
            "locked": bool(nugget_raw.get("locked", False)),
        }
        if nugget["value"] < 0:
            blockers.append(VariographyIssue("INVALID_NUGGET", "Nugget no puede ser negativo.", "blocker"))
            nugget["value"] = 0.0
        if not nugget["enabled"]:
            nugget["value"] = 0.0
        structures_raw = model.get("structures") if isinstance(model.get("structures"), list) else []
        structures: list[dict[str, object]] = []
        active_count = 0
        for idx, item in enumerate(structures_raw):
            if not isinstance(item, dict):
                continue
            structure_type = str(item.get("type", "spherical")).strip().lower()
            if structure_type not in ALLOWED_STRUCTURE_TYPES:
                blockers.append(VariographyIssue("INVALID_STRUCTURE_TYPE", f"Estructura #{idx + 1} tiene tipo no permitido: {structure_type}", "blocker"))
                continue
            contribution = float(item.get("contribution", 0.0) or 0.0)
            if contribution < 0:
                blockers.append(VariographyIssue("INVALID_STRUCTURE_CONTRIBUTION", f"Estructura #{idx + 1}: contribución no puede ser negativa.", "blocker"))
                contribution = 0.0
            range_major = float(item.get("range_major", 1.0) or 1.0)
            range_minor = float(item.get("range_minor", range_major) or range_major)
            range_vertical = float(item.get("range_vertical", range_major) or range_major)
            if range_major <= 0 or range_minor <= 0 or range_vertical <= 0:
                blockers.append(VariographyIssue("INVALID_STRUCTURE_RANGE", f"Estructura #{idx + 1}: ranges deben ser > 0.", "blocker"))
                range_major = max(1e-6, range_major)
                range_minor = max(1e-6, range_minor)
                range_vertical = max(1e-6, range_vertical)
            is_active = bool(item.get("active", True))
            if is_active:
                active_count += 1
            structures.append(
                {
                    "active": is_active,
                    "type": structure_type,
                    "contribution": contribution,
                    "range_major": range_major,
                    "range_minor": range_minor,
                    "range_vertical": range_vertical,
                    "azimuth": float(item.get("azimuth", 0.0) or 0.0),
                    "dip": float(item.get("dip", 0.0) or 0.0),
                    "lock_contribution": bool(item.get("lock_contribution", False)),
                    "lock_range": bool(item.get("lock_range", False)),
                }
            )

        fit_raw = model.get("fit") if isinstance(model.get("fit"), dict) else {}
        fit_method = str(fit_raw.get("method", "manual")).upper()
        min_pairs = max(1, int(fit_raw.get("min_pairs", 30) or 30))
        excluded_lags = [int(v) for v in (fit_raw.get("exclude_lags", []) if isinstance(fit_raw.get("exclude_lags"), list) else []) if int(v) > 0]
        if not structures or active_count <= 0:
            if fit_method == "MANUAL":
                blockers.append(
                    VariographyIssue(
                        "MISSING_ACTIVE_STRUCTURES_MANUAL",
                        "Debe definir al menos una estructura activa para modelado manual.",
                        "blocker",
                    )
                )
            else:
                blockers.append(
                    VariographyIssue(
                        "MISSING_ACTIVE_STRUCTURES_AUTO",
                        "Debe definir al menos una estructura activa para ajuste automático.",
                        "blocker",
                    )
                )
            contract = VariogramModelContract(
                nugget=nugget,
                structures=[StructureContract(**item) for item in structures],
                fit=FitDiagnosticsContract(method=fit_method, min_pairs=min_pairs, exclude_lags=excluded_lags, optimizer={}),
                curve_total=[],
                curves_by_structure=[],
                sill=0.0,
                nugget_relative_pct=0.0,
                practical_range=0.0,
                anisotropy_mode="equivalent_isotropic_range",
                quality={"rmse": math.nan, "sse": math.nan, "valid_lags": 0, "invalid_lags": []},
                reliability=ReliabilityContract(
                    classification="BLOCKED",
                    level="low",
                    flags=["MISSING_ACTIVE_STRUCTURES"],
                    notes=["Sin estructuras activas para modelado."],
                    metrics={},
                ),
                usage_target=str(model.get("usage_target", "kriging")),
                usage_warnings=["Modelado bloqueado: sin estructuras activas."],
                assumptions=["No hay estructuras activas; no se construye modelo teórico."],
            )
            return contract.as_dict()
        if fit_method == "WLS":
            nugget, structures, fit_meta = auto_fit_wls(lag_centers, gamma_values, pair_counts, nugget, structures, min_pairs, excluded_lags)
        else:
            fit_meta = {"applied": False, "reason": "manual_mode"}

        modeled_total, by_structure, sill = evaluate_model(lag_centers, float(nugget["value"]), structures)
        quality = evaluate_quality(lag_centers, gamma_values, pair_counts, modeled_total, min_pairs, excluded_lags)
        if quality.valid_lags < 2:
            warnings.append(VariographyIssue("LOW_VALID_LAGS_FOR_FIT", "Modelo ajustado con pocos lags válidos después de filtros.", "warning"))

        nugget_rel = (float(nugget["value"]) / sill * 100.0) if sill > 0 else 0.0
        if nugget_rel > 60.0:
            warnings.append(VariographyIssue("HIGH_NUGGET_RATIO", "Nugget/sill alto: continuidad espacial baja para kriging local.", "warning"))
        if sill <= 0:
            blockers.append(VariographyIssue("INVALID_SILL", "Sill total inválido; revise nugget y contribuciones.", "blocker"))
        warnings.append(
            VariographyIssue(
                "THEORETICAL_ANISOTROPY_SIMPLIFIED",
                "Anisotropía estructural simplificada: la curva teórica usa rango isotrópico equivalente (media geométrica de ejes).",
                "warning",
            )
        )
        fit_reliability = assess_fit_reliability(
            lag_centers=lag_centers,
            gamma_values=gamma_values,
            pair_counts=pair_counts,
            model_payload={
                "structures": structures,
                "quality": {
                    "rmse": quality.rmse,
                    "sse": quality.sse,
                    "valid_lags": quality.valid_lags,
                },
                "sill": sill,
                "nugget_relative_pct": nugget_rel,
            },
            min_pairs=min_pairs,
        )
        operational_reliability = classify_operational_reliability(
            fit_reliability=fit_reliability,
            blockers_count=len(blockers),
            total_pairs=int(sum(pair_counts)),
            valid_lags=int(quality.valid_lags),
        )
        if fit_reliability.level != "high":
            warnings.append(
                VariographyIssue(
                    "LOW_MODEL_RELIABILITY",
                    f"Ajuste con confiabilidad {fit_reliability.level}; revisar flags: {', '.join(fit_reliability.flags[:4]) or 'sin detalle'}",
                    "warning",
                )
            )
        model_ranges = [float(s.get("range_major", 0.0)) for s in structures if bool(s.get("active", True))]
        practical_range = max(model_ranges) if model_ranges else 0.0
        # TODO(geostat): sustituir rango isotrópico equivalente por modelado anisotrópico completo orientado por dirección de lag.
        model_contract = VariogramModelContract(
            nugget=nugget,
            structures=[StructureContract(**item) for item in structures],
            fit=FitDiagnosticsContract(
                method=fit_method,
                min_pairs=min_pairs,
                exclude_lags=excluded_lags,
                optimizer=fit_meta,
            ),
            curve_total=[float(v) for v in modeled_total],
            curves_by_structure=[[float(v) for v in curve] for curve in by_structure],
            sill=float(sill),
            nugget_relative_pct=float(nugget_rel),
            practical_range=float(practical_range),
            anisotropy_mode="equivalent_isotropic_range",
            quality={
                "rmse": quality.rmse,
                "sse": quality.sse,
                "valid_lags": quality.valid_lags,
                "invalid_lags": quality.invalid_lags,
            },
            reliability=ReliabilityContract(
                classification=operational_reliability.classification,
                level=fit_reliability.level,
                flags=fit_reliability.flags,
                notes=[*fit_reliability.notes, *operational_reliability.rationale],
                metrics=fit_reliability.metrics,
            ),
            usage_target=str(model.get("usage_target", "kriging")),
            usage_warnings=self._usage_warnings(str(model.get("usage_target", "kriging")), nugget_rel, quality.rmse),
            assumptions=[
                "Curva teórica en 1D de lag usa rango isotrópico equivalente.",
                "Orientación estructural se preserva como metadata para consumo aguas abajo.",
            ],
        )
        return model_contract.as_dict()

    def _usage_warnings(self, usage_target: str, nugget_rel: float, rmse: float) -> list[str]:
        warnings: list[str] = []
        if usage_target == "kriging":
            if nugget_rel > 70.0:
                warnings.append("Modelo poco adecuado para kriging local: nugget muy alto.")
            if math.isfinite(rmse) and rmse > 1.0:
                warnings.append("Error de ajuste alto para kriging; revise estructuras y lags excluidos.")
        if usage_target == "simulation":
            if nugget_rel < 1.0:
                warnings.append("Nugget extremadamente bajo puede subestimar variabilidad en simulación.")
        return warnings

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
        numeric_columns = [
            ("x_col", request.x_col),
            ("y_col", request.y_col),
            ("z_col", request.z_col),
            ("target_col", request.target_col),
        ]
        for label, col in numeric_columns:
            if col and col in df.columns and not is_numeric_dtype(df[col]):
                issues.append(VariographyIssue("NON_NUMERIC_CONTEXT_COLUMN", f"{label} debe ser numérica: {col}", "blocker"))
        if request.lag.lag_distance <= 0:
            issues.append(VariographyIssue("INVALID_LAG_DISTANCE", "lag_distance debe ser > 0.", "blocker"))
        if request.lag.n_lags <= 0:
            issues.append(VariographyIssue("INVALID_N_LAGS", "n_lags debe ser > 0.", "blocker"))
        if request.lag.max_distance <= 0:
            issues.append(VariographyIssue("INVALID_MAX_DISTANCE", "max_distance debe ser > 0.", "blocker"))
        if request.lag.lag_tolerance <= 0:
            issues.append(VariographyIssue("INVALID_LAG_TOLERANCE", "lag_tolerance debe ser > 0.", "blocker"))
        if request.direction.ang_tol_h <= 0 or request.direction.ang_tol_h > 90:
            issues.append(VariographyIssue("INVALID_ANG_TOL_H", "ang_tol_h debe estar en (0, 90].", "blocker"))
        if request.direction.ang_tol_v <= 0 or request.direction.ang_tol_v > 90:
            issues.append(VariographyIssue("INVALID_ANG_TOL_V", "ang_tol_v debe estar en (0, 90].", "blocker"))
        if request.direction.dip < -90 or request.direction.dip > 90:
            issues.append(VariographyIssue("INVALID_DIP", "dip debe estar en [-90, 90].", "blocker"))
        if request.lag.max_distance <= request.lag.lag_distance:
            issues.append(VariographyIssue("MAX_DISTANCE_TOO_SMALL", "max_distance debe ser mayor que lag_distance.", "blocker"))
        return issues

    def _compute_hash(self, request: ExperimentalVariogramRequest) -> str:
        payload = json.dumps(asdict(request), sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
