"""Compact three-panel trade-off figure for Table 3.

Run:
    PYTHONPATH=src python3 experiments/annotation/make_calibration_tradeoff.py

Writes:
    paper/figures/calibration_tradeoff.pdf
    paper/figures/calibration_tradeoff.png
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "paper" / "figures"

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "argus_mplconfig"))
os.environ.setdefault("XDG_CACHE_HOME", str(Path(tempfile.gettempdir()) / "argus_xdg_cache"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import sys  # noqa: E402

sys.path.insert(0, str(ROOT / "experiments"))
from figstyle import PALETTE, apply_style  # noqa: E402

LABELS = ["Before", "Demote", "Abstain"]
COLORS = [PALETTE["before"], PALETTE["demote"], PALETTE["abstain"]]
INK = PALETTE["ink"]
MUTED = PALETTE["muted"]
BORDER = PALETTE["border"]
AXIS = PALETTE["axis"]

PANELS = [
    {
        "title": "A  Over-severe count",
        "ylabel": "over-severe cells",
        "values": [29, 18, 6],
        "ylim": (0, 34),
        "better": r"$\downarrow$ better",
        "better_pos": (0.98, 0.92, "right"),
        "fmt": "{:.0f}",
    },
    {
        "title": "B  Coverage",
        "ylabel": "answered cells",
        "values": [33, 33, 13],
        "ylim": (0, 38),
        "better": r"$\uparrow$ better",
        "better_pos": (0.98, 0.92, "right"),
        "fmt": "{:.0f}",
    },
    {
        "title": r"C  Weighted $\kappa$",
        "ylabel": r"weighted $\kappa$",
        "values": [0.06, 0.13, 0.25],
        "ylim": (0, 0.30),
        "better": r"$\uparrow$ better",
        "better_pos": (0.02, 0.82, "left"),
        "fmt": "{:.2f}",
    },
]


def draw_panel(ax, panel: dict) -> None:
    xs = range(len(LABELS))
    values = panel["values"]
    bars = ax.bar(xs, values, color=COLORS, width=0.62, edgecolor="white", linewidth=0.7)

    ax.set_title(panel["title"], fontsize=8.7, fontweight="bold", loc="left", color=INK, pad=4)
    ax.set_ylabel(panel["ylabel"], fontsize=7.8, color=INK)
    ax.set_xticks(list(xs))
    ax.set_xticklabels(LABELS, fontsize=7.5)
    ax.set_ylim(*panel["ylim"])
    ax.tick_params(axis="y", labelsize=7.3, colors=MUTED, length=2.5)
    ax.tick_params(axis="x", length=0, pad=2)
    ax.grid(axis="y", color=BORDER, linewidth=0.6)
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color(AXIS)

    ymax = panel["ylim"][1]
    offset = ymax * 0.025
    for bar, value in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            value + offset,
            panel["fmt"].format(value),
            ha="center",
            va="bottom",
            fontsize=7.4,
            color=INK,
            fontweight="bold",
        )
    better_x, better_y, better_ha = panel["better_pos"]
    ax.text(
        better_x,
        better_y,
        panel["better"],
        transform=ax.transAxes,
        ha=better_ha,
        va="top",
        fontsize=7.2,
        color=MUTED,
    )


def main() -> None:
    apply_style()
    plt.rcParams.update({"pdf.fonttype": 42, "ps.fonttype": 42})
    fig, axes = plt.subplots(1, 3, figsize=(6.7, 2.15), constrained_layout=True)
    fig.patch.set_facecolor("white")
    for ax, panel in zip(axes, PANELS):
        draw_panel(ax, panel)

    fig.suptitle(
        "Calibration trade-off: severity reduction versus coverage",
        fontsize=9.4,
        fontweight="bold",
        color=INK,
    )
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(OUT_DIR / f"calibration_tradeoff.{ext}", dpi=220, bbox_inches="tight")
    print(f"wrote {(OUT_DIR / 'calibration_tradeoff.pdf').relative_to(ROOT)}")


if __name__ == "__main__":
    main()
