"""Service layer for geostatistical workflows."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import math
import statistics
import subprocess

from app.adapters.geostatspy_adapter import GeostatSpyAdapter
from app.models.dataset_model import DatasetModel
from app.models.variable_config_model import VariableConfigModel
from app.models.workflow_state_model import WorkflowStateModel
from app.services.activity_log_service import ActivityLogService
from app.services.visualization_service import SwathSeries, SpatialDataBundle, compute_swath_series, prepare_spatial_sections
from app.utils.paths import PROJECT_ROOT

WORKFLOW_STEPS = ["Datos", "EDA", "Cutoffs", "Espacial", "Dominios"]
FUNCTIONAL_STATUS = {step: "funcional" for step in WORKFLOW_STEPS}
STEP_EVENT_MAP = {
    "Datos": "workflow_step_data_opened",
    "EDA": "workflow_step_eda_opened",
    "Cutoffs": "workflow_step_cutoffs_opened",
    "Espacial": "workflow_step_spatial_opened",
    "Dominios": "workflow_step_domains_opened",
}


@dataclass
class LoadCsvResult:
    success: bool
    message: str
    details: str
    dataset: DatasetModel | None = None


@dataclass
class RepoUpdateResult:
    success: bool
    message: str
    details: str
    restart_recommended: bool = False


@dataclass
class ColumnSelectionResult:
    success: bool
    message: str
    eda_summary: str


@dataclass
class VisualPreparationResult:
    success: bool
    message: str
    spatial_data: SpatialDataBundle | None


@dataclass
class CutoffResult:
    success: bool
    message: str


@dataclass
class DynamicCutoffResult:
    success: bool
    message: str
    cutoff_value: float = 0.0


def _read_csv(path: Path):
    import pandas as pd

    return pd.read_csv(path)


def _read_csv_with_encoding(path: Path, encoding: str):
    import pandas as pd

    return pd.read_csv(path, encoding=encoding)


def _csv_errors():
    from pandas.errors import EmptyDataError, ParserError

    return EmptyDataError, ParserError


def _is_numeric_dtype(series) -> bool:
    from pandas.api.types import is_numeric_dtype

    return bool(is_numeric_dtype(series))


def _to_numeric(series):
    import pandas as pd

    return pd.to_numeric(series, errors="coerce")


def _is_missing_category(value: object) -> bool:
    if value is None:
        return True
    normalized = str(value).strip().lower()
    if normalized in {"", "na", "n/a", "null", "none", "nan"}:
        return True
    return False


def _normalize_identifier(value: str) -> str:
    """Normalize identifiers for resilient column matching."""
    return value.lower().replace("_", "").replace(" ", "")


def _build_univariate_availability(target: str, valid_count: int, probability_min_samples: int = 3) -> dict[str, dict[str, object]]:
    histogram_available = valid_count > 0
    boxplot_available = valid_count > 0
    probability_available = valid_count >= probability_min_samples
    return {
        "histogram": {
            "available": histogram_available,
            "message": ""
            if histogram_available
            else f"Histograma no disponible: target {target} no tiene valores numéricos válidos.",
        },
        "boxplot": {
            "available": boxplot_available,
            "message": ""
            if boxplot_available
            else f"Boxplot general no disponible: target {target} no tiene valores numéricos válidos.",
        },
        "probability": {
            "available": probability_available,
            "message": ""
            if probability_available
            else f"Probability plot no disponible: menos de {probability_min_samples} valores válidos.",
        },
    }


def _empty_domain_payload(message: str = "") -> dict[str, object]:
    return {"enabled": False, "labels": [], "values": [], "message": message, "valid_rows": 0, "valid_categories": 0}


def _compute_target_statistics(clean, total: int) -> dict[str, float]:
    """Compute descriptive target metrics while preserving output contract."""
    if clean.empty:
        null_pct = float(((total - len(clean)) / total) * 100.0) if total else 0.0
        return {
            "valid_count": 0.0,
            "null_pct": null_pct,
            "mean": math.nan,
            "std": math.nan,
            "cv": math.nan,
            "min": math.nan,
            "p10": math.nan,
            "p25": math.nan,
            "p50": math.nan,
            "p75": math.nan,
            "p90": math.nan,
            "max": math.nan,
            "skewness": math.nan,
        }
    mean = float(clean.mean())
    std = float(clean.std())
    return {
        "valid_count": float(len(clean)),
        "null_pct": float(((total - len(clean)) / total) * 100.0) if total else 0.0,
        "mean": mean,
        "std": std,
        "cv": float(std / mean) if mean != 0 else 0.0,
        "min": float(clean.min()),
        "p10": float(clean.quantile(0.10)),
        "p25": float(clean.quantile(0.25)),
        "p50": float(clean.quantile(0.50)),
        "p75": float(clean.quantile(0.75)),
        "p90": float(clean.quantile(0.90)),
        "max": float(clean.max()),
        "skewness": float(clean.skew()) if len(clean) > 2 else math.nan,
    }


class GeostatService:
    def __init__(self, adapter: GeostatSpyAdapter, activity_log: ActivityLogService | None = None) -> None:
        self.adapter = adapter
        self.activity_log = activity_log or ActivityLogService()
        self.current_dataset: DatasetModel | None = None
        self.variable_config: VariableConfigModel | None = None
        self.workflow_state = WorkflowStateModel()
        self.autodetected_columns: dict[str, str] = {}

    def set_workflow_step(self, step_name: str) -> str:
        if step_name not in WORKFLOW_STEPS:
            return "Paso de workflow no válido."
        self.workflow_state.current_step = step_name
        self.activity_log.log("workflow_step_changed", "info", f"Paso activo: {step_name}", {"step": step_name})
        self.activity_log.log(STEP_EVENT_MAP[step_name], "info", f"Se abrió el paso {step_name}.", {"step": step_name})
        return f"Paso activo: {step_name} (funcional)."

    def get_workflow_step_status(self) -> list[tuple[str, str]]:
        self.activity_log.log("workflow_simplified_view_loaded", "info", "Workflow simplificado cargado.", {"steps": WORKFLOW_STEPS})
        return [(step, FUNCTIONAL_STATUS[step]) for step in WORKFLOW_STEPS]

    def get_available_columns(self) -> list[str]:
        return [] if self.current_dataset is None else self.current_dataset.columns

    def load_csv(self, file_path: str) -> LoadCsvResult:
        self.activity_log.log("csv_load_started", "info", "Iniciando carga de CSV.", {"file_path": file_path})
        selected_path = Path(file_path)
        if not selected_path.exists() or not selected_path.is_file():
            message = "No se pudo cargar el archivo."
            details = "La ruta seleccionada no existe o no es un archivo válido."
            self.activity_log.log("csv_load_failed", "error", message, {"file_path": file_path, "reason": details})
            return LoadCsvResult(False, message, details)

        try:
            dataframe = _read_csv(selected_path)
        except _csv_errors()[0]:
            return LoadCsvResult(False, "El archivo CSV está vacío.", "Selecciona un CSV con datos y vuelve a intentar.")
        except UnicodeDecodeError:
            try:
                dataframe = _read_csv_with_encoding(selected_path, "latin-1")
            except Exception as exc:
                return LoadCsvResult(False, "No se pudo leer el encoding del CSV.", f"Detalle técnico: {exc}")
        except _csv_errors()[1]:
            return LoadCsvResult(False, "El CSV no tiene un formato legible.", "Revisa separadores y estructura de columnas.")
        except Exception as exc:
            self.activity_log.log("app_error", "error", "Error inesperado leyendo CSV.", {"error": str(exc)})
            return LoadCsvResult(False, "Ocurrió un error inesperado al leer el CSV.", f"Detalle técnico: {exc}")

        if dataframe.empty:
            return LoadCsvResult(False, "El CSV no contiene filas de datos.", "Agrega al menos una fila y vuelve a cargar.")

        dataset = DatasetModel.from_dataframe(file_path=selected_path, dataframe=dataframe)
        self.current_dataset = dataset
        self.variable_config = None
        self._clear_cutoff_state()
        self._clear_dynamic_cutoff_state()
        self._clear_domain_state()
        self.autodetected_columns = self.autodetect_columns(dataset.columns, dataset.dataframe)
        self.activity_log.log("columns_autodetected", "info", "Columnas sugeridas automáticamente.", self.autodetected_columns)
        details = self._build_dataset_summary(dataset)
        self.activity_log.log("csv_load_succeeded", "success", "CSV cargado correctamente.", {"file": dataset.file_name})
        return LoadCsvResult(True, "CSV cargado correctamente.", details, dataset)

    def autodetect_columns(self, columns: list[str], dataframe) -> dict[str, str]:
        normalized = {_normalize_identifier(col): col for col in columns}

        def pick(candidates: list[str]) -> str:
            for candidate in candidates:
                normalized_candidate = _normalize_identifier(candidate)
                for key, original in normalized.items():
                    if len(normalized_candidate) == 1:
                        if key == normalized_candidate:
                            return original
                    elif key == normalized_candidate or key.startswith(normalized_candidate):
                        return original
            return ""

        suggestions = {
            "x": pick(["x", "easting", "east"]),
            "y": pick(["y", "northing", "north"]),
            "z": pick(["z", "elev", "elevation", "rl"]),
            "hole_id": pick(["holeid", "hole_id", "dhid", "drillhole"]),
            "domain": pick(["domain", "lito", "litho", "lithology", "zone"]),
        }

        numeric_candidates: list[str] = []
        for col in columns:
            if _is_numeric_dtype(dataframe[col]) and col not in {suggestions["x"], suggestions["y"], suggestions["z"]}:
                numeric_candidates.append(col)
        suggestions["target"] = numeric_candidates[0] if numeric_candidates else ""
        return suggestions

    def get_autodetected_columns(self) -> dict[str, str]:
        return self.autodetected_columns.copy()

    def get_domain_candidate_columns(self) -> list[str]:
        if self.current_dataset is None:
            return []
        domain_columns: list[str] = []
        for column in self.current_dataset.columns:
            if not _is_numeric_dtype(self.current_dataset.dataframe[column]):
                domain_columns.append(column)
        return domain_columns

    def get_domain_layer_candidates(self, max_low_cardinality: int = 20) -> list[str]:
        if self.current_dataset is None:
            return []
        df = self.current_dataset.dataframe
        candidates: list[str] = []
        for column in self.current_dataset.columns:
            series = df[column]
            is_explicit_category = str(series.dtype) == "category"
            distinct = int(series.nunique(dropna=True))
            is_low_cardinality_numeric = _is_numeric_dtype(series) and 1 < distinct <= max_low_cardinality
            if is_explicit_category or (not _is_numeric_dtype(series)) or is_low_cardinality_numeric:
                candidates.append(column)
        return candidates

    def configure_domains(self, ordered_layers: list[str], active_layers: list[str], min_samples: int = 1, include_missing: bool = False) -> CutoffResult:
        if self.current_dataset is None:
            return CutoffResult(False, "No hay dataset cargado.")
        if self.variable_config is None:
            return CutoffResult(False, "Configura X/Y/Z/target antes de definir dominios.")
        allowed = set(self.get_domain_layer_candidates())
        unique_ordered: list[str] = []
        for layer in ordered_layers[:3]:
            if layer and layer in allowed and layer not in unique_ordered:
                unique_ordered.append(layer)
        active_unique = [layer for layer in active_layers if layer in unique_ordered][:3]
        if not active_unique:
            self.workflow_state.domain_layers_order = unique_ordered
            self.workflow_state.domain_active_layers = []
            self.workflow_state.domain_output_column = ""
            self.workflow_state.domain_min_samples = max(1, int(min_samples))
            self.workflow_state.domain_include_missing = bool(include_missing)
            self.workflow_state.active_domain = "No definido"
            return CutoffResult(True, "Constructor de dominios actualizado (sin capas activas).")

        output_column = "domain_composite"
        frame = self.current_dataset.dataframe
        text_layers = frame[active_unique].copy()
        missing_mask = None
        for layer in active_unique:
            layer_values = text_layers[layer]
            mask = layer_values.map(_is_missing_category)
            missing_mask = mask if missing_mask is None else (missing_mask | mask)
            text_layers[layer] = layer_values.map(
                lambda value: f"{layer}_Missing" if _is_missing_category(value) else f"{layer}_{str(value).strip()}"
            )

        composed = text_layers.agg(" | ".join, axis=1)
        if include_missing:
            frame[output_column] = composed
        else:
            frame[output_column] = composed.where(~missing_mask, other=None)
        if output_column not in self.current_dataset.columns:
            self.current_dataset.columns.append(output_column)
            self.current_dataset.column_count = len(self.current_dataset.columns)

        self.workflow_state.domain_layers_order = unique_ordered
        self.workflow_state.domain_active_layers = active_unique
        self.workflow_state.domain_output_column = output_column
        self.workflow_state.domain_min_samples = max(1, int(min_samples))
        self.workflow_state.domain_include_missing = bool(include_missing)
        self.workflow_state.active_domain = " | ".join(active_unique)
        self.activity_log.log(
            "domain_configuration_applied",
            "success",
            "Configuración de dominios aplicada.",
            {
                "ordered_layers": unique_ordered,
                "active_layers": active_unique,
                "output_column": output_column,
                "min_samples": self.workflow_state.domain_min_samples,
                "include_missing": bool(include_missing),
            },
        )
        return CutoffResult(True, "Dominios actualizados correctamente.")

    def get_domain_state(self) -> dict[str, object]:
        return {
            "ordered_layers": list(self.workflow_state.domain_layers_order),
            "active_layers": list(self.workflow_state.domain_active_layers),
            "output_column": self.workflow_state.domain_output_column,
            "min_samples": int(self.workflow_state.domain_min_samples),
            "include_missing": bool(self.workflow_state.domain_include_missing),
            "effective_target_column": self._get_effective_target_column(),
            "capping_confirmed": bool(self.has_confirmed_dynamic_capping()),
        }

    def prepare_domain_statistics(self) -> dict[str, object]:
        if self.current_dataset is None or self.variable_config is None:
            raise ValueError("No hay dataset/configuración suficiente para Dominios.")
        output_column = self.workflow_state.domain_output_column
        active_layers = list(self.workflow_state.domain_active_layers)
        if not output_column or output_column not in self.current_dataset.dataframe.columns or not active_layers:
            return {"items": [], "selection_column": output_column, "active_layers": active_layers}

        target_column = self._get_effective_target_column()
        df = self.current_dataset.dataframe[[output_column, target_column]].copy()
        df[target_column] = _to_numeric(df[target_column])
        df = df.dropna(subset=[output_column, target_column])
        if df.empty:
            return {"items": [], "selection_column": output_column, "active_layers": active_layers}

        total = len(df)
        min_samples = max(1, int(self.workflow_state.domain_min_samples))
        items: list[dict[str, object]] = []
        grouped = df.groupby(output_column, dropna=False)
        for domain_name, chunk in grouped:
            count = int(len(chunk))
            if count < min_samples:
                continue
            mean_val = float(chunk[target_column].mean())
            std_val = float(chunk[target_column].std(ddof=0))
            cv_val = float(std_val / mean_val) if mean_val != 0 else 0.0
            indexes = [int(index) for index in chunk.index.tolist()]
            items.append(
                {
                    "domain": str(domain_name),
                    "count": count,
                    "mean": mean_val,
                    "std": std_val,
                    "cv": cv_val,
                    "pct_total": float((count / total) * 100.0),
                    "indexes": indexes,
                    "primary_group": str(domain_name).split(" | ")[0],
                }
            )
        items.sort(key=lambda row: row["mean"])
        return {
            "items": items,
            "selection_column": output_column,
            "active_layers": active_layers,
            "target_column": target_column,
            "total_rows": int(total),
            "min_samples": min_samples,
        }

    def set_variable_config(
        self,
        x_column: str,
        y_column: str,
        z_column: str,
        target_column: str,
        hole_id_column: str | None = None,
        domain_column: str | None = None,
    ) -> ColumnSelectionResult:
        if self.current_dataset is None:
            return ColumnSelectionResult(False, "Primero debes cargar un CSV.", "No hay dataset cargado.")
        selected = [x_column, y_column, z_column, target_column]
        if any(not value for value in selected):
            return ColumnSelectionResult(False, "Debes seleccionar X, Y, Z y variable objetivo.", "Configuración incompleta.")
        invalid = [col for col in selected if col not in self.current_dataset.columns]
        if invalid:
            return ColumnSelectionResult(False, "La selección contiene columnas no válidas.", f"Columnas inválidas: {', '.join(invalid)}")

        self.variable_config = VariableConfigModel(x_column, y_column, z_column, target_column, hole_id_column, domain_column)
        self.workflow_state.active_domain = f"Columna: {domain_column}" if domain_column else "No definido"
        self.workflow_state.active_support = "Muestra original"
        self._clear_cutoff_state()
        self._clear_dynamic_cutoff_state()
        self._clear_domain_state()
        self.workflow_state.effective_target_column = target_column
        self.activity_log.log("variable_config_applied", "success", "Configuración de variables aplicada.", {"target": target_column, "domain": domain_column or ""})
        return ColumnSelectionResult(True, "Configuración de variables guardada.", self.build_eda_summary())

    def get_numeric_columns(self) -> list[str]:
        if self.current_dataset is None:
            return []
        numeric_columns: list[str] = []
        for column in self.current_dataset.columns:
            if _is_numeric_dtype(self.current_dataset.dataframe[column]):
                numeric_columns.append(column)
        return numeric_columns

    def get_cutoff_state(self) -> dict[str, object]:
        default_target = self.variable_config.target_column if self.variable_config else ""
        return {
            "enabled": self.workflow_state.cutoffs_enabled,
            "target_column": self.workflow_state.cutoff_target_column or default_target,
            "limits": [float(v) for v in self.workflow_state.cutoff_limits],
            "labels": list(self.workflow_state.cutoff_labels),
            "output_column": self.workflow_state.cutoff_output_column,
            "effective_target_column": self._get_effective_target_column(),
            "dynamic_enabled": self.workflow_state.dynamic_cutoff_enabled,
            "dynamic_target_column": self.workflow_state.dynamic_cutoff_target_column or default_target,
            "dynamic_mode": self.workflow_state.dynamic_cutoff_mode,
            "dynamic_percent": float(self.workflow_state.dynamic_cutoff_percent),
            "dynamic_cutoff_value": float(self.workflow_state.dynamic_cutoff_value),
            "dynamic_output_column": self.workflow_state.dynamic_cutoff_output_column,
            "dynamic_category_column": self.workflow_state.dynamic_cutoff_category_column,
        }

    def has_confirmed_dynamic_capping(self) -> bool:
        return bool(self.workflow_state.dynamic_cutoff_enabled and self.workflow_state.dynamic_cutoff_output_column)

    def prepare_dynamic_cutoff_preview(self, target_column: str, mode: str, slider_percent: float) -> dict[str, object]:
        if self.current_dataset is None:
            raise ValueError("No hay dataset cargado.")
        if target_column not in self.current_dataset.columns:
            raise ValueError("La variable seleccionada no existe en el dataset.")

        numeric = _to_numeric(self.current_dataset.dataframe[target_column]).dropna().astype(float)
        if numeric.empty:
            raise ValueError("La variable seleccionada no tiene valores numéricos válidos.")

        values = numeric.tolist()
        min_val = float(numeric.min())
        max_val = float(numeric.max())
        slider_clamped = max(0.0, min(100.0, float(slider_percent)))
        if mode == "absolute":
            cutoff = min_val + ((max_val - min_val) * (slider_clamped / 100.0))
        else:
            cutoff = float(numeric.quantile(slider_clamped / 100.0))

        retained = numeric[numeric <= cutoff]
        truncated = numeric[numeric > cutoff]
        capped = numeric.clip(upper=cutoff)
        capped_max = float(min(max_val, cutoff))
        percentile_at_cutoff = float((numeric <= cutoff).sum() / len(numeric) * 100.0)

        sorted_vals = sorted(values)
        n = len(sorted_vals)
        normal = statistics.NormalDist()
        theoretical = [normal.inv_cdf((idx + 0.5) / n) for idx in range(n)] if n > 1 else [0.0]

        return {
            "values": values,
            "sorted_values": sorted_vals,
            "theoretical_quantiles": theoretical,
            "cutoff_value": float(cutoff),
            "min": min_val,
            "max": max_val,
            "affected_count": int(len(truncated)),
            "affected_pct": float((len(truncated) / len(values)) * 100.0),
            "retained_pct": percentile_at_cutoff,
            "retained_values": retained.tolist(),
            "truncated_values": truncated.tolist(),
            "capped_values": capped.tolist(),
            "max_original": max_val,
            "max_truncated": capped_max,
        }

    def apply_dynamic_cutoff(
        self,
        enabled: bool,
        target_column: str,
        mode: str,
        slider_percent: float,
        output_column: str | None = None,
        keep_category_column: bool = True,
    ) -> DynamicCutoffResult:
        if self.current_dataset is None:
            return DynamicCutoffResult(False, "No hay dataset cargado.")
        if self.variable_config is None:
            return DynamicCutoffResult(False, "Configura X/Y/Z/target antes de aplicar capping.")
        if not enabled:
            self._clear_dynamic_cutoff_state()
            return DynamicCutoffResult(True, "Capping dinámico desactivado.")

        try:
            preview = self.prepare_dynamic_cutoff_preview(target_column, mode, slider_percent)
        except ValueError as exc:
            return DynamicCutoffResult(False, str(exc))

        cutoff = float(preview["cutoff_value"])
        out_col = (output_column or f"{target_column}_capped").strip()
        if out_col in {self.variable_config.x_column, self.variable_config.y_column, self.variable_config.z_column}:
            return DynamicCutoffResult(False, "El nombre de salida no puede sobrescribir X/Y/Z.")

        source = _to_numeric(self.current_dataset.dataframe[target_column])
        self.current_dataset.dataframe[out_col] = source.clip(upper=cutoff)
        if out_col not in self.current_dataset.columns:
            self.current_dataset.columns.append(out_col)
            self.current_dataset.column_count = len(self.current_dataset.columns)

        category_col = ""
        if keep_category_column:
            category_col = f"{out_col}_class"
            labels = [f"<= {self._format_cutoff_number(cutoff)}", f"> {self._format_cutoff_number(cutoff)}"]
            import pandas as pd

            self.current_dataset.dataframe[category_col] = pd.cut(source, bins=[-math.inf, cutoff, math.inf], labels=labels, right=True, include_lowest=True)
            if category_col not in self.current_dataset.columns:
                self.current_dataset.columns.append(category_col)
                self.current_dataset.column_count = len(self.current_dataset.columns)

        self.workflow_state.dynamic_cutoff_enabled = True
        self.workflow_state.dynamic_cutoff_target_column = target_column
        self.workflow_state.dynamic_cutoff_mode = "absolute" if mode == "absolute" else "percentile"
        self.workflow_state.dynamic_cutoff_percent = float(max(0.0, min(100.0, slider_percent)))
        self.workflow_state.dynamic_cutoff_value = cutoff
        self.workflow_state.dynamic_cutoff_output_column = out_col
        self.workflow_state.dynamic_cutoff_category_column = category_col
        self.workflow_state.effective_target_column = out_col
        self.activity_log.log(
            "dynamic_cutoff_applied",
            "success",
            "Capping dinámico aplicado.",
            {
                "target": target_column,
                "mode": self.workflow_state.dynamic_cutoff_mode,
                "slider_percent": self.workflow_state.dynamic_cutoff_percent,
                "cutoff_value": cutoff,
                "output_column": out_col,
                "category_column": category_col,
            },
        )
        return DynamicCutoffResult(True, f"Capping aplicado. Nueva variable: {out_col}", cutoff)

    def apply_cutoffs(self, enabled: bool, target_column: str, limits_text: str, output_column: str | None = None) -> CutoffResult:
        if self.current_dataset is None:
            return CutoffResult(False, "No hay dataset cargado.")
        if self.variable_config is None:
            return CutoffResult(False, "Configura X/Y/Z/target antes de aplicar cutoffs.")

        if not enabled:
            self._clear_cutoff_state()
            self.workflow_state.effective_target_column = self.variable_config.target_column
            self.activity_log.log("cutoff_disabled", "info", "Cutoffs desactivados. Se usa target original.", {"target": self.variable_config.target_column})
            return CutoffResult(True, "Cutoffs desactivados. Se mantiene variable original.")

        if target_column not in self.current_dataset.columns:
            return CutoffResult(False, "La variable seleccionada no existe en el dataset.")
        if not _is_numeric_dtype(self.current_dataset.dataframe[target_column]):
            return CutoffResult(False, "La variable seleccionada debe ser numérica.")

        limits, parse_error = self._parse_cutoff_limits(limits_text)
        if parse_error:
            return CutoffResult(False, parse_error)

        labels = self._build_cutoff_labels(limits)
        output_name = (output_column or f"{target_column}_cutoff").strip()
        if output_name in {self.variable_config.x_column, self.variable_config.y_column, self.variable_config.z_column}:
            return CutoffResult(False, "El nombre de salida no puede sobrescribir X/Y/Z.")

        import pandas as pd

        source = _to_numeric(self.current_dataset.dataframe[target_column])
        bins = [-math.inf, *limits, math.inf]
        categorized = pd.cut(source, bins=bins, labels=labels, right=False, include_lowest=True)
        self.current_dataset.dataframe[output_name] = categorized
        if output_name not in self.current_dataset.columns:
            self.current_dataset.columns.append(output_name)
            self.current_dataset.column_count = len(self.current_dataset.columns)

        self.workflow_state.cutoffs_enabled = True
        self.workflow_state.cutoff_target_column = target_column
        self.workflow_state.cutoff_limits = [float(v) for v in limits]
        self.workflow_state.cutoff_labels = labels
        self.workflow_state.cutoff_output_column = output_name
        self.workflow_state.effective_target_column = output_name
        self.activity_log.log(
            "cutoff_applied",
            "success",
            "Cutoffs aplicados y variable categorizada persistida.",
            {"target": target_column, "output_column": output_name, "limits": limits, "labels": labels},
        )
        return CutoffResult(True, f"Cutoffs aplicados. Nueva variable: {output_name}")

    def _parse_cutoff_limits(self, limits_text: str) -> tuple[list[float], str]:
        raw = (limits_text or "").strip()
        if not raw:
            return [], "Debes ingresar al menos un cutoff."
        tokens = [token for token in raw.replace(";", ",").split(",") if token.strip()]
        if not tokens:
            return [], "Debes ingresar al menos un cutoff válido."
        values: list[float] = []
        for token in tokens:
            try:
                values.append(float(token.strip()))
            except ValueError:
                return [], f"Cutoff inválido: '{token.strip()}'. Usa solo números."
        unique_sorted = sorted(set(values))
        if not unique_sorted:
            return [], "No se detectaron cutoffs válidos."
        if len(unique_sorted) < len(values):
            self.activity_log.log("cutoff_duplicates_ignored", "warning", "Se ignoraron cutoffs repetidos.", {"input_count": len(values), "unique_count": len(unique_sorted)})
        return unique_sorted, ""

    def _build_cutoff_labels(self, limits: list[float]) -> list[str]:
        if len(limits) == 1:
            c0 = self._format_cutoff_number(limits[0])
            return [f"< {c0}", f">= {c0}"]

        labels: list[str] = [f"< {self._format_cutoff_number(limits[0])}"]
        for left, right in zip(limits[:-1], limits[1:]):
            labels.append(f"[{self._format_cutoff_number(left)}, {self._format_cutoff_number(right)})")
        labels.append(f">= {self._format_cutoff_number(limits[-1])}")
        return labels

    def _format_cutoff_number(self, value: float) -> str:
        return f"{value:.6g}"

    def _clear_cutoff_state(self) -> None:
        self.workflow_state.cutoffs_enabled = False
        self.workflow_state.cutoff_target_column = ""
        self.workflow_state.cutoff_limits = []
        self.workflow_state.cutoff_labels = []
        self.workflow_state.cutoff_output_column = ""
        self.workflow_state.effective_target_column = ""

    def _clear_dynamic_cutoff_state(self) -> None:
        self.workflow_state.dynamic_cutoff_enabled = False
        self.workflow_state.dynamic_cutoff_target_column = ""
        self.workflow_state.dynamic_cutoff_mode = "percentile"
        self.workflow_state.dynamic_cutoff_percent = 95.0
        self.workflow_state.dynamic_cutoff_value = 0.0
        self.workflow_state.dynamic_cutoff_output_column = ""
        self.workflow_state.dynamic_cutoff_category_column = ""

    def _clear_domain_state(self) -> None:
        self.workflow_state.domain_layers_order = []
        self.workflow_state.domain_active_layers = []
        self.workflow_state.domain_output_column = ""
        self.workflow_state.domain_min_samples = 1
        self.workflow_state.domain_include_missing = False

    def _get_effective_target_column(self) -> str:
        if self.workflow_state.dynamic_cutoff_enabled and self.workflow_state.dynamic_cutoff_output_column:
            return self.workflow_state.dynamic_cutoff_output_column
        if self.workflow_state.cutoffs_enabled and self.workflow_state.cutoff_output_column:
            return self.workflow_state.cutoff_output_column
        if self.variable_config is None:
            return ""
        return self.variable_config.target_column

    def prepare_visual_data(self) -> VisualPreparationResult:
        self.activity_log.log("dashboard_render_started", "info", "Render espacial iniciado.", {"view": "Espacial"})
        if self.current_dataset is None or self.variable_config is None:
            message = "No hay dataset/configuración suficiente para renderizar visuales."
            self.activity_log.log("dashboard_render_failed", "error", message, {"view": "Espacial"})
            return VisualPreparationResult(False, message, None)
        try:
            spatial = prepare_spatial_sections(
                self.current_dataset.dataframe,
                self.variable_config.x_column,
                self.variable_config.y_column,
                self.variable_config.z_column,
                self._get_effective_target_column(),
                allow_categorical_target=self.workflow_state.cutoffs_enabled,
            )
        except ValueError as exc:
            self.activity_log.log("dashboard_render_failed", "error", str(exc), {"view": "Espacial"})
            return VisualPreparationResult(False, str(exc), None)

        self.activity_log.log(
            "spatial_2d_rendered",
            "success",
            "Vistas espaciales 2D preparadas.",
            {"rows": len(spatial.target), "target_column": self._get_effective_target_column()},
        )
        self.activity_log.log("dashboard_render_finished", "success", "Render espacial finalizado.", {"view": "Espacial"})
        return VisualPreparationResult(True, "Visuales preparados.", spatial)

    def prepare_univariate_data(self, max_domain_categories: int = 10, use_effective_target: bool = False) -> dict:
        if self.current_dataset is None or self.variable_config is None:
            message = "No hay dataset/configuración suficiente para EDA."
            self.activity_log.log("eda_univariate_payload_empty", "warning", message, {})
            self.activity_log.log("univariate_payload_empty", "warning", message, {})
            raise ValueError(message)

        df = self.current_dataset.dataframe
        target = self._get_effective_target_column() if use_effective_target else self.variable_config.target_column
        if not target or target not in df.columns:
            message = f"Target no válido para EDA univariado: '{target}'."
            self.activity_log.log("eda_univariate_payload_empty", "warning", message, {"target": target})
            self.activity_log.log("univariate_payload_empty", "warning", message, {"target": target})
            raise ValueError(message)

        numeric_target = _to_numeric(df[target])
        total_rows = int(len(df))
        valid_count = int(numeric_target.notna().sum())
        nan_count = int(total_rows - valid_count)

        self.activity_log.log(
            "eda_target_coerced_numeric",
            "info",
            "Target convertido a numérico para EDA univariado.",
            {"target": target, "total_rows": total_rows, "valid_count": valid_count, "nan_count": nan_count},
        )
        self.activity_log.log(
            "eda_target_valid_count_computed",
            "info",
            "Conteo de target válido calculado.",
            {"target": target, "valid_count": valid_count, "nan_count": nan_count},
        )

        clean_target = numeric_target.dropna().astype(float)

        probability_min_samples = 3
        availability = _build_univariate_availability(target, valid_count, probability_min_samples=probability_min_samples)
        histogram_available = bool(availability["histogram"]["available"])
        boxplot_available = bool(availability["boxplot"]["available"])
        probability_available = bool(availability["probability"]["available"])

        for key, event_name, detail in [
            ("histogram", "univariate_histogram_available", "histograma"),
            ("boxplot", "univariate_boxplot_available", "boxplot general"),
            ("probability", "univariate_probability_available", "probability plot"),
        ]:
            if availability[key]["available"]:
                self.activity_log.log(event_name, "info", f"{detail.capitalize()} disponible.", {"target": target, "valid_count": valid_count})
            else:
                self.activity_log.log(
                    "univariate_component_unavailable",
                    "warning",
                    availability[key]["message"],
                    {"component": key, "target": target, "valid_count": valid_count},
                )

        if not (histogram_available or boxplot_available or probability_available):
            message = f"No hay valores numéricos válidos para target {target}."
            self.activity_log.log("eda_univariate_payload_empty", "warning", message, {"target": target})
            self.activity_log.log("univariate_payload_empty", "warning", message, {"target": target})
            raise ValueError(message)

        sorted_vals = sorted(clean_target.tolist())
        n = len(sorted_vals)
        qq_x: list[float] = []
        qq_y: list[float] = []
        probability_failed = False
        if probability_available:
            try:
                normal = statistics.NormalDist()
                qq_x = [normal.inv_cdf((idx + 0.5) / n) for idx in range(n)]
                qq_y = sorted_vals
                self.activity_log.log("probability_plot_rendered", "info", "Probability plot preparado.", {"n": n})
            except Exception as exc:
                probability_failed = True
                availability["probability"] = {
                    "available": False,
                    "message": f"Probability plot no disponible: error al calcular cuantiles ({exc}).",
                }
                self.activity_log.log("probability_plot_failed", "error", str(exc), {"n": n})
                self.activity_log.log(
                    "univariate_component_unavailable",
                    "warning",
                    availability["probability"]["message"],
                    {"component": "probability", "target": target, "valid_count": valid_count},
                )

        domain_payload = _empty_domain_payload()
        domain_col = self.variable_config.domain_column
        if not domain_col:
            domain_payload["message"] = "Boxplot por dominio no disponible: no hay dominio seleccionado."
            self.activity_log.log("univariate_component_unavailable", "warning", domain_payload["message"], {"component": "domain_boxplot", "target": target})
        elif domain_col not in df.columns:
            domain_payload["message"] = f"Boxplot por dominio no disponible: columna {domain_col} no encontrada."
            self.activity_log.log(
                "univariate_component_unavailable", "warning", domain_payload["message"], {"component": "domain_boxplot", "target": target, "domain": domain_col}
            )
        else:
            try:
                domain_df = df[[domain_col]].copy()
                domain_df["target"] = numeric_target
                domain_df = domain_df.dropna(subset=["target", domain_col])
                valid_rows = int(len(domain_df))
                valid_categories = int(domain_df[domain_col].nunique()) if valid_rows else 0
                self.activity_log.log(
                    "eda_domain_valid_count_computed",
                    "info",
                    "Conteo de dominio válido calculado.",
                    {"domain": domain_col, "valid_rows": valid_rows, "valid_categories": valid_categories},
                )
                if not domain_df.empty:
                    counts = domain_df[domain_col].value_counts()
                    top = counts.head(max_domain_categories)
                    selected_categories = top.index.tolist()
                    labels = [str(v) for v in selected_categories]
                    grouped_values = [domain_df.loc[domain_df[domain_col] == cat, "target"].astype(float).tolist() for cat in selected_categories]
                    labels = [lbl for lbl, vals in zip(labels, grouped_values) if vals]
                    grouped_values = [vals for vals in grouped_values if vals]
                    simplified = len(counts) > max_domain_categories
                    domain_payload = {
                        "enabled": bool(labels and grouped_values),
                        "labels": labels,
                        "values": grouped_values,
                        "message": "" if not simplified else f"Mostrando top {max_domain_categories} categorías por frecuencia.",
                        "valid_rows": valid_rows,
                        "valid_categories": valid_categories,
                    }
                    if domain_payload["enabled"]:
                        self.activity_log.log(
                            "univariate_domain_boxplot_available",
                            "info",
                            "Boxplot por dominio disponible.",
                            {"domain": domain_col, "categories": len(labels), "valid_rows": valid_rows},
                        )
                        self.activity_log.log("eda_domain_boxplot_rendered", "info", "Boxplot por dominio preparado.", {"categories": len(labels)})
                        self.activity_log.log("domain_boxplot_rendered", "info", "Boxplot por dominio renderizable preparado.", {"categories": len(labels)})
                        if simplified:
                            self.activity_log.log("domain_boxplot_simplified", "info", "Boxplot por dominio simplificado a top categorías.", {"max_categories": max_domain_categories})
                    else:
                        domain_payload["message"] = f"Boxplot por dominio no disponible: {domain_col} no tiene categorías válidas con target numérico."
                        self.activity_log.log(
                            "univariate_component_unavailable",
                            "warning",
                            domain_payload["message"],
                            {"component": "domain_boxplot", "domain": domain_col, "valid_rows": valid_rows},
                        )
                else:
                    domain_payload = _empty_domain_payload(
                        message=f"Boxplot por dominio no disponible: {domain_col} no tiene filas válidas con target numérico."
                    )
                    domain_payload["valid_rows"] = valid_rows
                    domain_payload["valid_categories"] = valid_categories
                    self.activity_log.log(
                        "univariate_component_unavailable",
                        "warning",
                        domain_payload["message"],
                        {"component": "domain_boxplot", "domain": domain_col, "valid_rows": valid_rows},
                    )
            except Exception as exc:
                self.activity_log.log("domain_boxplot_failed", "error", str(exc), {"domain": domain_col})
                domain_payload["message"] = f"Boxplot por dominio no disponible: error al preparar dominio ({exc})."
                self.activity_log.log(
                    "univariate_component_unavailable",
                    "warning",
                    domain_payload["message"],
                    {"component": "domain_boxplot", "domain": domain_col},
                )

        payload = {
            "target_values": clean_target.tolist(),
            "probplot_x": qq_x,
            "probplot_y": qq_y,
            "probability_failed": probability_failed,
            "domain_boxplot": domain_payload,
            "availability": availability,
            "diagnostics": {
                "target": target,
                "domain": domain_col or "",
                "total_rows": total_rows,
                "target_valid_count": valid_count,
                "target_nan_count": nan_count,
                "domain_valid_rows": domain_payload.get("valid_rows", 0),
                "domain_valid_categories": domain_payload.get("valid_categories", 0),
            },
        }
        self.activity_log.log("univariate_payload_built", "success", "Payload univariado construido.", payload["diagnostics"])
        self.activity_log.log(
            "eda_univariate_payload_prepared",
            "success",
            "Payload univariado preparado.",
            {
                "rows": len(clean_target),
                "domain_enabled": bool(domain_payload["enabled"]),
                "probability_failed": probability_failed,
            },
        )
        return payload

    def prepare_swath_data(self, bins: int = 20) -> dict[str, SwathSeries]:
        if self.current_dataset is None or self.variable_config is None:
            raise ValueError("No hay dataset/configuración suficiente para swath.")

        dataframe = self.current_dataset.dataframe
        target_col = self.variable_config.target_column
        if not target_col or target_col not in dataframe.columns:
            raise ValueError(f"Target no válido para swath: '{target_col}'.")

        payload = {
            "x": compute_swath_series(dataframe, self.variable_config.x_column, target_col, bins=bins),
            "y": compute_swath_series(dataframe, self.variable_config.y_column, target_col, bins=bins),
            "z": compute_swath_series(dataframe, self.variable_config.z_column, target_col, bins=bins),
        }
        self.activity_log.log("swath_payload_prepared", "success", "Series swath preparadas.", {"bins": bins, "target": target_col})
        return payload

    def build_eda_summary(self, use_effective_target: bool = False) -> str:
        if self.current_dataset is None:
            return "No hay dataset cargado para EDA."
        base = (
            "MÓDULO EDA\n"
            "----------\n"
            "Subsecciones: Resumen | Univariado\n"
            f"Filas: {self.current_dataset.row_count} | Columnas: {self.current_dataset.column_count}\n"
        )
        if self.variable_config is None:
            return base + "Selecciona X/Y/Z/target para habilitar estadísticas del target."
        target = self._get_effective_target_column() if use_effective_target else self.variable_config.target_column
        df = self.current_dataset.dataframe
        if target not in df.columns or not _is_numeric_dtype(df[target]):
            return base + "Target no numérico: estadísticas limitadas."
        stats = self._target_statistics(use_effective_target=use_effective_target)
        return base + f"Target {target}: válidos={stats['valid_count']} | nulos={stats['null_pct']:.2f}% | mean={stats['mean']:.4g}"

    def _target_statistics(self, use_effective_target: bool = False) -> dict[str, float]:
        target = self._get_effective_target_column() if use_effective_target else self.variable_config.target_column
        df = self.current_dataset.dataframe
        total = len(df)
        clean = df[target].dropna().astype(float)
        return _compute_target_statistics(clean, total)

    def get_target_statistics_table(self, use_effective_target: bool = False) -> list[tuple[str, str]]:
        if self.current_dataset is None or self.variable_config is None:
            return []
        target = self._get_effective_target_column() if use_effective_target else self.variable_config.target_column
        df = self.current_dataset.dataframe
        if target not in df.columns or not _is_numeric_dtype(df[target]):
            return []

        stats = self._target_statistics(use_effective_target=use_effective_target)
        return [
            ("dataset", self.current_dataset.file_name),
            ("samples", str(self.current_dataset.row_count)),
            ("columns", str(self.current_dataset.column_count)),
            ("target", target),
            ("valid_count", str(int(stats["valid_count"]))),
            ("null_pct", f"{stats['null_pct']:.3g}"),
            ("mean", f"{stats['mean']:.5g}"),
            ("std", f"{stats['std']:.5g}"),
            ("cv", f"{stats['cv']:.5g}"),
            ("min", f"{stats['min']:.5g}"),
            ("p10", f"{stats['p10']:.5g}"),
            ("p25", f"{stats['p25']:.5g}"),
            ("p50", f"{stats['p50']:.5g}"),
            ("p75", f"{stats['p75']:.5g}"),
            ("p90", f"{stats['p90']:.5g}"),
            ("max", f"{stats['max']:.5g}"),
            ("skewness", f"{stats['skewness']:.5g}"),
        ]

    def get_summary_cards(self) -> dict[str, str]:
        if self.current_dataset is None:
            return {"Dataset": "No cargado", "Muestras": "0", "Columnas": "0", "Target": "No definido", "Estado": "Pendiente", "Dominio": "No definido"}

        target = self._get_effective_target_column() if self.variable_config else "No definido"
        return {
            "Dataset": self.current_dataset.file_name,
            "Muestras": str(self.current_dataset.row_count),
            "Columnas": str(self.current_dataset.column_count),
            "Target": target,
            "Estado": "Listo" if self.variable_config else "Configurar variables",
            "Dominio": self.workflow_state.active_domain,
        }

    def update_repository(self) -> RepoUpdateResult:
        if getattr(self, "_repo_update_running", False):
            return RepoUpdateResult(False, "Ya hay una actualización en curso.", "Espera a que finalice el proceso actual.", False)
        if self.workflow_state.current_step == "Datos" and self.dataframe_write_in_progress():
            return RepoUpdateResult(False, "Actualización no permitida durante escritura activa.", "Espera a que termine el proceso crítico y vuelve a intentar.", False)
        if os.getenv("GEOSTAT_ENABLE_RUNTIME_GIT_UPDATE", "0") != "1":
            message = "Actualización de repositorio deshabilitada en runtime por seguridad."
            details = "Cierra la app y ejecuta `python scripts/update_repo.py` desde terminal."
            self.activity_log.log("repo_update_blocked", "warning", message, {"recommended_command": "python scripts/update_repo.py"})
            return RepoUpdateResult(False, message, details, False)

        self._repo_update_running = True
        self.activity_log.log("repo_update_started", "info", "Iniciando actualización de repositorio.", {})
        try:
            pull_result = subprocess.run(["git", "pull"], cwd=PROJECT_ROOT, capture_output=True, text=True, check=False, timeout=120)
            if pull_result.returncode != 0:
                error_output = (pull_result.stderr or pull_result.stdout).strip()
                return RepoUpdateResult(False, "Falló `git pull`.", error_output or "Error desconocido de git.")

            submodule_result = subprocess.run(
                ["git", "submodule", "update", "--init", "--recursive"],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                check=False,
                timeout=120,
            )
            output = (pull_result.stdout or pull_result.stderr).strip()
            submodule_output = (submodule_result.stdout or submodule_result.stderr).strip()
            if submodule_result.returncode != 0:
                self.activity_log.log(
                    "repo_update_failed",
                    "error",
                    "Falló actualización de submódulos.",
                    {"command": "git submodule update --init --recursive", "details": submodule_output},
                )
                return RepoUpdateResult(False, "Falló actualización de submódulos.", submodule_output or "Error desconocido de submódulos.")
            combined = f"git pull:\n{output or '(sin salida)'}\n\nsubmodules:\n{submodule_output or '(sin cambios)'}"
            up_to_date = "Already up to date" in output or "Ya está actualizado" in output
            message = "Repositorio ya estaba actualizado." if up_to_date else "Repositorio actualizado correctamente. Reinicia la app para aplicar cambios."
            self.activity_log.log("repo_update_finished", "success", message, {"restart_recommended": not up_to_date})
            return RepoUpdateResult(True, message, combined, not up_to_date)
        except Exception as exc:
            return RepoUpdateResult(False, "No se pudo ejecutar la actualización del repositorio.", f"Detalle técnico: {exc}")
        finally:
            self._repo_update_running = False

    def dataframe_write_in_progress(self) -> bool:
        return bool(getattr(self, "_dataframe_write_in_progress", False))

    def export_activity_log(self, destination_path: str) -> str:
        exported = self.activity_log.export_log(destination_path)
        self.activity_log.log("export_log_requested", "success", "Log exportado correctamente.", {"destination": str(exported)})
        return str(exported)

    def module_not_implemented(self, module_name: str) -> str:
        message = f"{module_name}: etapa aún no implementada. Esta acción fue registrada."
        self.activity_log.log("placeholder_module_clicked", "info", message, {"module": module_name})
        return message


    def variogram_placeholder(self) -> str:
        return self.module_not_implemented("Variografía")

    def kriging_placeholder(self) -> str:
        return self.module_not_implemented("Kriging")

    def sgs_placeholder(self) -> str:
        return self.module_not_implemented("Simulación")

    def visualization_placeholder(self) -> str:
        return self.module_not_implemented("Espacial")

    def _build_dataset_summary(self, dataset: DatasetModel) -> str:
        dtypes = dataset.dataframe.dtypes.astype(str).to_dict()
        dtypes_text = "\n".join(f"• {k}: {v}" for k, v in dtypes.items())
        preview = dataset.preview_as_text()
        return (
            "ETAPA DATOS\n"
            "-----------\n"
            f"Archivo: {dataset.file_name}\n"
            f"Filas: {dataset.row_count} | Columnas: {dataset.column_count}\n"
            "Tipos de datos:\n"
            f"{dtypes_text}\n\n"
            "Preview:\n"
            f"{preview}"
        )
