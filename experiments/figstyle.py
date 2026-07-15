"""One shared top-journal visual identity for every ARGUS data figure.

Semantic color consistency: the same concept always gets the same color.
  red=high risk, amber=medium/partial, green=low/detected, gray=unknown/abstain,
  purple=LLM/reasoning, orange=human calibration, blue=input/data/reference.

Design intent (2026 refresh): an *editorial* palette (deliberately off the
default Tableau-10 hues so figures don't read as "matplotlib defaults"),
hairline axes, embedded vector text (Type-42), and generous whitespace. Every
matplotlib figure imports RISK / PALETTE / apply_style (and, optionally, the
despine / panel_title helpers); the hand-drawn architecture diagrams
(Figure 1, Figure 2) are intentionally OUT of scope and keep their own artwork.
"""

from __future__ import annotations

# Master palette — editorial, desaturated, harmonised; strong value separation so
# it survives grayscale printing. Semantic roles are stable across every figure.
ARGUS_COLORS = {
    # risk scale (semantic, used everywhere)
    "low": "#5C9070",        # sage green   (was Tableau #59A14F)
    "medium": "#CF9B3C",     # ochre        (was #E5A823)
    "high": "#BE5A4C",       # terracotta   (was #D9534F)
    "unknown": "#9BA1A9",    # cool gray
    # module fills / accents  (fills are light tints for by-hand SVG use)
    "input": "#E9F0F7",      "input_accent": "#3E6598",   # editorial blue
    "retrieval": "#E9F1EC",  "retrieval_accent": "#5C9070",
    "llm": "#EFECF7",        "llm_accent": "#7061A8",     # muted violet
    "human": "#FBF1E3",      "human_accent": "#D08A46",   # muted orange
    "output": "#FAF4E6",     "output_accent": "#CF9B3C",
    "eval": "#EBF0F5",       "eval_accent": "#34597F",
    # neutrals
    "border": "#D9DEE5",
    "axis": "#AEB4BD",       # hairline spines / tick marks
    "text": "#22262B",       # near-black body text
    "secondary_text": "#697079",
    # calibration-strategy colors (Fig 6): green / blue / amber (on-palette, NOT
    # purple -- purple is reserved for LLM/reasoning).
    "before": "#5C9070",
    "demote": "#3E6598",
    "abstain": "#CF9B3C",
}

INK = ARGUS_COLORS["text"]
MUTED = ARGUS_COLORS["secondary_text"]

RISK = {k: ARGUS_COLORS[k] for k in ("low", "medium", "high", "unknown")}

PALETTE = {
    "ink": INK, "muted": MUTED, "border": ARGUS_COLORS["border"],
    "axis": ARGUS_COLORS["axis"],
    "risk": RISK,
    "accent": ARGUS_COLORS["input_accent"],          # "answered" coverage accent
    "missed_fill": "#EDEFF2", "missed_edge": ARGUS_COLORS["border"],
    "before": ARGUS_COLORS["before"],
    "demote": ARGUS_COLORS["demote"],
    "abstain": ARGUS_COLORS["abstain"],
    "colors": ARGUS_COLORS,
}

# Ordered categorical cycle (used when a figure doesn't pick colors by hand).
CYCLE = [ARGUS_COLORS[k] for k in
         ("input_accent", "low", "medium", "high", "llm_accent", "human_accent", "unknown")]


def apply_style() -> None:
    """Set matplotlib rcParams so every generated figure matches (top-journal look)."""
    import matplotlib as mpl
    from cycler import cycler

    mpl.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"],
        "font.size": 12.0,
        "axes.titlesize": 13.0,
        "axes.titleweight": "bold",
        "axes.titlepad": 7.0,
        "axes.labelsize": 11.5,
        "axes.edgecolor": ARGUS_COLORS["axis"],
        "axes.linewidth": 0.7,             # hairline spines (was 0.9)
        "axes.grid": False,
        "axes.prop_cycle": cycler(color=CYCLE),
        "xtick.labelsize": 10.5,
        "ytick.labelsize": 10.5,
        "xtick.color": ARGUS_COLORS["axis"],
        "ytick.color": ARGUS_COLORS["axis"],
        "xtick.labelcolor": INK,
        "ytick.labelcolor": INK,
        "xtick.major.width": 0.6,
        "ytick.major.width": 0.6,
        "xtick.major.size": 3.0,
        "ytick.major.size": 3.0,
        "text.color": INK,
        "axes.labelcolor": INK,
        "legend.fontsize": 10.5,
        "legend.frameon": False,
        "legend.handlelength": 1.2,
        "legend.handleheight": 1.1,
        "legend.columnspacing": 1.2,
        "figure.facecolor": "white",
        "figure.titlesize": 14.5,
        "figure.titleweight": "bold",
        "savefig.facecolor": "white",
        "savefig.bbox": "tight",
        "savefig.dpi": 300,                # was 200
        # embed real vector text so PDF figures stay crisp at any zoom
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "svg.fonttype": "none",
    })


# ---- optional helpers (a figure may use them; not required) -------------------------

def despine(ax, keep=("left", "bottom")) -> None:
    """Hide all spines except `keep`; a clean top-journal frame."""
    for side, sp in ax.spines.items():
        sp.set_visible(side in keep)


def panel_title(ax, letter: str, text: str = "", **kw) -> None:
    """Consistent left-aligned bold panel title, e.g. panel_title(ax, 'A', 'Coverage')."""
    label = f"{letter}  {text}".rstrip()
    ax.set_title(label, loc="left", fontweight="bold", color=INK, **kw)
