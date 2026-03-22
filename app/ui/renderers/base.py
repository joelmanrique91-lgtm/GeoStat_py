"""Renderer interfaces for HomePanel visual sections."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from app.services.visualization_service import Spatial3DDataBundle, SpatialDataBundle


@dataclass
class EDARenderContext:
    active_variable: str
    skewness_text: str
    chart_text_color: str
    chart_legend_size: int
    chart_label_size: int


@dataclass
class Spatial2DRenderContext:
    color_by: str | None
    snapshot: dict[str, object]
    guardrail_note: str
    info_text_color: str
    info_border_color: str
    info_bg_color: str
    label_size: int


class EDARenderer(ABC):
    @abstractmethod
    def render(self, grid: Any, data: dict[str, object], context: EDARenderContext, *, original_values: list[float], cutoff_value: float | None) -> None:
        """Render EDA charts inside a dashboard grid."""


class Spatial2DRenderer(ABC):
    @abstractmethod
    def render(self, grid: Any, spatial: SpatialDataBundle, context: Spatial2DRenderContext) -> None:
        """Render 2D spatial charts inside a dashboard grid."""


class Spatial3DRenderer(ABC):
    @abstractmethod
    def is_available(self) -> tuple[bool, str]:
        """Return backend availability tuple."""

    @abstractmethod
    def create_widget(self, parent) -> Any:
        """Create renderer host widget attached to parent."""

    @abstractmethod
    def render(self, widget: Any, data: Spatial3DDataBundle, color_display_label: str) -> None:
        """Render 3D payload in the provided widget."""

    @abstractmethod
    def show_unavailable(self, widget: Any, reason: str) -> None:
        """Display backend unavailability message in widget."""
