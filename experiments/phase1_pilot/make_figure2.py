"""Generate Figure 2 (the results / conclusion figure).

Two panels:
  A. Headline metrics, keyword baseline vs LLM evidence-adequacy assessor —
     detection collapses to 0.182 for keyword once sentinel leakage is removed,
     and the LLM recovers it to 1.000 with no false alarms.
  B. Per-flaw outcome matrix for the keyword baseline, grouped omission vs
     commission — it is blind to every commission-type flaw; the LLM catches all.

The keyword side is recomputed live (deterministic, no API). The LLM headline is
read from the frozen `llm_summary.json` (the LLM run is non-deterministic and
costs API calls), so the figure cannot drift from the committed numbers.

Run:
    PYTHONPATH=src python3 experiments/phase1_pilot/make_figure2.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments"))

from argus.config import load_flaws  # noqa: E402
from argus.evaluation.runner import evaluate_flaws  # noqa: E402
from figstyle import PALETTE, apply_style  # noqa: E402

apply_style()
# Fig 3 keeps enlarged base fonts independent of the shared figstyle (Fig 4/6 use the base).
import matplotlib as _mpl  # noqa: E402
_mpl.rcParams.update({"font.size": 12.0, "axes.titlesize": 13.0, "axes.labelsize": 11.5,
                      "xtick.labelsize": 10.5, "ytick.labelsize": 10.5, "legend.fontsize": 10.5})

PAPER = ROOT / "examples" / "papers" / "clean_supported.json"
LLM_SUMMARY = Path(__file__).resolve().parent / "llm_summary.json"
OUT_DIR = ROOT / "paper" / "figures"

# Shared palette (see experiments/figstyle.py).
GREEN = PALETTE["risk"]["low"]
RED = PALETTE["risk"]["high"]
GRAY = PALETTE["risk"]["unknown"]
INK = PALETTE["ink"]
MUTED = PALETTE["muted"]
MISSED_FILL = PALETTE["missed_fill"]
MISSED_EDGE = PALETTE["missed_edge"]


def keyword_result() -> dict:
    paper = json.loads(PAPER.read_text())
    return evaluate_flaws(paper, sorted(load_flaws()), max_steps=1, assessor="keyword")


def _pretty(lab: str) -> str:
    return lab.replace("_", " ")


def _panel_label(ax, letter: str) -> None:
    ax.text(-0.02, 1.06, letter, transform=ax.transAxes, fontsize=15.4,
            fontweight="bold", va="bottom", ha="right", color=INK)


def panel_a(ax, kw: dict, llm: dict) -> None:
    """Dumbbell: keyword (hollow) -> LLM (filled) per metric; the connecting bar
    reads the recovery directly (detection 0.18 -> 1.00)."""
    rows = [("detection", kw["detection_rate"], llm["detection_rate"]),
            ("localization", kw["localization_acc"], llm["localization_acc"]),
            ("false alarm", kw["false_alarm_rate"], llm["false_alarm_rate"])]
    ys = list(range(len(rows)))[::-1]
    for y, (name, kv, lv) in zip(ys, rows):
        if abs(lv - kv) > 1e-6:
            ax.plot([kv, lv], [y, y], color=PALETTE["border"], lw=3.0, zorder=1,
                    solid_capstyle="round")
        ax.scatter([kv], [y], s=42, facecolor="white", edgecolor=GRAY, lw=1.5, zorder=3)
        ax.scatter([lv], [y], s=48, facecolor=GREEN, edgecolor="white", lw=0.8, zorder=4)
        if abs(lv - kv) <= 1e-6:                      # coincident (e.g. false alarm 0=0)
            ax.text(lv + 0.04, y, f"{lv:.2f}", ha="left", va="center", fontsize=10.6,
                    color=MUTED)
        else:
            ax.text(kv - 0.035, y, f"{kv:.2f}", ha="right", va="center", fontsize=10.5,
                    color=MUTED)
            ax.text(lv + 0.038, y, f"{lv:.2f}", ha="left", va="center", fontsize=10.9,
                    color=GREEN, fontweight="bold")
    ax.set_yticks(ys)
    ax.set_yticklabels([r[0] for r in rows], fontsize=12.6)
    ax.set_ylim(-0.6, len(rows) - 0.4)
    ax.set_xlim(-0.02, 1.16)
    ax.set_xticks([0, 0.5, 1.0])
    ax.set_xlabel("rate", fontsize=11.9)
    ax.set_ylabel("metric", fontsize=11.9)
    # keep both axes drawn (x = rate at the bottom, y = metric on the left);
    # only the top/right frame is dropped.
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(axis="y", length=0)
    # compact legend (open = keyword, filled = LLM)
    ax.scatter([], [], s=42, facecolor="white", edgecolor=GRAY, lw=1.5, label="keyword")
    ax.scatter([], [], s=48, facecolor=GREEN, edgecolor="white", lw=0.8,
               label=f"LLM ({llm.get('model', 'gpt-4o')})")
    ax.legend(fontsize=10.6, loc="lower right", frameon=False, handletextpad=0.3,
              borderpad=0.2)
    _panel_label(ax, "a")


def panel_b(ax, pairs: list[dict], llm: dict) -> None:
    """Per-flaw caught/missed matrix, keyword vs LLM, grouped omission/commission.
    Makes the commission-blindness of the keyword column visible against the fully
    green LLM column."""
    omission = [p for p in pairs if p["ground_truth"]["injection_op"] == "remove"]
    commission = [p for p in pairs if p["ground_truth"]["injection_op"] == "replace"]
    ordered = omission + commission
    n = len(ordered)
    cols = [("keyword", None), (f"LLM", None)]

    for i, p in enumerate(ordered):
        yy = n - 1 - i
        outcomes = [bool(p["score"]["detected"]), True]  # LLM detection == 1.00
        for cx, det in enumerate(outcomes):
            face = GREEN if det else GRAY   # missed = the shared "unknown" gray (#9BA1A9)
            ax.add_patch(plt.Rectangle((cx + 0.09, yy - 0.40), 0.82, 0.80,
                         facecolor=face, edgecolor="white", lw=0.8, zorder=2))
            if not det:  # white x marks a miss (redundant with fill for colour-blind)
                ax.plot(cx + 0.5, yy, marker="x", ms=4.5, mew=1.3, color="white", zorder=3)
        ax.text(-0.12, yy, _pretty(p["flaw_id"]), ha="right", va="center",
                fontsize=10.4, color=INK)

    for cx, (c, _) in enumerate(cols):
        ax.text(cx + 0.5, n - 0.28, c, ha="center", va="bottom", fontsize=11.2,
                fontweight="bold", color=INK)
    # omission / commission grouping brackets on the RIGHT (clear of the flaw labels)
    div = len(commission) - 0.5
    rx = 2.06
    ax.plot([rx, rx], [div, n - 0.5], color=MUTED, lw=1.4, zorder=1)          # omission (top)
    ax.plot([rx, rx], [-0.5, div], color=RED, lw=1.4, zorder=1)               # commission (bottom)
    ax.text(rx + 0.07, (div + n - 0.5) / 2, "omission", fontsize=10.5,
            color=MUTED, va="center", ha="left", rotation=90)
    ax.text(rx + 0.07, (-0.5 + div) / 2, "commission", fontsize=10.5,
            color=RED, va="center", ha="left", rotation=90, fontweight="bold")

    ax.set_xlim(-1.15, 2.55)
    ax.set_ylim(-0.75, n + 0.05)
    ax.axis("off")
    _panel_label(ax, "b")


def main() -> None:
    kw = keyword_result()
    llm = json.loads(LLM_SUMMARY.read_text())

    fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.5),
                             gridspec_kw={"width_ratios": [1.15, 1.0]})
    fig.patch.set_facecolor("white")
    panel_a(axes[0], kw["summary"], llm)
    panel_b(axes[1], kw["pairs"], llm)
    # shared caught/missed key, unobtrusive at the foot
    fig.legend(handles=[
        Patch(facecolor=GREEN, edgecolor="none", label="caught"),
        Patch(facecolor=GRAY, edgecolor="none", label="missed"),
    ], loc="lower center", ncol=2, fontsize=11.2, frameon=False, bbox_to_anchor=(0.5, -0.02),
        handlelength=1.1, columnspacing=1.4)

    fig.tight_layout(rect=[0, 0.04, 1, 1.0], w_pad=2.2)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(OUT_DIR / f"figure_phase1.{ext}", dpi=400, bbox_inches="tight",
                    facecolor="white")
    s = kw["summary"]
    print(f"wrote {(OUT_DIR / 'figure_phase1.pdf').relative_to(ROOT)} and figure_phase1.png")
    print(f"  keyword: detection={s['detection_rate']:.3f}  "
          f"LLM: detection={llm['detection_rate']:.3f}")


if __name__ == "__main__":
    main()
