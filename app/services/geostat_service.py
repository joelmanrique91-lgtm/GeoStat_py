"""Service layer for geostatistical workflows."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from pandas.errors import EmptyDataError, ParserError

from app.adapters.geostatspy_adapter import GeostatSpyAdapter
from app.models.dataset_model import DatasetModel


@dataclass
class LoadCsvResult:
    """Structured response for UI after attempting CSV load."""

    success: bool
    message: str
    details: str
    dataset: DatasetModel | None = None


class GeostatService:
    """Mediates between UI actions and adapter calls."""

    def __init__(self, adapter: GeostatSpyAdapter) -> None:
        self.adapter = adapter
        self.current_dataset: DatasetModel | None = None

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

        details = self._build_dataset_summary(dataset)
        return LoadCsvResult(
            success=True,
            message="CSV cargado correctamente.",
            details=details,
            dataset=dataset,
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
