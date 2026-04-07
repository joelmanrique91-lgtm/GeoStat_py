"""UI theme tokens and matplotlib styling helpers for GeoStat Py."""

from __future__ import annotations

from matplotlib import cm


APP_BG = "#ECEBE7"
PANEL_BG = "#F6F4EF"
CARD_BG = "#FFFCF7"
SURFACE_ELEVATED = "#E3DFD6"
BG_MAIN = APP_BG
BG_PANEL = PANEL_BG
BG_CARD = CARD_BG
BORDER_SOFT = "#C9C3B6"
DIVIDER_SOFT = BORDER_SOFT
TEXT_MAIN = "#242A32"
TEXT_MUTED = "#4E5965"
TEXT_SOFT = "#6B7683"
GRID_COLOR = "#D5D0C4"
CHART_BG = "#FAF8F2"
CHART_BORDER = "#B7AF9E"
CHART_GRID = "#D9D3C7"
CHART_TEXT = "#2E3640"

SEM_BLUE = "#1F4B5C"
SEM_BLUE_SOFT = "#3E6D80"
SEM_GREEN = "#4C7A63"
SEM_ORANGE = "#A7793F"
SEM_RED = "#B46B59"
SEM_GRAY = "#8492A0"
SEM_WHITE = "#F5F3EE"
SEM_PURPLE = "#4E3A66"

WF_IDLE = "#D8D2C5"
WF_ACTIVE = "#2F596B"
WF_READY = "#5B7D68"
WF_BLOCKED = "#8A5C54"
WF_WARNING = "#8D6A3F"
CHIP_BG = "#E0DBCF"
BTN_SECONDARY_BG = "#DAD4C8"
BTN_SECONDARY_HOVER = "#CEC7BA"
BTN_TERTIARY_BG = "#E7E2D6"
BTN_TERTIARY_HOVER = "#D6CFC1"
BTN_PRIMARY_BG = SEM_BLUE
BTN_PRIMARY_HOVER = "#2B5F74"
BTN_DANGER_BG = "#A7695B"
BTN_DANGER_HOVER = "#965C50"
BTN_DISABLED_BG = "#D0CBC0"
KPI_PRIMARY_BG = "#D7E3E8"

BTN_HEIGHT_PRIMARY = 32
BTN_HEIGHT_SECONDARY = 30
BTN_HEIGHT_AUX = 28
BTN_CORNER_RADIUS = 8
INPUT_HEIGHT = 30

DOMAIN_PALETTE = [
    "#3F6C85",
    "#4A866A",
    SEM_ORANGE,
    "#8A5A7B",
    "#6D6294",
    "#4D7D85",
    "#B46B59",
    "#A1864A",
    "#5D8C6D",
    "#7FA0B3",
]

FONT_TITLE = {"size": 25, "weight": "bold"}
FONT_TITLE_COMPACT = {"size": 20, "weight": "bold"}
FONT_SUBTITLE = {"size": 16, "weight": "bold"}
FONT_BODY = {"size": 13, "weight": "normal"}
FONT_SMALL = {"size": 12, "weight": "normal"}
FONT_MICRO = {"size": 11, "weight": "normal"}
FONT_KPI = {"size": 16, "weight": "bold"}

CHART_FONT_SIZE_TITLE = 13
CHART_FONT_SIZE_LABEL = 10
CHART_FONT_SIZE_TICK = 9
CHART_FONT_SIZE_LEGEND = 9


def get_domain_color(domain_label: str) -> str:
    label = str(domain_label).strip()
    if not label or label.upper() in {"UNDEFINED", "NA", "N/A", "NONE", "NULL"}:
        return SEM_GRAY
    return DOMAIN_PALETTE[sum(ord(ch) for ch in label) % len(DOMAIN_PALETTE)]


def get_continuous_colormap() -> str:
    return "cividis"


def apply_axis_style(ax) -> None:
    ax.set_facecolor(CHART_BG)
    ax.grid(color=CHART_GRID, alpha=0.55, linestyle="-", linewidth=0.6)
    ax.tick_params(colors=CHART_TEXT, labelsize=CHART_FONT_SIZE_TICK)
    ax.xaxis.label.set_color(CHART_TEXT)
    ax.yaxis.label.set_color(CHART_TEXT)
    ax.xaxis.label.set_size(CHART_FONT_SIZE_LABEL)
    ax.yaxis.label.set_size(CHART_FONT_SIZE_LABEL)
    ax.title.set_color(CHART_TEXT)
    ax.title.set_fontsize(CHART_FONT_SIZE_TITLE)
    ax.title.set_fontweight("bold")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(CHART_BORDER)
    ax.spines["bottom"].set_color(CHART_BORDER)


def apply_figure_theme(fig) -> None:
    fig.patch.set_facecolor(CHART_BG)
    try:
        fig.set_layout_engine("none")
    except Exception:
        pass


def apply_dashboard_layout(fig, *, left: float = 0.055, right: float = 0.985, top: float = 0.94, bottom: float = 0.12, wspace: float = 0.22, hspace: float = 0.26) -> None:
    """Unified layout policy for embedded dashboard figures.

    This intentionally avoids mixing `tight_layout`/`constrained_layout` across
    renderers to keep resize behavior stable in embedded Tk canvases.
    """
    fig.subplots_adjust(left=left, right=right, top=top, bottom=bottom, wspace=wspace, hspace=hspace)


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
