"""Data model for tabular geostatistical datasets."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import pandas as pd


@dataclass
class DatasetModel:
    """Represents a dataset loaded into the desktop application."""

    file_name: str
    file_path: Path
    row_count: int
    column_count: int
    columns: list[str]
    preview: Any
    dataframe: Any

    @classmethod
    def from_dataframe(cls, file_path: Path, dataframe: Any, preview_rows: int = 5) -> "DatasetModel":
        """Create model from a loaded dataframe and file metadata."""
        normalized_path = file_path.resolve()
        return cls(
            file_name=normalized_path.name,
            file_path=normalized_path,
            row_count=len(dataframe.index),
            column_count=len(dataframe.columns),
            columns=[str(col) for col in dataframe.columns.tolist()],
            preview=dataframe.head(preview_rows).copy(),
            dataframe=dataframe,
        )

    def preview_as_text(self) -> str:
        """Return a readable textual preview for the UI panel."""
        if self.preview.empty:
            return "(sin filas para previsualizar)"
        return self.preview.to_string(index=False)
