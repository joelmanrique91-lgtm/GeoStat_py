"""Service layer for geostatistical workflows."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess

from app.adapters.geostatspy_adapter import GeostatSpyAdapter
from app.models.dataset_model import DatasetModel
from app.models.variable_config_model import VariableConfigModel
from app.services.activity_log_service import ActivityLogService
from app.utils.paths import PROJECT_ROOT


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


class GeostatService:
    """Mediates between UI actions and adapter calls."""

    def __init__(self, adapter: GeostatSpyAdapter, activity_log: ActivityLogService | None = None) -> None:
        self.adapter = adapter
        self.activity_log = activity_log or ActivityLogService()
        self.current_dataset: DatasetModel | None = None
        self.variable_config: VariableConfigModel | None = None

    def load_csv(self, file_path: str) -> LoadCsvResult:
        self.activity_log.log("csv_load_started", "info", "Iniciando carga de CSV.", {"file_path": file_path})
        selected_path = Path(file_path)

        if not selected_path.exists() or not selected_path.is_file():
            message = "No se pudo cargar el archivo."
            details = "La ruta seleccionada no existe o no es un archivo válido."
            self.activity_log.log("csv_load_failed", "error", message, {"file_path": file_path, "reason": details})
            return LoadCsvResult(success=False, message=message, details=details)

        try:
            dataframe = _read_csv(selected_path)
        except _csv_errors()[0]:
            message = "El archivo CSV está vacío."
            details = "Selecciona un CSV con datos y vuelve a intentar."
            self.activity_log.log("csv_load_failed", "error", message, {"file_path": file_path, "reason": "empty"})
            return LoadCsvResult(success=False, message=message, details=details)
        except UnicodeDecodeError:
            try:
                dataframe = _read_csv_with_encoding(selected_path, "latin-1")
            except Exception as exc:
                message = "No se pudo leer el encoding del CSV."
                details = "Intenta guardar el archivo en UTF-8 o latin-1."
                self.activity_log.log("csv_load_failed", "error", message, {"file_path": file_path, "reason": str(exc)})
                return LoadCsvResult(success=False, message=message, details=details)
        except _csv_errors()[1]:
            message = "El CSV no tiene un formato legible."
            details = "Revisa separadores, comillas y estructura de columnas."
            self.activity_log.log("csv_load_failed", "error", message, {"file_path": file_path, "reason": "parser_error"})
            return LoadCsvResult(success=False, message=message, details=details)
        except Exception as exc:
            message = "Ocurrió un error inesperado al leer el CSV."
            details = f"Detalle técnico: {exc}"
            self.activity_log.log("app_error", "error", message, {"file_path": file_path, "error": str(exc)})
            return LoadCsvResult(success=False, message=message, details=details)

        if dataframe.empty:
            message = "El CSV no contiene filas de datos."
            details = "Agrega al menos una fila y vuelve a cargar."
            self.activity_log.log("csv_load_failed", "error", message, {"file_path": file_path, "reason": "no_rows"})
            return LoadCsvResult(success=False, message=message, details=details)

        dataset = DatasetModel.from_dataframe(file_path=selected_path, dataframe=dataframe)
        self.current_dataset = dataset
        self.variable_config = None

        details = self._build_dataset_summary(dataset)
        self.activity_log.log(
            "csv_load_succeeded",
            "success",
            "CSV cargado correctamente.",
            {
                "file_name": dataset.file_name,
                "file_path": str(dataset.file_path),
                "row_count": dataset.row_count,
                "column_count": dataset.column_count,
            },
        )
        return LoadCsvResult(success=True, message="CSV cargado correctamente.", details=details, dataset=dataset)

    def update_repository(self) -> RepoUpdateResult:
        self.activity_log.log("repo_update_started", "info", "Iniciando actualización de repositorio.", {})
        try:
            pull_result = subprocess.run(
                ["git", "pull"], cwd=PROJECT_ROOT, capture_output=True, text=True, check=False, timeout=120
            )
        except FileNotFoundError:
            message = "Git no está disponible en el sistema."
            details = "Instala Git y verifica que esté en PATH."
            self.activity_log.log("repo_update_finished", "error", message, {"details": details})
            return RepoUpdateResult(success=False, message=message, details=details)
        except Exception as exc:
            message = "No se pudo ejecutar la actualización del repositorio."
            details = f"Detalle técnico: {exc}"
            self.activity_log.log("app_error", "error", message, {"error": str(exc)})
            return RepoUpdateResult(success=False, message=message, details=details)

        if pull_result.returncode != 0:
            error_output = (pull_result.stderr or pull_result.stdout).strip()
            message = "Falló `git pull`."
            self.activity_log.log("repo_update_finished", "error", message, {"details": error_output})
            return RepoUpdateResult(success=False, message=message, details=error_output or "Error desconocido de git.")

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
        message = "Repositorio actualizado correctamente."
        if up_to_date:
            message = "Repositorio ya estaba actualizado."
        elif restart_recommended:
            message += " Reinicia la app para aplicar completamente cambios de código."

        self.activity_log.log(
            "repo_update_finished",
            "success",
            message,
            {"restart_recommended": restart_recommended, "git_output": output},
        )
        return RepoUpdateResult(success=True, message=message, details=combined, restart_recommended=restart_recommended)

    def export_activity_log(self, destination_path: str) -> str:
        exported = self.activity_log.export_log(destination_path)
        self.activity_log.log(
            "export_log_requested",
            "success",
            "Log exportado correctamente.",
            {"destination": str(exported)},
        )
        return str(exported)

    def get_available_columns(self) -> list[str]:
        return [] if self.current_dataset is None else self.current_dataset.columns

    def set_variable_config(self, x_column: str, y_column: str, z_column: str, target_column: str) -> ColumnSelectionResult:
        if self.current_dataset is None:
            return ColumnSelectionResult(False, "Primero debes cargar un CSV.", "No hay dataset cargado.")

        selected = [x_column, y_column, z_column, target_column]
        if any(not value for value in selected):
            return ColumnSelectionResult(False, "Debes seleccionar X, Y, Z y variable objetivo.", "Configuración incompleta.")

        invalid = [col for col in selected if col not in self.current_dataset.columns]
        if invalid:
            return ColumnSelectionResult(
                False,
                "La selección contiene columnas no válidas.",
                f"Columnas inválidas: {', '.join(invalid)}",
            )

        self.variable_config = VariableConfigModel(x_column=x_column, y_column=y_column, z_column=z_column, target_column=target_column)
        self.activity_log.log(
            "variable_config_applied",
            "success",
            "Configuración de variables aplicada.",
            {"x": x_column, "y": y_column, "z": z_column, "target": target_column},
        )
        eda_summary = self.build_eda_summary()
        return ColumnSelectionResult(True, "Configuración de variables guardada.", eda_summary)

    def build_eda_summary(self) -> str:
        if self.current_dataset is None:
            return "No hay dataset cargado para EDA."

        df = self.current_dataset.dataframe
        columns = ", ".join(self.current_dataset.columns)
        dtypes = "\n".join(f"• {col}: {dtype}" for col, dtype in df.dtypes.items())
        nulls = "\n".join(f"• {col}: {int(count)}" for col, count in df.isna().sum().items())
        numeric_columns = [col for col in df.columns if _is_numeric_dtype(df[col])]
        numeric_text = ", ".join(str(col) for col in numeric_columns) if numeric_columns else "(ninguna)"

        summary = (
            "RESUMEN EDA\n"
            "-----------\n"
            f"Filas: {self.current_dataset.row_count}\n"
            f"Columnas: {self.current_dataset.column_count}\n"
            f"Columnas disponibles: {columns}\n\n"
            "Tipos de datos:\n"
            f"{dtypes}\n\n"
            "Nulos por columna:\n"
            f"{nulls}\n\n"
            f"Columnas numéricas: {numeric_text}\n"
        )

        if self.variable_config is None:
            return summary + "\nSelecciona X/Y/Z/target para habilitar estadísticas del target."

        target = self.variable_config.target_column
        target_series = df[target]
        summary += (
            "\nConfiguración espacial activa:\n"
            f"• X: {self.variable_config.x_column}\n"
            f"• Y: {self.variable_config.y_column}\n"
            f"• Z: {self.variable_config.z_column}\n"
            f"• Target: {target}\n"
        )

        if not _is_numeric_dtype(target_series):
            return summary + "\nTarget no numérico: no se calculan estadísticas numéricas."

        stats = target_series.describe(percentiles=[0.25, 0.5, 0.75])
        return (
            summary
            + "\nEstadísticos del target:\n"
            f"• count: {stats.get('count', 0):.0f}\n"
            f"• mean: {stats.get('mean', float('nan')):.6g}\n"
            f"• std: {stats.get('std', float('nan')):.6g}\n"
            f"• min: {stats.get('min', float('nan')):.6g}\n"
            f"• 25%: {stats.get('25%', float('nan')):.6g}\n"
            f"• 50%: {stats.get('50%', float('nan')):.6g}\n"
            f"• 75%: {stats.get('75%', float('nan')):.6g}\n"
            f"• max: {stats.get('max', float('nan')):.6g}"
        )

    def module_not_implemented(self, module_name: str) -> str:
        message = f"{module_name}: módulo aún no implementado. Esta acción fue registrada."
        self.activity_log.log(
            "placeholder_module_clicked",
            "info",
            message,
            {"module": module_name},
        )
        return message

    def variogram_placeholder(self) -> str:
        return self.module_not_implemented("Análisis variográfico")

    def kriging_placeholder(self) -> str:
        return self.module_not_implemented("Kriging")

    def sgs_placeholder(self) -> str:
        return self.module_not_implemented("Simulación SGS")

    def visualization_placeholder(self) -> str:
        return self.module_not_implemented("Visualización")

    def _build_dataset_summary(self, dataset: DatasetModel) -> str:
        columns_text = ", ".join(dataset.columns)
        return (
            "DATASET CARGADO\n"
            "--------------\n"
            f"Archivo: {dataset.file_name}\n"
            f"Ruta: {dataset.file_path}\n"
            f"Filas: {dataset.row_count} | Columnas: {dataset.column_count}\n"
            f"Nombres de columnas: {columns_text}\n\n"
            "Preview (primeras 5 filas):\n"
            f"{dataset.preview_as_text()}"
        )
