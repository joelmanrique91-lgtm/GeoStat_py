"""UI theme tokens and matplotlib styling helpers for GeoStat Py."""

from __future__ import annotations

from matplotlib import cm


APP_BG = "#0F172A"
PANEL_BG = "#0B1220"
CARD_BG = "#111827"
BG_MAIN = APP_BG
BG_PANEL = PANEL_BG
BG_CARD = CARD_BG
BORDER_SOFT = "#1F2937"
TEXT_MAIN = "#E5E7EB"
TEXT_MUTED = "#9CA3AF"
GRID_COLOR = "#273449"

SEM_BLUE = "#3B82F6"
SEM_BLUE_SOFT = "#7FB2FF"
SEM_GREEN = "#26A269"
SEM_ORANGE = "#D4A72C"
SEM_RED = "#D6616B"
SEM_GRAY = "#9AA8BA"
SEM_WHITE = "#F5F8FC"

WF_IDLE = "#1F2937"
WF_ACTIVE = "#3B82F6"
WF_READY = "#2F6C53"
WF_BLOCKED = "#7A3A45"
WF_WARNING = "#7A5E2A"
CHIP_BG = BG_CARD
BTN_SECONDARY_BG = "#1E293B"
BTN_SECONDARY_HOVER = "#334155"
BTN_PRIMARY_HOVER = "#2563EB"
DIVIDER_SOFT = BORDER_SOFT
KPI_PRIMARY_BG = "#1D4E89"

DOMAIN_PALETTE = [
    "#60A5FA",
    "#34D399",
    SEM_ORANGE,
    "#F472B6",
    "#A78BFA",
    "#22D3EE",
    "#F87171",
    SEM_ORANGE,
    "#4ADE80",
    "#93C5FD",
]

FONT_TITLE = {"size": 17, "weight": "bold"}
FONT_SUBTITLE = {"size": 12, "weight": "bold"}
FONT_BODY = {"size": 11, "weight": "normal"}
FONT_SMALL = {"size": 10, "weight": "normal"}
FONT_KPI = {"size": 14, "weight": "bold"}

CHART_FONT_SIZE_TITLE = 11
CHART_FONT_SIZE_LABEL = 9
CHART_FONT_SIZE_TICK = 9
CHART_FONT_SIZE_LEGEND = 8


def get_domain_color(domain_label: str) -> str:
    label = str(domain_label).strip()
    if not label or label.upper() in {"UNDEFINED", "NA", "N/A", "NONE", "NULL"}:
        return SEM_GRAY
    return DOMAIN_PALETTE[sum(ord(ch) for ch in label) % len(DOMAIN_PALETTE)]


def get_continuous_colormap() -> str:
    return "cividis"


def apply_axis_style(ax) -> None:
    ax.set_facecolor(BG_CARD)
    ax.grid(color=GRID_COLOR, alpha=0.22, linestyle="-", linewidth=0.55)
    ax.tick_params(colors=TEXT_MUTED, labelsize=CHART_FONT_SIZE_TICK)
    ax.xaxis.label.set_color(TEXT_MUTED)
    ax.yaxis.label.set_color(TEXT_MUTED)
    ax.xaxis.label.set_size(CHART_FONT_SIZE_LABEL)
    ax.yaxis.label.set_size(CHART_FONT_SIZE_LABEL)
    ax.title.set_color(TEXT_MAIN)
    ax.title.set_fontsize(CHART_FONT_SIZE_TITLE)
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
