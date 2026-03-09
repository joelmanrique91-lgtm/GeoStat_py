"""Service layer for geostatistical workflows."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess

import pandas as pd
from pandas.api.types import is_numeric_dtype
from pandas.errors import EmptyDataError, ParserError

from app.adapters.geostatspy_adapter import GeostatSpyAdapter
from app.models.dataset_model import DatasetModel
from app.models.variable_config_model import VariableConfigModel
from app.utils.paths import PROJECT_ROOT


@dataclass
class LoadCsvResult:
    """Structured response for UI after attempting CSV load."""

    success: bool
    message: str
    details: str
    dataset: DatasetModel | None = None


@dataclass
class RepoUpdateResult:
    """Result for repository update operations."""

    success: bool
    message: str
    details: str
    restart_recommended: bool = False


@dataclass
class ColumnSelectionResult:
    """Result for X/Y/Z/target column configuration."""

    success: bool
    message: str
    eda_summary: str


class GeostatService:
    """Mediates between UI actions and adapter calls."""

    def __init__(self, adapter: GeostatSpyAdapter) -> None:
        self.adapter = adapter
        self.current_dataset: DatasetModel | None = None
        self.variable_config: VariableConfigModel | None = None

    def load_csv(self, file_path: str) -> LoadCsvResult:
        """Load a CSV file, validate it, and keep the dataset in memory."""
        selected_path = Path(file_path)

        if not selected_path.exists() or not selected_path.is_file():
            return LoadCsvResult(
                success=False,
                message="No se pudo cargar el archivo.",
                details="La ruta seleccionada no existe o no es un archivo válido.",
            )

        try:
            dataframe = pd.read_csv(selected_path)
        except EmptyDataError:
            return LoadCsvResult(
                success=False,
                message="El archivo CSV está vacío.",
                details="Selecciona un CSV con datos y vuelve a intentar.",
            )
        except UnicodeDecodeError:
            try:
                dataframe = pd.read_csv(selected_path, encoding="latin-1")
            except Exception:
                return LoadCsvResult(
                    success=False,
                    message="No se pudo leer el encoding del CSV.",
                    details="Intenta guardar el archivo en UTF-8 o latin-1.",
                )
        except ParserError:
            return LoadCsvResult(
                success=False,
                message="El CSV no tiene un formato legible.",
                details="Revisa separadores, comillas y estructura de columnas.",
            )
        except Exception as exc:
            return LoadCsvResult(
                success=False,
                message="Ocurrió un error inesperado al leer el CSV.",
                details=f"Detalle técnico: {exc}",
            )

        if dataframe.empty:
            return LoadCsvResult(
                success=False,
                message="El CSV no contiene filas de datos.",
                details="Agrega al menos una fila y vuelve a cargar.",
            )

        dataset = DatasetModel.from_dataframe(file_path=selected_path, dataframe=dataframe)
        self.current_dataset = dataset
        self.variable_config = None

        details = self._build_dataset_summary(dataset)
        return LoadCsvResult(
            success=True,
            message="CSV cargado correctamente.",
            details=details,
            dataset=dataset,
        )

    def update_repository(self) -> RepoUpdateResult:
        """Run a safe repository update using git pull."""
        try:
            pull_result = subprocess.run(
                ["git", "pull"],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                check=False,
                timeout=120,
            )
        except FileNotFoundError:
            return RepoUpdateResult(
                success=False,
                message="Git no está disponible en el sistema.",
                details="Instala Git y verifica que esté en PATH.",
            )
        except Exception as exc:
            return RepoUpdateResult(
                success=False,
                message="No se pudo ejecutar la actualización del repositorio.",
                details=f"Detalle técnico: {exc}",
            )

        if pull_result.returncode != 0:
            error_output = (pull_result.stderr or pull_result.stdout).strip()
            return RepoUpdateResult(
                success=False,
                message="Falló `git pull`.",
                details=error_output or "Error desconocido de git.",
            )

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

        return RepoUpdateResult(
            success=True,
            message=message,
            details=combined,
            restart_recommended=restart_recommended,
        )

    def get_available_columns(self) -> list[str]:
        if self.current_dataset is None:
            return []
        return self.current_dataset.columns

    def set_variable_config(self, x_column: str, y_column: str, z_column: str, target_column: str) -> ColumnSelectionResult:
        """Validate and persist spatial/target column selections."""
        if self.current_dataset is None:
            return ColumnSelectionResult(
                success=False,
                message="Primero debes cargar un CSV.",
                eda_summary="No hay dataset cargado.",
            )

        selected = [x_column, y_column, z_column, target_column]
        if any(not value for value in selected):
            return ColumnSelectionResult(
                success=False,
                message="Debes seleccionar X, Y, Z y variable objetivo.",
                eda_summary="Configuración incompleta.",
            )

        invalid = [col for col in selected if col not in self.current_dataset.columns]
        if invalid:
            return ColumnSelectionResult(
                success=False,
                message="La selección contiene columnas no válidas.",
                eda_summary=f"Columnas inválidas: {', '.join(invalid)}",
            )

        self.variable_config = VariableConfigModel(
            x_column=x_column,
            y_column=y_column,
            z_column=z_column,
            target_column=target_column,
        )

        eda_summary = self.build_eda_summary()
        return ColumnSelectionResult(
            success=True,
            message="Configuración de variables guardada.",
            eda_summary=eda_summary,
        )

    def build_eda_summary(self) -> str:
        """Create a basic EDA summary from loaded dataset and selected target."""
        if self.current_dataset is None:
            return "No hay dataset cargado para EDA."

        df = self.current_dataset.dataframe
        dtypes = "\n".join(f"- {col}: {dtype}" for col, dtype in df.dtypes.items())
        nulls = "\n".join(f"- {col}: {int(count)}" for col, count in df.isna().sum().items())
        numeric_columns = [col for col in df.columns if is_numeric_dtype(df[col])]
        numeric_text = ", ".join(str(col) for col in numeric_columns) if numeric_columns else "(ninguna)"

        summary = (
            f"Filas: {self.current_dataset.row_count}\n"
            f"Columnas: {self.current_dataset.column_count}\n"
            f"Nombres de columnas: {', '.join(self.current_dataset.columns)}\n\n"
            "Tipos de datos:\n"
            f"{dtypes}\n\n"
            "Nulos por columna:\n"
            f"{nulls}\n\n"
            f"Columnas numéricas detectadas: {numeric_text}\n"
        )

        if self.variable_config is None:
            return summary + "\nSelecciona X/Y/Z/target para ver estadísticos de la variable objetivo."

        target = self.variable_config.target_column
        target_series = df[target]
        summary += (
            "\nConfiguración actual:\n"
            f"- X: {self.variable_config.x_column}\n"
            f"- Y: {self.variable_config.y_column}\n"
            f"- Z: {self.variable_config.z_column}\n"
            f"- Target: {self.variable_config.target_column}\n"
        )

        if not is_numeric_dtype(target_series):
            return summary + "\nLa variable objetivo no es numérica. No se calculan estadísticos numéricos."

        stats = target_series.describe(percentiles=[0.25, 0.5, 0.75])
        return (
            summary
            + "\nEstadísticos de la variable objetivo:\n"
            f"- count: {stats.get('count', 0):.0f}\n"
            f"- mean: {stats.get('mean', float('nan')):.6g}\n"
            f"- std: {stats.get('std', float('nan')):.6g}\n"
            f"- min: {stats.get('min', float('nan')):.6g}\n"
            f"- 25%: {stats.get('25%', float('nan')):.6g}\n"
            f"- 50%: {stats.get('50%', float('nan')):.6g}\n"
            f"- 75%: {stats.get('75%', float('nan')):.6g}\n"
            f"- max: {stats.get('max', float('nan')):.6g}"
        )

    def _build_dataset_summary(self, dataset: DatasetModel) -> str:
        columns_text = ", ".join(dataset.columns)
        return (
            f"Archivo: {dataset.file_name}\n"
            f"Ruta: {dataset.file_path}\n"
            f"Filas: {dataset.row_count}\n"
            f"Columnas: {dataset.column_count}\n"
            f"Nombres de columnas: {columns_text}\n\n"
            "Preview (primeras 5 filas):\n"
            f"{dataset.preview_as_text()}"
        )

    def variogram_placeholder(self) -> str:
        availability = self.adapter.describe_availability()
        return f"[Placeholder] Análisis variográfico pendiente. {availability}"

    def kriging_placeholder(self) -> str:
        return "[Placeholder] Módulo de kriging pendiente de implementación."

    def sgs_placeholder(self) -> str:
        return "[Placeholder] Simulación SGS pendiente de implementación."

    def visualization_placeholder(self) -> str:
        return "[Placeholder] Visualización pendiente de implementación."
