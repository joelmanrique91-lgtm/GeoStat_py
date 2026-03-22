"""UI theme tokens and matplotlib styling helpers for GeoStat Py."""

from __future__ import annotations

from matplotlib import cm


APP_BG = "#0E1624"
PANEL_BG = "#142033"
CARD_BG = "#1B2A3D"
BORDER_SOFT = "#334A66"
TEXT_MAIN = "#E7EEF7"
TEXT_MUTED = "#9CB0C8"
GRID_COLOR = "#35506C"

SEM_BLUE = "#3B82F6"
SEM_BLUE_SOFT = "#7FB2FF"
SEM_GREEN = "#26A269"
SEM_ORANGE = "#D4A72C"
SEM_RED = "#D6616B"
SEM_GRAY = "#9AA8BA"
SEM_WHITE = "#F5F8FC"

WF_IDLE = "#243549"
WF_ACTIVE = "#2F5E98"
WF_READY = "#2F6C53"
WF_BLOCKED = "#7A3A45"
WF_WARNING = "#7A5E2A"
CHIP_BG = "#243549"

DOMAIN_PALETTE = [
    "#60A5FA",
    "#34D399",
    "#F59E0B",
    "#F472B6",
    "#A78BFA",
    "#22D3EE",
    "#F87171",
    "#FBBF24",
    "#4ADE80",
    "#93C5FD",
]


def get_domain_color(domain_label: str) -> str:
    label = str(domain_label).strip()
    if not label or label.upper() in {"UNDEFINED", "NA", "N/A", "NONE", "NULL"}:
        return SEM_GRAY
    return DOMAIN_PALETTE[sum(ord(ch) for ch in label) % len(DOMAIN_PALETTE)]


def get_continuous_colormap() -> str:
    return "cividis"


def apply_axis_style(ax) -> None:
    ax.set_facecolor(CARD_BG)
    ax.grid(color=GRID_COLOR, alpha=0.28, linestyle="-", linewidth=0.6)
    ax.tick_params(colors=TEXT_MUTED, labelsize=8.5)
    ax.xaxis.label.set_color(TEXT_MUTED)
    ax.yaxis.label.set_color(TEXT_MUTED)
    ax.title.set_color(TEXT_MAIN)
    ax.title.set_fontsize(11)
    ax.title.set_fontweight("bold")
    for spine in ax.spines.values():
        spine.set_color(BORDER_SOFT)


def apply_figure_theme(fig) -> None:
    fig.patch.set_facecolor(PANEL_BG)


def add_reference_line(ax, value: float, *, label: str, color: str, y_pos: float = 0.95) -> None:
    ax.axvline(value, color=color, linestyle="--", linewidth=1.2, alpha=0.95)
    ax.text(
        value,
        y_pos,
        f" {label}",
        transform=ax.get_xaxis_transform(),
        color=color,
        fontsize=8,
        va="top",
        ha="left",
        bbox={"facecolor": CARD_BG, "edgecolor": color, "alpha": 0.35, "boxstyle": "round,pad=0.18"},
    )


def get_categorical_cmap():
    return cm.get_cmap("tab20")
