"""Helpers for robust Tk/CustomTk window geometry normalization."""

from __future__ import annotations

from dataclasses import dataclass
import re


_GEOMETRY_PATTERN = re.compile(r"^(?P<w>\d+)x(?P<h>\d+)(?P<x>[+-]\d+)(?P<y>[+-]\d+)$")


@dataclass(frozen=True)
class Rect:
    """Simple immutable rectangle in virtual-screen coordinates."""

    x: int
    y: int
    width: int
    height: int


def parse_tk_geometry(value: str) -> Rect | None:
    """Parse Tk geometry strings like '1360x860+10-5'."""
    match = _GEOMETRY_PATTERN.match((value or "").strip())
    if match is None:
        return None
    return Rect(
        x=int(match.group("x")),
        y=int(match.group("y")),
        width=int(match.group("w")),
        height=int(match.group("h")),
    )


def to_tk_geometry(rect: Rect) -> str:
    """Serialize a rectangle to Tk geometry format."""
    x = f"+{rect.x}" if rect.x >= 0 else str(rect.x)
    y = f"+{rect.y}" if rect.y >= 0 else str(rect.y)
    return f"{rect.width}x{rect.height}{x}{y}"


def clamp_to_visible_area(
    rect: Rect,
    *,
    visible: Rect,
    min_width: int,
    min_height: int,
    edge_padding: int = 0,
) -> Rect:
    """
    Clamp geometry to a visible area preserving usability.

    If the visible area is smaller than desired minimums (common in high-DPI
    effective resolutions), the function gracefully degrades to fit the
    available area.
    """
    safe_w = max(320, min_width)
    safe_h = max(240, min_height)
    max_w = max(320, visible.width - (edge_padding * 2))
    max_h = max(240, visible.height - (edge_padding * 2))

    width = max(320, min(rect.width, max_w))
    height = max(240, min(rect.height, max_h))

    width = max(min(width, max_w), min(safe_w, max_w))
    height = max(min(height, max_h), min(safe_h, max_h))

    min_x = visible.x + edge_padding
    min_y = visible.y + edge_padding
    max_x = visible.x + visible.width - edge_padding - width
    max_y = visible.y + visible.height - edge_padding - height
    x = min(max(rect.x, min_x), max(min_x, max_x))
    y = min(max(rect.y, min_y), max(min_y, max_y))
    return Rect(x=x, y=y, width=width, height=height)
