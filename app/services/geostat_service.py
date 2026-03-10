"""Service layer for geostatistical workflows."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import math
import statistics
import subprocess

from app.adapters.geostatspy_adapter import GeostatSpyAdapter
from app.models.dataset_model import DatasetModel
from app.models.variable_config_model import VariableConfigModel
from app.models.workflow_state_model import WorkflowStateModel
from app.services.activity_log_service import ActivityLogService
from app.services.visualization_service import SpatialDataBundle, prepare_spatial_sections
from app.utils.paths import PROJECT_ROOT

WORKFLOW_STEPS = ["Datos", "EDA", "Espacial"]
FUNCTIONAL_STATUS = {step: "funcional" for step in WORKFLOW_STEPS}
STEP_EVENT_MAP = {
    "Datos": "workflow_step_data_opened",
    "EDA": "workflow_step_eda_opened",
    "Espacial": "workflow_step_spatial_opened",
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
        self.autodetected_columns = self.autodetect_columns(dataset.columns, dataset.dataframe)
        self.activity_log.log("columns_autodetected", "info", "Columnas sugeridas automáticamente.", self.autodetected_columns)
        details = self._build_dataset_summary(dataset)
        self.activity_log.log("csv_load_succeeded", "success", "CSV cargado correctamente.", {"file": dataset.file_name})
        return LoadCsvResult(True, "CSV cargado correctamente.", details, dataset)

    def autodetect_columns(self, columns: list[str], dataframe) -> dict[str, str]:
        normalized = {col.lower().replace("_", "").replace(" ", ""): col for col in columns}

        def pick(candidates: list[str]) -> str:
            for candidate in candidates:
                for key, original in normalized.items():
                    if candidate in key:
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
        self.activity_log.log("variable_config_applied", "success", "Configuración de variables aplicada.", {"target": target_column, "domain": domain_column or ""})
        return ColumnSelectionResult(True, "Configuración de variables guardada.", self.build_eda_summary())

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
                self.variable_config.target_column,
            )
        except ValueError as exc:
            self.activity_log.log("dashboard_render_failed", "error", str(exc), {"view": "Espacial"})
            return VisualPreparationResult(False, str(exc), None)

        self.activity_log.log("spatial_2d_rendered", "success", "Vistas espaciales 2D preparadas.", {"rows": len(spatial.target)})
        self.activity_log.log("dashboard_render_finished", "success", "Render espacial finalizado.", {"view": "Espacial"})
        return VisualPreparationResult(True, "Visuales preparados.", spatial)

    def prepare_univariate_data(self, max_domain_categories: int = 10) -> dict:
        if self.current_dataset is None or self.variable_config is None:
            message = "No hay dataset/configuración suficiente para EDA."
            self.activity_log.log("eda_univariate_payload_empty", "warning", message, {})
            raise ValueError(message)

        df = self.current_dataset.dataframe
        target = self.variable_config.target_column
        if target not in df.columns or not _is_numeric_dtype(df[target]):
            message = "Target no numérico para EDA univariado."
            self.activity_log.log("eda_univariate_payload_empty", "warning", message, {"target": target})
            raise ValueError(message)

        clean_target = df[target].dropna().astype(float)
        if clean_target.empty:
            message = "No hay suficientes datos válidos para renderizar Univariado."
            self.activity_log.log("eda_univariate_payload_empty", "warning", message, {"target": target})
            raise ValueError(message)

        sorted_vals = sorted(clean_target.tolist())
        n = len(sorted_vals)
        qq_x: list[float] = []
        qq_y: list[float] = []
        probability_failed = False
        try:
            normal = statistics.NormalDist()
            qq_x = [normal.inv_cdf((idx + 0.5) / n) for idx in range(n)]
            qq_y = sorted_vals
            self.activity_log.log("probability_plot_rendered", "info", "Probability plot preparado.", {"n": n})
        except Exception as exc:
            probability_failed = True
            self.activity_log.log("probability_plot_failed", "error", str(exc), {"n": n})

        domain_payload = {"enabled": False, "labels": [], "values": [], "message": ""}
        domain_col = self.variable_config.domain_column
        if domain_col and domain_col in df.columns:
            try:
                domain_df = df[[target, domain_col]].dropna()
                if not domain_df.empty:
                    counts = domain_df[domain_col].value_counts()
                    top = counts.head(max_domain_categories)
                    labels = [str(v) for v in top.index.tolist()]
                    grouped_values = [domain_df.loc[domain_df[domain_col] == label, target].astype(float).tolist() for label in top.index.tolist()]
                    grouped_values = [vals for vals in grouped_values if vals]
                    labels = [lbl for lbl, vals in zip(labels, [domain_df.loc[domain_df[domain_col] == label, target].astype(float).tolist() for label in top.index.tolist()]) if vals]
                    simplified = len(counts) > max_domain_categories
                    domain_payload = {
                        "enabled": bool(labels and grouped_values),
                        "labels": labels,
                        "values": grouped_values,
                        "message": "" if not simplified else f"Mostrando top {max_domain_categories} categorías por frecuencia.",
                    }
                    if domain_payload["enabled"]:
                        self.activity_log.log("eda_domain_boxplot_rendered", "info", "Boxplot por dominio preparado.", {"categories": len(labels)})
                        self.activity_log.log("domain_boxplot_rendered", "info", "Boxplot por dominio renderizable preparado.", {"categories": len(labels)})
                        if simplified:
                            self.activity_log.log("domain_boxplot_simplified", "info", "Boxplot por dominio simplificado a top categorías.", {"max_categories": max_domain_categories})
            except Exception as exc:
                self.activity_log.log("domain_boxplot_failed", "error", str(exc), {"domain": domain_col})

        payload = {
            "target_values": clean_target.tolist(),
            "probplot_x": qq_x,
            "probplot_y": qq_y,
            "probability_failed": probability_failed,
            "domain_boxplot": domain_payload,
        }
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

    def build_eda_summary(self) -> str:
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
        target = self.variable_config.target_column
        df = self.current_dataset.dataframe
        if target not in df.columns or not _is_numeric_dtype(df[target]):
            return base + "Target no numérico: estadísticas limitadas."
        stats = self._target_statistics()
        return base + f"Target {target}: válidos={stats['valid_count']} | nulos={stats['null_pct']:.2f}% | mean={stats['mean']:.4g}"

    def _target_statistics(self) -> dict[str, float]:
        target = self.variable_config.target_column
        df = self.current_dataset.dataframe
        total = len(df)
        clean = df[target].dropna().astype(float)
        return {
            "valid_count": float(len(clean)),
            "null_pct": float(((total - len(clean)) / total) * 100.0) if total else 0.0,
            "mean": float(clean.mean()),
            "std": float(clean.std()),
            "cv": float(clean.std() / clean.mean()) if float(clean.mean()) != 0 else 0.0,
            "min": float(clean.min()),
            "p10": float(clean.quantile(0.10)),
            "p25": float(clean.quantile(0.25)),
            "p50": float(clean.quantile(0.50)),
            "p75": float(clean.quantile(0.75)),
            "p90": float(clean.quantile(0.90)),
            "max": float(clean.max()),
            "skewness": float(clean.skew()) if len(clean) > 2 else math.nan,
        }

    def get_target_statistics_table(self) -> list[tuple[str, str]]:
        if self.current_dataset is None or self.variable_config is None:
            return []
        target = self.variable_config.target_column
        df = self.current_dataset.dataframe
        if target not in df.columns or not _is_numeric_dtype(df[target]):
            return []

        stats = self._target_statistics()
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

        target = self.variable_config.target_column if self.variable_config else "No definido"
        return {
            "Dataset": self.current_dataset.file_name,
            "Muestras": str(self.current_dataset.row_count),
            "Columnas": str(self.current_dataset.column_count),
            "Target": target,
            "Estado": "Listo" if self.variable_config else "Configurar variables",
            "Dominio": self.workflow_state.active_domain,
        }

    def update_repository(self) -> RepoUpdateResult:
        self.activity_log.log("repo_update_started", "info", "Iniciando actualización de repositorio.", {})
        try:
            pull_result = subprocess.run(["git", "pull"], cwd=PROJECT_ROOT, capture_output=True, text=True, check=False, timeout=120)
        except Exception as exc:
            return RepoUpdateResult(False, "No se pudo ejecutar la actualización del repositorio.", f"Detalle técnico: {exc}")

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
        combined = f"git pull:\n{output or '(sin salida)'}\n\nsubmodules:\n{submodule_output or '(sin cambios)'}"
        up_to_date = "Already up to date" in output or "Ya está actualizado" in output
        message = "Repositorio ya estaba actualizado." if up_to_date else "Repositorio actualizado correctamente. Reinicia la app para aplicar cambios."
        self.activity_log.log("repo_update_finished", "success", message, {"restart_recommended": not up_to_date})
        return RepoUpdateResult(True, message, combined, not up_to_date)

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
