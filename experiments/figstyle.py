"""One shared Nature-style visual identity for every ARGUS figure.

Semantic color consistency: the same concept always gets the same color.
  red=high risk, amber=medium/partial, green=low/detected, gray=unknown/abstain,
  purple=LLM/reasoning, orange=human calibration, blue=input/data/reference.

Matplotlib figures import RISK / PALETTE / apply_style; the SVG figures
(Figure 1, Figure 2/architecture) use the same hex values by hand.
"""

from __future__ import annotations

# Master palette (Nature/biomedical-style: white bg, pastel fills, darker accents).
ARGUS_COLORS = {
    # risk scale (semantic, used everywhere)
    "low": "#59A14F",
    "medium": "#E5A823",
    "high": "#D9534F",
    "unknown": "#8A8F98",
    # module fills / accents
    "input": "#EAF3FB",      "input_accent": "#4E79A7",
    "retrieval": "#EAF6EE",  "retrieval_accent": "#59A14F",
    "llm": "#F1ECFA",        "llm_accent": "#7E57C2",
    "human": "#FFF3DF",      "human_accent": "#F28E2B",
    "output": "#FFF8E8",     "output_accent": "#E5A823",
    "eval": "#EEF3F8",       "eval_accent": "#2F5D8C",
    # neutrals
    "border": "#D8DEE9",
    "axis": "#9CA6B4",       # axis spines / tick marks (deeper than border)
    "text": "#1F2933",
    "secondary_text": "#5B6475",
    # calibration-strategy colors (Fig 6): green / blue / yellow (on-palette, high
    # contrast, and NOT purple -- purple is reserved for LLM/reasoning).
    "before": "#59A14F",
    "demote": "#4E79A7",
    "abstain": "#E5A823",
}

INK = ARGUS_COLORS["text"]
MUTED = ARGUS_COLORS["secondary_text"]

RISK = {k: ARGUS_COLORS[k] for k in ("low", "medium", "high", "unknown")}

PALETTE = {
    "ink": INK, "muted": MUTED, "border": ARGUS_COLORS["border"],
    "axis": ARGUS_COLORS["axis"],
    "risk": RISK,
    "accent": ARGUS_COLORS["input_accent"],          # "answered" coverage accent
    "missed_fill": "#EEF0F3", "missed_edge": ARGUS_COLORS["border"],
    "before": ARGUS_COLORS["before"],
    "demote": ARGUS_COLORS["demote"],
    "abstain": ARGUS_COLORS["abstain"],
    "colors": ARGUS_COLORS,
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
        "axes.edgecolor": ARGUS_COLORS["axis"],
        "axes.linewidth": 0.9,
        "axes.grid": False,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "xtick.color": ARGUS_COLORS["axis"],
        "ytick.color": ARGUS_COLORS["axis"],
        "xtick.labelcolor": INK,
        "ytick.labelcolor": INK,
        "xtick.major.width": 0.8,
        "ytick.major.width": 0.8,
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
