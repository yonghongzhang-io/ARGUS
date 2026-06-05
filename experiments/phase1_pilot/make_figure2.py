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

from argus.config import load_flaws  # noqa: E402
from argus.evaluation.runner import evaluate_flaws  # noqa: E402

PAPER = ROOT / "examples" / "papers" / "clean_supported.json"
LLM_SUMMARY = Path(__file__).resolve().parent / "llm_summary.json"
OUT_DIR = ROOT / "paper" / "figures"

GREEN = "#3a9d6a"
RED = "#c0473f"
GRAY = "#9a9483"
INK = "#1a1a1a"
MUTED = "#666666"


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
    ax.annotate("", xy=(1.0, 0.16), xytext=(0.182, 0.16),
                arrowprops=dict(arrowstyle="->", color=GREEN, lw=1.6))
    ax.text(0.58, -0.18, "0.18 → 1.00", fontsize=9, color=GREEN,
            fontweight="bold", ha="center")


def panel_b(ax, pairs: list[dict], llm: dict) -> None:
    omission = [p for p in pairs if p["ground_truth"]["injection_op"] == "remove"]
    commission = [p for p in pairs if p["ground_truth"]["injection_op"] == "replace"]
    ordered = omission + commission
    labels = [p["flaw_id"] for p in ordered]
    detected = [p["score"]["detected"] for p in ordered]
    n = len(ordered)

    for i, (lab, det) in enumerate(zip(labels, detected)):
        yy = n - 1 - i
        color = GREEN if det else "#e7e3d6"
        edge = GREEN if det else "#c9c4b4"
        ax.add_patch(plt.Rectangle((0, yy - 0.42), 1, 0.84, facecolor=color,
                                   edgecolor=edge, lw=1.2))
        ax.text(0.5, yy, "caught" if det else "missed", ha="center", va="center",
                fontsize=8.5, color="white" if det else MUTED,
                fontweight="bold" if det else "normal")
        ax.text(-0.08, yy, lab, ha="right", va="center", fontsize=8.5, color=INK)

    ax.axhline(len(commission) - 0.5, color=MUTED, lw=0.8, ls=":")
    n_om = len(omission)
    ax.text(1.12, n - (n_om / 2) - 0.5, "omission\n(remove\nevidence)", fontsize=8,
            color=MUTED, va="center", ha="left")
    ax.text(1.12, (len(commission) / 2) - 0.5, "commission\n(flawed\nevidence)", fontsize=8,
            color=RED, va="center", ha="left", fontweight="bold")

    ax.set_xlim(-0.55, 1.5)
    ax.set_ylim(-1.15, n - 0.4)
    ax.axis("off")
    ax.set_title("B  Keyword baseline: blind to commission-type flaws",
                 fontsize=11, fontweight="bold", loc="left", color=INK)
    det = llm["detection_rate"]
    ax.text(0.5, -0.95,
            f"LLM ({llm.get('model', 'gpt-4o')}) catches all {len(ordered)} "
            f"(detection {det:.2f})",
            ha="center", va="center", fontsize=9, color=GREEN, fontweight="bold")


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
        Patch(facecolor="#e7e3d6", edgecolor="#c9c4b4", label="missed"),
    ], loc="lower center", ncol=2, fontsize=9, frameon=False, bbox_to_anchor=(0.5, -0.02))

    fig.tight_layout(rect=[0, 0.03, 1, 0.96])
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(OUT_DIR / f"figure2.{ext}", dpi=200, bbox_inches="tight", facecolor="white")
    print(f"wrote {(OUT_DIR / 'figure2.pdf').relative_to(ROOT)} and figure2.png")
    print(f"  keyword: detection={s['detection_rate']:.3f}  "
          f"LLM: detection={llm['detection_rate']:.3f}")


if __name__ == "__main__":
    main()
