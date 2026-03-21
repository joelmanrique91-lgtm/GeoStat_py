"""UI theme tokens and matplotlib styling helpers for GeoStat Py."""

from __future__ import annotations

from matplotlib import cm


APP_BG = "#0B1220"
PANEL_BG = "#111827"
CARD_BG = "#1F2937"
BORDER_SOFT = "#334155"
TEXT_MAIN = "#E5E7EB"
TEXT_MUTED = "#94A3B8"
GRID_COLOR = "#334155"

SEM_BLUE = "#2563EB"
SEM_BLUE_SOFT = "#60A5FA"
SEM_GREEN = "#10B981"
SEM_ORANGE = "#F59E0B"
SEM_RED = "#EF4444"
SEM_GRAY = "#9CA3AF"
SEM_WHITE = "#F8FAFC"

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
