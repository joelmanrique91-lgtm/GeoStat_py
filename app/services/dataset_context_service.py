"""Specialized service for dataset/config/context lifecycle flows."""

from __future__ import annotations

from pathlib import Path

from app.models.dataset_model import DatasetModel
from app.models.variable_config_model import VariableConfigModel


def _read_csv(path: Path):
    import pandas as pd

    return pd.read_csv(path)


def _read_csv_with_encoding(path: Path, encoding: str):
    import pandas as pd

    return pd.read_csv(path, encoding=encoding)


def _csv_errors():
    from pandas.errors import EmptyDataError, ParserError

    return EmptyDataError, ParserError


def _normalize_identifier(value: str) -> str:
    return value.lower().replace("_", "").replace(" ", "")


def _is_numeric_dtype(series) -> bool:
    from pandas.api.types import is_numeric_dtype

    return bool(is_numeric_dtype(series))


class DatasetContextService:
    """Owns dataset load, column autodetection and variable configuration lifecycle."""

    def __init__(self, host_service) -> None:
        self.host = host_service

    def get_available_columns(self) -> list[str]:
        return [] if self.host.current_dataset is None else self.host.current_dataset.columns

    def get_numeric_columns(self) -> list[str]:
        if self.host.current_dataset is None:
            return []
        numeric_columns: list[str] = []
        for column in self.host.current_dataset.columns:
            if _is_numeric_dtype(self.host.current_dataset.dataframe[column]):
                numeric_columns.append(column)
        return numeric_columns

    def get_categorical_columns(self) -> list[str]:
        if self.host.current_dataset is None:
            return []
        return [column for column in self.host.current_dataset.columns if not _is_numeric_dtype(self.host.current_dataset.dataframe[column])]

    def get_autodetected_columns(self) -> dict[str, str]:
        return dict(self.host.autodetected_columns)

    def load_csv(self, file_path: str):
        self.host.activity_log.log("csv_load_started", "info", "Iniciando carga de CSV.", {"file_path": file_path})
        selected_path = Path(file_path)
        if not selected_path.exists() or not selected_path.is_file():
            message = "No se pudo cargar el archivo."
            details = "La ruta seleccionada no existe o no es un archivo válido."
            self.host.activity_log.log("csv_load_failed", "error", message, {"file_path": file_path, "reason": details})
            return False, message, details, None

        try:
            dataframe = _read_csv(selected_path)
        except _csv_errors()[0]:
            return False, "El archivo CSV está vacío.", "Selecciona un CSV con datos y vuelve a intentar.", None
        except UnicodeDecodeError:
            try:
                dataframe = _read_csv_with_encoding(selected_path, "latin-1")
            except Exception as exc:
                return False, "No se pudo leer el CSV.", f"Error de codificación: {exc}", None
        except _csv_errors()[1] as exc:
            return False, "El CSV tiene formato inválido.", f"Detalle parser: {exc}", None
        except Exception as exc:  # noqa: BLE001
            return False, "Error inesperado al cargar CSV.", f"{exc}", None

        if dataframe.empty:
            return False, "El archivo CSV no contiene filas.", "Carga un CSV con al menos una fila de datos.", None

        dataset = DatasetModel.from_dataframe(file_path=selected_path, dataframe=dataframe)
        self.host.current_dataset = dataset
        self.host.variable_config = None
        self.host.workflow_state.current_step = "Datos"
        self.host.workflow_state.active_domain = "No definido"
        self.host.workflow_state.active_support = "No definido"
        self.host._clear_cutoff_state()
        self.host._clear_dynamic_cutoff_state()
        self.host._clear_domain_state()
        self.host.clear_support_state()
        self.host._domain_filter_context_enabled = True
        self.host.autodetected_columns = self.autodetect_columns(dataset.columns, dataset.dataframe)
        message = f"CSV cargado: {dataset.file_name} ({dataset.row_count} filas, {dataset.column_count} columnas)."
        details = self.host._build_dataset_summary(dataset)
        self.host.activity_log.log(
            "csv_loaded",
            "success",
            "CSV cargado correctamente.",
            {
                "file_name": dataset.file_name,
                "rows": dataset.row_count,
                "columns": dataset.column_count,
                "autodetected": self.host.autodetected_columns,
            },
        )
        return True, message, details, dataset

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
            "x": pick(["x", "coordx", "east", "easting"]),
            "y": pick(["y", "coordy", "north", "northing"]),
            "z": pick(["z", "coordz", "elev", "elevation", "bench", "rl"]),
            "hole_id": pick(["holeid", "hole", "dhid", "id", "sampleid", "hole_id", "drillhole"]),
            "domain": pick(["domain", "dom", "lith", "lithology", "zone", "facies", "lito", "litho"]),
        }
        target_col = pick(["target", "ley", "grade", "au", "ag", "cu", "value", "val", "variable"])
        if not target_col:
            for col in columns:
                if _is_numeric_dtype(dataframe[col]) and col not in {suggestions["x"], suggestions["y"], suggestions["z"]}:
                    target_col = col
                    break
        suggestions["target"] = target_col

        return suggestions

    def set_variable_config(
        self,
        x_column: str,
        y_column: str,
        z_column: str,
        target_column: str,
        hole_id_column: str | None = None,
        domain_column: str | None = None,
    ) -> tuple[bool, str, str]:
        if self.host.current_dataset is None:
            return False, "Primero debes cargar un CSV.", "No hay dataset cargado."
        selected = [x_column, y_column, z_column, target_column]
        if any(not value for value in selected):
            return False, "Debes seleccionar X, Y, Z y variable objetivo.", "Configuración incompleta."
        invalid = [col for col in selected if col not in self.host.current_dataset.columns]
        if invalid:
            return False, "La selección contiene columnas no válidas.", f"Columnas inválidas: {', '.join(invalid)}"
        coordinate_columns = [x_column, y_column, z_column]
        if len(set(coordinate_columns)) != len(coordinate_columns):
            return False, "X, Y, Z deben ser columnas diferentes.", "No se permiten coordenadas duplicadas."
        non_numeric_coordinates = [col for col in coordinate_columns if not _is_numeric_dtype(self.host.current_dataset.dataframe[col])]
        if non_numeric_coordinates:
            return (
                False,
                "X, Y, Z deben ser columnas numéricas.",
                f"Columnas no numéricas: {', '.join(non_numeric_coordinates)}",
            )

        self.host.variable_config = VariableConfigModel(x_column, y_column, z_column, target_column, hole_id_column, domain_column)
        self.host._domain_filter_context_enabled = bool(domain_column)
        self.host.workflow_state.active_domain = f"Columna: {domain_column}" if domain_column else "No definido"
        self.host.workflow_state.active_support = "Muestra original"
        self.host._clear_cutoff_state()
        self.host._clear_dynamic_cutoff_state()
        self.host._clear_domain_state()
        self.host.clear_support_state()
        self.host.workflow_state.effective_target_column = target_column
        self.host.activity_log.log("variable_config_applied", "success", "Configuración de variables aplicada.", {"target": target_column, "domain": domain_column or ""})
        return True, "Configuración de variables guardada.", self.host.build_eda_summary()
