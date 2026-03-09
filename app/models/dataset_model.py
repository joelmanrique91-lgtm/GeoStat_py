"""Data model for tabular geostatistical datasets."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class DatasetModel:
    """Represents a dataset loaded into the desktop application."""

    file_path: Path
    row_count: int = 0
    column_count: int = 0
