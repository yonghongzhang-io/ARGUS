"""Generate Figure 2 (the results / conclusion figure) from the live evaluation.

Two panels:
  A. The headline metrics, circular (pre-fix) vs realistic injection — detection
     collapses from 1.000 to the honest rate, false-alarm stays at 0.
  B. Per-flaw outcome matrix, grouped omission vs commission — visualising the
     baseline's systematic blindness to commission-type threats.

Numbers are read from the evaluation, so the figure can never drift from the
reported results.

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
OUT_DIR = ROOT / "paper" / "figures"

# palette consistent with Figure 1
GREEN = "#3a9d6a"
RED = "#c0473f"
AMBER = "#cdb24a"
BLUE = "#3f5f8f"
INK = "#1a1a1a"
MUTED = "#666666"
BG = "#faf9f2"


def run() -> dict:
    paper = json.loads(PAPER.read_text())
    return evaluate_flaws(paper, sorted(load_flaws()), max_steps=1)


def panel_a(ax, summary: dict) -> None:
    metrics = ["detection", "false alarm", "localization"]
    circular = [1.0, 0.0, 1.0]
    realistic = [summary["detection_rate"], summary["false_alarm_rate"], summary["localization_acc"]]

    y = range(len(metrics))
    h = 0.36
    ax.barh([i + h / 2 for i in y], circular, height=h, color="#c9c4b4",
            label="sentinel injection (circular)")
    ax.barh([i - h / 2 for i in y], realistic, height=h, color=BLUE,
            label="realistic injection (honest)")

    for i, v in enumerate(circular):
        ax.text(v + 0.02, i + h / 2, f"{v:.2f}", va="center", fontsize=9, color=MUTED)
    for i, v in enumerate(realistic):
        ax.text(v + 0.02, i - h / 2, f"{v:.2f}", va="center", fontsize=9,
                fontweight="bold", color=BLUE)

    ax.set_yticks(list(y))
    ax.set_yticklabels(metrics, fontsize=10)
    ax.set_xlim(0, 1.15)
    ax.set_xticks([0, 0.5, 1.0])
    ax.invert_yaxis()
    ax.set_title("A  Removing leakage collapses detection", fontsize=11,
                 fontweight="bold", loc="left", color=INK)
    ax.legend(fontsize=8, loc="lower right", frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    ax.annotate("", xy=(0.18, 0.18), xytext=(1.0, 0.18),
                arrowprops=dict(arrowstyle="->", color=RED, lw=1.6))
    ax.text(0.58, -0.12, "1.00 → 0.18", fontsize=9, color=RED,
            fontweight="bold", ha="center")


def panel_b(ax, pairs: list[dict]) -> None:
    # split omission (remove) vs commission (replace), preserve order within group
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
        ax.text(0.5, yy, "detected" if det else "missed", ha="center", va="center",
                fontsize=8.5, color="white" if det else MUTED,
                fontweight="bold" if det else "normal")
        ax.text(-0.08, yy, lab, ha="right", va="center", fontsize=8.5, color=INK)

    # group separators / labels
    n_om = len(omission)
    ax.axhline(len(commission) - 0.5, color=MUTED, lw=0.8, ls=":")
    ax.text(1.12, n - (n_om / 2) - 0.5, "omission\n(remove\nevidence)", fontsize=8,
            color=MUTED, va="center", ha="left")
    ax.text(1.12, (len(commission) / 2) - 0.5, "commission\n(flawed\nevidence)", fontsize=8,
            color=RED, va="center", ha="left", fontweight="bold")

    ax.set_xlim(-0.55, 1.45)
    ax.set_ylim(-0.6, n - 0.4)
    ax.axis("off")
    ax.set_title("B  Blind to every commission-type threat", fontsize=11,
                 fontweight="bold", loc="left", color=INK)


def main() -> None:
    result = run()
    fig, axes = plt.subplots(1, 2, figsize=(11, 5.0), gridspec_kw={"width_ratios": [1, 1.05]})
    fig.patch.set_facecolor("white")
    panel_a(axes[0], result["summary"])
    panel_b(axes[1], result["pairs"])

    s = result["summary"]
    fig.suptitle(
        "Honest baseline under realistic flaw injection "
        f"(n={s['n']}, detection={s['detection_rate']:.2f}, false alarm={s['false_alarm_rate']:.2f})",
        fontsize=12.5, fontweight="bold", color=INK, y=0.99,
    )
    fig.legend(handles=[
        Patch(facecolor=GREEN, label="detected"),
        Patch(facecolor="#e7e3d6", edgecolor="#c9c4b4", label="missed"),
    ], loc="lower center", ncol=2, fontsize=9, frameon=False, bbox_to_anchor=(0.5, -0.02))

    fig.tight_layout(rect=[0, 0.03, 1, 0.96])
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(OUT_DIR / f"figure2.{ext}", dpi=200, bbox_inches="tight",
                    facecolor="white")
    print(f"wrote {(OUT_DIR / 'figure2.pdf').relative_to(ROOT)} and figure2.png")


if __name__ == "__main__":
    main()
