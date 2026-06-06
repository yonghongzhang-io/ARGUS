"""One shared visual style for every ARGUS figure: palette, font, spacing.

Import in the matplotlib figure scripts:
    import sys; sys.path.insert(0, str(ROOT / "experiments"))
    from figstyle import PALETTE, RISK, apply_style
The SVG figures (Figure 1, Figure 3) use the same hex values by hand.

Design: a single muted palette. Ordinal risk colors (low/medium/high/unknown)
are semantic and reused everywhere; structural figures reuse green/amber/gray and
add only blue (input) and purple (audit) so the whole paper shares one look.
"""

from __future__ import annotations

INK = "#333333"
MUTED = "#777777"

# Ordinal risk scale (semantic — keep consistent across all figures).
RISK = {
    "low": "#5b9e6f",      # muted green
    "medium": "#d2a85c",   # muted amber
    "high": "#c4615c",     # muted salmon-red
    "unknown": "#9aa0a6",  # cool gray
}

# Structural accents (fill, line) for module/pipeline boxes.
PALETTE = {
    "ink": INK, "muted": MUTED,
    "risk": RISK,
    "blue":   {"fill": "#dbe4ee", "line": "#6a8caf"},   # input
    "green":  {"fill": "#dcebd9", "line": "#5b9e6f"},   # retrieval / agentic
    "purple": {"fill": "#e6ddf0", "line": "#8f7bb0"},   # audit
    "amber":  {"fill": "#f6e7cf", "line": "#cc9a5c"},   # output
    "gray":   {"fill": "#f0efe9", "line": "#9aa0a6"},   # neutral / loop
    "callout": {"fill": "#fbf6e3", "line": "#cabf6f"},
    # neutral "answered" accent (coverage donut) — reuse the input blue line
    "accent": "#6a8caf",
    "missed_fill": "#ece7df", "missed_edge": "#cfc8bd",
}


def apply_style() -> None:
    """Set matplotlib rcParams so every generated figure matches."""
    import matplotlib as mpl

    mpl.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"],
        "font.size": 10,
        "axes.titlesize": 11,
        "axes.titleweight": "bold",
        "axes.labelsize": 9.5,
        "axes.edgecolor": "#888888",
        "axes.linewidth": 0.8,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "xtick.color": INK,
        "ytick.color": INK,
        "text.color": INK,
        "axes.labelcolor": INK,
        "legend.fontsize": 8.5,
        "legend.frameon": False,
        "figure.facecolor": "white",
        "figure.titlesize": 13,
        "figure.titleweight": "bold",
        "savefig.facecolor": "white",
        "savefig.bbox": "tight",
        "savefig.dpi": 200,
    })
