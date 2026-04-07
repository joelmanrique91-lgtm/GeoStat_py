"""Renderer interfaces for HomePanel visual sections."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from app.models.spatial import SceneState
from app.services.visualization_service import SpatialDataBundle


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
    cutoff_state: dict[str, object]
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
    def render(self, widget: Any, scene: SceneState, color_display_label: str) -> None:
        """Render logical 3D scene payload in the provided widget."""

    @abstractmethod
    def show_unavailable(self, widget: Any, reason: str) -> None:
        """Display backend unavailability message in widget."""


@dataclass
class VariographyRenderContext:
    target_label: str
    info_text: str
    chart_text_color: str
    chart_label_size: int
    chart_legend_size: int


class VariographyRenderer(ABC):
    @abstractmethod
    def render(self, grid: Any, response: dict[str, object], context: VariographyRenderContext) -> None:
        """Render experimental variography outputs (gamma + npairs + diagnostics)."""
