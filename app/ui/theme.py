"""UI theme tokens and matplotlib styling helpers for GeoStat Py."""

from __future__ import annotations

from matplotlib import cm


APP_BG = "#0B1120"
PANEL_BG = "#111A2E"
CARD_BG = "#18243A"
SURFACE_ELEVATED = "#1D2C46"
BG_MAIN = APP_BG
BG_PANEL = PANEL_BG
BG_CARD = CARD_BG
BORDER_SOFT = "#2A3A56"
DIVIDER_SOFT = BORDER_SOFT
TEXT_MAIN = "#E6EDF8"
TEXT_MUTED = "#A7B6CB"
TEXT_SOFT = "#8B9AB0"
GRID_COLOR = "#334866"
CHART_BG = "#142033"
CHART_BORDER = "#2F4666"
CHART_GRID = "#355174"
CHART_TEXT = "#DCE8F8"

SEM_BLUE = "#4A8DFF"
SEM_BLUE_SOFT = "#8EB8FF"
SEM_GREEN = "#38B780"
SEM_ORANGE = "#D6A956"
SEM_RED = "#CF6A78"
SEM_GRAY = "#8EA0B8"
SEM_WHITE = "#EEF3FC"

WF_IDLE = "#24344E"
WF_ACTIVE = "#3271E6"
WF_READY = "#295B4A"
WF_BLOCKED = "#5A3340"
WF_WARNING = "#6A5530"
CHIP_BG = "#21314B"
BTN_SECONDARY_BG = "#24344E"
BTN_SECONDARY_HOVER = "#2E4566"
BTN_TERTIARY_BG = "#1B273D"
BTN_TERTIARY_HOVER = "#253650"
BTN_PRIMARY_BG = SEM_BLUE
BTN_PRIMARY_HOVER = "#2B6EEA"
BTN_DANGER_BG = "#8F3A4A"
BTN_DANGER_HOVER = "#A2485A"
BTN_DISABLED_BG = "#1A2334"
KPI_PRIMARY_BG = "#245796"

BTN_HEIGHT_PRIMARY = 32
BTN_HEIGHT_SECONDARY = 30
BTN_HEIGHT_AUX = 28
BTN_CORNER_RADIUS = 8
INPUT_HEIGHT = 30

DOMAIN_PALETTE = [
    "#64A8FF",
    "#44D9A0",
    SEM_ORANGE,
    "#F58AB8",
    "#A997FF",
    "#2FD6E8",
    "#F27F7F",
    "#F0C46A",
    "#63D98B",
    "#A7D0FF",
]

FONT_TITLE = {"size": 24, "weight": "bold"}
FONT_TITLE_COMPACT = {"size": 19, "weight": "bold"}
FONT_SUBTITLE = {"size": 15, "weight": "bold"}
FONT_BODY = {"size": 13, "weight": "normal"}
FONT_SMALL = {"size": 12, "weight": "normal"}
FONT_MICRO = {"size": 11, "weight": "normal"}
FONT_KPI = {"size": 16, "weight": "bold"}

CHART_FONT_SIZE_TITLE = 12
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
    ax.grid(color=CHART_GRID, alpha=0.38, linestyle="-", linewidth=0.7)
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


def apply_dashboard_layout(fig, *, left: float = 0.055, right: float = 0.985, top: float = 0.94, bottom: float = 0.10, wspace: float = 0.22, hspace: float = 0.28) -> None:
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
