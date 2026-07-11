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


def panel_a(ax, kw: dict, llm: dict) -> None:
    metrics = ["detection", "false alarm", "localization"]
    kw_vals = [kw["detection_rate"], kw["false_alarm_rate"], kw["localization_acc"]]
    llm_vals = [llm["detection_rate"], llm["false_alarm_rate"], llm["localization_acc"]]

    y = range(len(metrics))
    h = 0.36
    ax.barh([i + h / 2 for i in y], kw_vals, height=h, color=GRAY, label="keyword baseline")
    ax.barh([i - h / 2 for i in y], llm_vals, height=h, color=GREEN,
            label=f"LLM ({llm.get('model', 'gpt-4o')})")

    for i, v in enumerate(kw_vals):
        ax.text(v + 0.02, i + h / 2, f"{v:.2f}", va="center", fontsize=9, color=MUTED)
    for i, v in enumerate(llm_vals):
        ax.text(v + 0.02, i - h / 2, f"{v:.2f}", va="center", fontsize=9,
                fontweight="bold", color=GREEN)

    ax.set_yticks(list(y))
    ax.set_yticklabels(metrics, fontsize=10)
    ax.set_xlim(0, 1.18)
    ax.set_xticks([0, 0.5, 1.0])
    ax.invert_yaxis()
    ax.set_title("A  Reasoning over evidence adequacy recovers detection",
                 fontsize=11, fontweight="bold", loc="left", color=INK)
    ax.legend(fontsize=8.5, loc="lower right", frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    ax.annotate("", xy=(1.0, 0.16), xytext=(0.30, 0.16),
                arrowprops=dict(arrowstyle="->", color=GREEN, lw=1.6))
    ax.text(0.62, -0.18, r"0.18 $\rightarrow$ 1.00", fontsize=9, color=GREEN,
            fontweight="bold", ha="center")


def _donut(ax, caught: int, total: int, title: str, title_color: str,
           title_bold: bool, center_color: str) -> None:
    """One caught/missed donut: big fraction in the middle, 2px white spacers."""
    missed = total - caught
    vals = [v for v in (caught, missed) if v > 0]
    cols = ([GREEN] if caught else []) + ([MISSED_FILL] if missed else [])
    wedges, _ = ax.pie(
        vals, colors=cols, startangle=90, counterclock=False,
        wedgeprops=dict(width=0.40, edgecolor="white", linewidth=2))
    for w, is_caught in zip(wedges, ([True] if caught else []) + ([False] if missed else [])):
        if not is_caught:
            w.set_edgecolor(MISSED_EDGE)
            w.set_linewidth(1.2)
    ax.text(0, 0.12, f"{caught}/{total}", ha="center", va="center",
            fontsize=15, fontweight="bold", color=center_color)
    ax.text(0, -0.30, "caught", ha="center", va="center", fontsize=8.5, color=MUTED)
    ax.set_title(title, fontsize=9, color=title_color,
                 fontweight="bold" if title_bold else "normal", pad=4)
    ax.set_aspect("equal")


def panel_b(ax, pairs: list[dict], llm: dict) -> None:
    omission = [p for p in pairs if p["ground_truth"]["injection_op"] == "remove"]
    commission = [p for p in pairs if p["ground_truth"]["injection_op"] == "replace"]
    om_caught = [p["flaw_id"] for p in omission if p["score"]["detected"]]
    cm_caught = [p["flaw_id"] for p in commission if p["score"]["detected"]]

    ax.axis("off")
    ax.set_title("B  Keyword baseline: blind to commission-type flaws",
                 fontsize=11, fontweight="bold", loc="left", color=INK)

    ax_om = ax.inset_axes([0.02, 0.28, 0.46, 0.58])
    ax_cm = ax.inset_axes([0.52, 0.28, 0.46, 0.58])
    _donut(ax_om, len(om_caught), len(omission),
           "omission (remove evidence)", MUTED, False, INK)
    _donut(ax_cm, len(cm_caught), len(commission),
           "commission (flawed evidence)", RED, True, RED)

    caught_names = ", ".join(om_caught) if om_caught else "none"
    ax.text(0.25, 0.16, f"caught: {caught_names}", ha="center", va="center",
            fontsize=7.5, color=MUTED, transform=ax.transAxes, wrap=True)
    ax.text(0.75, 0.16, "every flawed-but-present\nrewrite goes undetected",
            ha="center", va="center", fontsize=7.5, color=RED,
            transform=ax.transAxes)

    n = len(omission) + len(commission)
    det = llm["detection_rate"]
    ax.text(0.5, 0.02,
            f"LLM ({llm.get('model', 'gpt-4o')}) catches all {n} "
            f"(detection {det:.2f})",
            ha="center", va="center", fontsize=9, color=GREEN, fontweight="bold",
            transform=ax.transAxes)


def main() -> None:
    kw = keyword_result()
    llm = json.loads(LLM_SUMMARY.read_text())

    fig, axes = plt.subplots(1, 2, figsize=(11, 5.0), gridspec_kw={"width_ratios": [1, 1.05]})
    fig.patch.set_facecolor("white")
    panel_a(axes[0], kw["summary"], llm)
    panel_b(axes[1], kw["pairs"], llm)

    s = kw["summary"]
    fig.suptitle(
        "Keyword baseline vs LLM evidence-adequacy assessor "
        f"(n={s['n']} flaws, realistic injection)",
        fontsize=12.5, fontweight="bold", color=INK, y=0.99,
    )
    fig.legend(handles=[
        Patch(facecolor=GREEN, label="caught"),
        Patch(facecolor=MISSED_FILL, edgecolor=MISSED_EDGE, label="missed"),
    ], loc="lower center", ncol=2, fontsize=9, frameon=False, bbox_to_anchor=(0.5, -0.02))

    fig.tight_layout(rect=[0, 0.03, 1, 0.96])
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(OUT_DIR / f"figure_phase1.{ext}", dpi=200, bbox_inches="tight", facecolor="white")
    print(f"wrote {(OUT_DIR / 'figure_phase1.pdf').relative_to(ROOT)} and figure_phase1.png")
    print(f"  keyword: detection={s['detection_rate']:.3f}  "
          f"LLM: detection={llm['detection_rate']:.3f}")


if __name__ == "__main__":
    main()
