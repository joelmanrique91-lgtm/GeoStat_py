"""Service layer for geostatistical workflows."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess

from app.adapters.geostatspy_adapter import GeostatSpyAdapter
from app.models.dataset_model import DatasetModel
from app.models.variable_config_model import VariableConfigModel
from app.models.workflow_state_model import WorkflowStateModel
from app.services.activity_log_service import ActivityLogService
from app.services.visualization_service import (
    SpatialDataBundle,
    SwathSeries,
    VariogramResult,
    compute_experimental_variogram,
    compute_swath_series,
    prepare_spatial_sections,
)
from app.utils.paths import PROJECT_ROOT

WORKFLOW_STEPS = [
    "Datos",
    "QA/QC",
    "EDA",
    "Espacial",
    "Variografía",
    "Kriging",
    "Simulación",
    "Validación",
    "Exportación",
]

FUNCTIONAL_STATUS = {
    "Datos": "funcional",
    "QA/QC": "parcial",
    "EDA": "funcional",
    "Espacial": "funcional",
    "Variografía": "funcional",
    "Kriging": "futuro",
    "Simulación": "futuro",
    "Validación": "futuro",
    "Exportación": "parcial",
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

    def set_workflow_step(self, step_name: str) -> str:
        if step_name not in WORKFLOW_STEPS:
            return "Paso de workflow no válido."
        self.workflow_state.current_step = step_name
        event_name = f"{step_name.lower().replace(' ', '_').replace('/', '_')}_opened"
        self.activity_log.log("workflow_step_changed", "info", f"Paso activo: {step_name}", {"step": step_name})
        self.activity_log.log(event_name, "info", f"Se abrió el paso {step_name}.", {"step": step_name})
        return f"Paso activo: {step_name} ({FUNCTIONAL_STATUS.get(step_name, 'futuro')})."

    def get_workflow_step_status(self) -> list[tuple[str, str]]:
        return [(step, FUNCTIONAL_STATUS.get(step, "futuro")) for step in WORKFLOW_STEPS]

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
        details = self._build_dataset_summary(dataset)
        self.activity_log.log("csv_load_succeeded", "success", "CSV cargado correctamente.", {"file": dataset.file_name})
        return LoadCsvResult(True, "CSV cargado correctamente.", details, dataset)

    def evaluate_data_quality(self) -> tuple[str, str]:
        if self.current_dataset is None:
            return "rojo", "No hay dataset cargado para evaluar calidad."
        df = self.current_dataset.dataframe
        missing_pct = float(df.isna().sum().sum()) / float(df.size) * 100.0 if df.size else 0.0
        duplicated_rows = int(df.duplicated().sum())
        coord_nulls = sum(int(df[c].isna().sum()) for c in ["x", "y", "z"] if c in df.columns)

        semaphore = "verde"
        if coord_nulls > 0:
            semaphore = "rojo"
        elif duplicated_rows > 0 or missing_pct > 5:
            semaphore = "amarillo"

        summary = (
            "QUALITY GATE INICIAL\n"
            f"Semáforo: {semaphore.upper()}\n"
            f"% faltantes: {missing_pct:.2f}%\n"
            f"Duplicados: {duplicated_rows}\n"
            f"Coordenadas nulas (x/y/z): {coord_nulls}\n"
            "Tratamiento de extremos (top-cut/capping): pendiente en siguiente iteración."
        )
        self.activity_log.log("data_quality_evaluated", "success", "Evaluación QA/QC ejecutada.", {"semaphore": semaphore})
        return semaphore, summary

    def prepare_visual_data(self) -> VisualPreparationResult:
        self.activity_log.log("dashboard_render_started", "info", "Render espacial iniciado.", {"view": "Espacial"})
        if self.current_dataset is None or self.variable_config is None:
            message = "No hay dataset/configuración suficiente para renderizar visuales."
            self.activity_log.log("graph_render_failed", "error", message, {"view": "Espacial"})
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
            self.activity_log.log("graph_render_failed", "error", str(exc), {"view": "Espacial"})
            self.activity_log.log("dashboard_render_failed", "error", str(exc), {"view": "Espacial"})
            return VisualPreparationResult(False, str(exc), None)

        if spatial.downsampled:
            self.activity_log.log(
                "visualization_downsampled",
                "info",
                "Vista espacial muestreada para rendimiento.",
                {"source_points": spatial.source_points, "plotted_points": spatial.plotted_points},
            )

        self.activity_log.log("eda_dashboard_rendered", "info", "Dashboard EDA preparado.", {"rows": len(spatial.target)})
        self.activity_log.log("spatial_dashboard_rendered", "info", "Dashboard espacial preparado.", {"rows": len(spatial.target)})
        self.activity_log.log("section_view_rendered", "info", "Secciones XY/XZ/YZ preparadas.", {})
        self.activity_log.log("dashboard_render_finished", "success", "Render espacial finalizado.", {"view": "Espacial"})
        return VisualPreparationResult(True, "Visuales preparados.", spatial)

    def prepare_swath_data(self, bins: int = 20) -> dict[str, SwathSeries]:
        self.activity_log.log("dashboard_render_started", "info", "Render swath iniciado.", {"view": "Swath"})
        if self.current_dataset is None or self.variable_config is None:
            message = "No hay dataset/configuración suficiente para swath."
            self.activity_log.log("dashboard_render_failed", "error", message, {"view": "Swath"})
            raise ValueError(message)

        df = self.current_dataset.dataframe
        target = self.variable_config.target_column
        result = {
            "X": compute_swath_series(df, self.variable_config.x_column, target, bins=bins),
            "Y": compute_swath_series(df, self.variable_config.y_column, target, bins=bins),
            "Z": compute_swath_series(df, self.variable_config.z_column, target, bins=bins),
        }
        self.activity_log.log("swath_rendered", "success", "Swath plots preparados.", {"bins": bins})
        self.activity_log.log("dashboard_render_finished", "success", "Render swath finalizado.", {"view": "Swath"})
        return result

    def prepare_variogram_data(self, lag: float, n_lags: int, max_distance: float, mode: str = "omnidireccional") -> VariogramResult:
        self.activity_log.log("dashboard_render_started", "info", "Render variograma iniciado.", {"view": "Variografía"})
        if self.current_dataset is None or self.variable_config is None:
            message = "No hay dataset/configuración suficiente para variograma."
            self.activity_log.log("dashboard_render_failed", "error", message, {"view": "Variografía"})
            raise ValueError(message)

        self.activity_log.log("variogram_started", "info", "Cálculo de variograma iniciado.", {"mode": mode})
        try:
            result = compute_experimental_variogram(
                self.current_dataset.dataframe,
                self.variable_config.x_column,
                self.variable_config.y_column,
                self.variable_config.z_column,
                self.variable_config.target_column,
                lag=lag,
                n_lags=n_lags,
                max_distance=max_distance,
            )
        except ValueError as exc:
            self.activity_log.log("variogram_failed", "error", str(exc), {"mode": mode})
            self.activity_log.log("dashboard_render_failed", "error", str(exc), {"view": "Variografía"})
            raise

        if result.downsampled:
            self.activity_log.log(
                "visualization_degraded_mode",
                "warning",
                "Variograma calculado con muestra para mantener estabilidad.",
                {"source_points": result.source_points, "used_points": result.used_points},
            )

        self.activity_log.log("variogram_rendered", "success", "Variograma experimental preparado.", {"lags": n_lags, "mode": mode})
        self.activity_log.log("dashboard_render_finished", "success", "Render variograma finalizado.", {"view": "Variografía"})
        return result

    def get_summary_cards(self) -> dict[str, str]:
        if self.current_dataset is None:
            return {"Dataset": "No cargado", "Muestras": "0", "Columnas": "0", "Target": "No definido", "Estado": "Pendiente"}

        target = self.variable_config.target_column if self.variable_config else "No definido"
        cards = {
            "Dataset": self.current_dataset.file_name,
            "Muestras": str(self.current_dataset.row_count),
            "Columnas": str(self.current_dataset.column_count),
            "Target": target,
            "Estado": "Listo" if self.variable_config else "Configurar variables",
            "Dominio": self.workflow_state.active_domain,
            "Soporte": self.workflow_state.active_support,
        }

        if self.variable_config and target in self.current_dataset.dataframe.columns and _is_numeric_dtype(self.current_dataset.dataframe[target]):
            series = self.current_dataset.dataframe[target].dropna()
            if len(series) > 0:
                cards["Mean"] = f"{float(series.mean()):.3g}"
                cards["Std"] = f"{float(series.std()):.3g}"
                if float(series.mean()) != 0:
                    cards["CV"] = f"{float(series.std()/series.mean()):.3g}"
        return cards

    def get_target_statistics_table(self) -> list[tuple[str, str]]:
        if self.current_dataset is None or self.variable_config is None:
            return []
        target = self.variable_config.target_column
        df = self.current_dataset.dataframe
        if target not in df.columns or not _is_numeric_dtype(df[target]):
            return []

        series = df[target].dropna()
        if series.empty:
            return []

        stats = {
            "n": len(series),
            "mean": float(series.mean()),
            "std": float(series.std()),
            "min": float(series.min()),
            "p10": float(series.quantile(0.10)),
            "p25": float(series.quantile(0.25)),
            "p50": float(series.quantile(0.50)),
            "p75": float(series.quantile(0.75)),
            "p90": float(series.quantile(0.90)),
            "max": float(series.max()),
            "skewness": float(series.skew()),
        }
        return [(k, f"{v:.5g}" if isinstance(v, float) else str(v)) for k, v in stats.items()]

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
        restart_recommended = not up_to_date
        message = "Repositorio ya estaba actualizado." if up_to_date else "Repositorio actualizado correctamente. Reinicia la app para aplicar cambios."
        self.activity_log.log("repo_update_finished", "success", message, {"restart_recommended": restart_recommended})
        return RepoUpdateResult(True, message, combined, restart_recommended)

    def export_activity_log(self, destination_path: str) -> str:
        exported = self.activity_log.export_log(destination_path)
        self.activity_log.log("export_log_requested", "success", "Log exportado correctamente.", {"destination": str(exported)})
        return str(exported)

    def get_available_columns(self) -> list[str]:
        return [] if self.current_dataset is None else self.current_dataset.columns

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
        self.activity_log.log("variable_config_applied", "success", "Configuración de variables aplicada.", {"target": target_column})
        return ColumnSelectionResult(True, "Configuración de variables guardada.", self.build_eda_summary())

    def build_eda_summary(self) -> str:
        if self.current_dataset is None:
            return "No hay dataset cargado para EDA."
        df = self.current_dataset.dataframe
        summary = (
            "MÓDULO EDA\n"
            "----------\n"
            "Subsecciones: Resumen | Univariado | Espacial | Swath | Variografía\n"
            f"Filas: {self.current_dataset.row_count} | Columnas: {self.current_dataset.column_count}\n"
        )
        if self.variable_config is None:
            return summary + "Selecciona X/Y/Z/target para habilitar estadísticas del target."
        target = self.variable_config.target_column
        if target not in df.columns or not _is_numeric_dtype(df[target]):
            return summary + "Target no numérico: estadísticas limitadas."
        series = df[target].dropna()
        return summary + f"Target {target}: n={len(series)}, mean={float(series.mean()):.4g}, std={float(series.std()):.4g}"

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
        return (
            "ETAPA DATOS\n"
            "-----------\n"
            f"Archivo: {dataset.file_name}\n"
            f"Filas: {dataset.row_count} | Columnas: {dataset.column_count}\n"
            "Tipos de datos:\n"
            f"{dtypes_text}"
        )
