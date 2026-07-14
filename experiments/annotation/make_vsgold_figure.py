"""Four-panel diagnostic figure: ARGUS-LLM vs adjudicated human gold.

Reads the SAME sources as Table 2 (gold_labels.csv + did_llm_risks.csv) so the
figure cannot diverge from the table. Panels: (A) coverage, (B) risk
distributions, (C) error direction among answered cells, (D) ARGUS-by-gold
confusion matrix.

Run: PYTHONPATH=src python3 experiments/annotation/make_vsgold_figure.py
(gold_labels.csv is gitignored; run where the gold exists. Output PDF is committed.)
"""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
import sys; sys.path.insert(0, str(ROOT / "experiments"))  # noqa: E402
from figstyle import RISK, PALETTE, apply_style  # noqa: E402

apply_style()

GOLD = ROOT / "data" / "annotations" / "gold_labels.csv"
ARGUS = ROOT / "experiments" / "real_papers" / "corpus_results" / "did_llm_risks.csv"
OUT_DIR = ROOT / "paper" / "figures"

C = RISK
INK = PALETTE["ink"]
ACCENT = PALETTE["accent"]
MUTED = PALETTE["muted"]
RANK = {"low": 0, "medium": 1, "high": 2}


def load(path: Path, col: str) -> dict:
    return {(r["paper_id"], r["dimension"]): r[col] for r in csv.DictReader(open(path, encoding="utf-8"))}


def main() -> None:
    gold = load(GOLD, "gold_risk")
    argus = load(ARGUS, "risk")
    keys = sorted(set(gold) & set(argus))
    gd = Counter(gold[k] for k in keys)
    ad = Counter(argus[k] for k in keys)
    ans = [k for k in keys if argus[k] != "unknown"]
    over = sum(RANK[argus[k]] > RANK[gold[k]] for k in ans)
    exact = sum(argus[k] == gold[k] for k in ans)
    under = sum(RANK[argus[k]] < RANK[gold[k]] for k in ans)

    fig, ax = plt.subplots(2, 2, figsize=(8.8, 6.2))
    fig.patch.set_facecolor("white")
    (axA, axB), (axC, axD) = ax

    # ---- Panel A: coverage donut ----
    answered = len(ans)
    unknown = len(keys) - answered
    axA.pie([answered, unknown], colors=[ACCENT, C["unknown"]],
            startangle=90, counterclock=False, radius=1.38,
            wedgeprops=dict(width=0.58, edgecolor="white"))
    axA.set_xlim(-1.5, 1.5); axA.set_ylim(-1.5, 1.5)   # room for the enlarged donut
    axA.text(0, 0, f"{len(keys)}\ncells", ha="center", va="center", fontsize=13, fontweight="bold")
    axA.set_title("A  Coverage", fontsize=11, fontweight="bold", loc="left", color=INK)
    axA.legend(handles=[Patch(facecolor=ACCENT, label=f"answered ({answered})"),
                        Patch(facecolor=C["unknown"], label=f"unknown ({unknown})")],
               fontsize=8.5, loc="center", bbox_to_anchor=(0.5, -0.16), frameon=False, ncol=1)

    # ---- Panel B: risk distributions (gold vs ARGUS) ----
    def stack(ax, y, dist, order):
        left = 0
        for lab in order:
            v = dist.get(lab, 0)
            if v:
                ax.barh(y, v, left=left, color=C[lab], edgecolor="white", height=0.6)
                ax.text(left + v / 2, y, str(v), ha="center", va="center", fontsize=8,
                        color="white", fontweight="bold")
            left += v
    stack(axB, 1, gd, ["low", "medium", "high"])
    stack(axB, 0, ad, ["low", "medium", "high", "unknown"])
    axB.set_yticks([0, 1]); axB.set_yticklabels(["ARGUS", "human gold"], fontsize=9)
    axB.set_xlim(0, len(keys)); axB.set_title("B  Risk distribution", fontsize=11,
                                              fontweight="bold", loc="left", color=INK)
    axB.spines[["top", "right"]].set_visible(False)
    axB.legend(handles=[Patch(facecolor=C[l], label=l) for l in ["low", "medium", "high", "unknown"]],
               fontsize=7.5, loc="lower center", bbox_to_anchor=(0.5, -0.32), ncol=4, frameon=False)

    # ---- Panel C: error direction among answered ----
    left = 0
    for v, col, lab in [(over, C["high"], "over-severe"), (exact, C["low"], "exact"),
                        (under, MUTED, "under-severe")]:
        if v:
            axC.barh(0, v, left=left, color=col, edgecolor="white", height=0.5)
            axC.text(left + v / 2, 0, str(v), ha="center", va="center", fontsize=9,
                     color="white", fontweight="bold")
        left += v
    axC.set_xlim(0, len(ans)); axC.set_ylim(-0.6, 0.6); axC.set_yticks([])
    axC.set_title(f"C  Error direction ({len(ans)} answered)", fontsize=11,
                  fontweight="bold", loc="left", color=INK)
    axC.spines[["top", "right", "left"]].set_visible(False)
    axC.legend(handles=[Patch(facecolor=C["high"], label=f"over-severe ({over})"),
                        Patch(facecolor=C["low"], label=f"exact ({exact})"),
                        Patch(facecolor=MUTED, label=f"under-severe ({under})")],
               fontsize=7.5, loc="lower center", bbox_to_anchor=(0.5, -0.42), ncol=3, frameon=False)

    # ---- Panel D: confusion matrix (rows ARGUS, cols gold) ----
    rows = ["low", "medium", "high", "unknown"]; cols = ["low", "medium", "high"]
    M = [[sum(1 for k in keys if argus[k] == r and gold[k] == c) for c in cols] for r in rows]
    axD.imshow(M, cmap="Blues", aspect="auto")
    axD.set_xticks(range(len(cols))); axD.set_xticklabels(cols, fontsize=8.5)
    axD.set_yticks(range(len(rows))); axD.set_yticklabels(rows, fontsize=8.5)
    axD.set_xlabel("human gold", fontsize=9); axD.set_ylabel("ARGUS", fontsize=9)
    mx = max(max(r) for r in M)
    for i, r in enumerate(rows):
        for j, c in enumerate(cols):
            axD.text(j, i, str(M[i][j]), ha="center", va="center", fontsize=9,
                     color="white" if M[i][j] > mx * 0.55 else INK)
    axD.set_title("D  Confusion matrix", fontsize=11, fontweight="bold", loc="left", color=INK)

    fig.suptitle("ARGUS--LLM vs. adjudicated human gold: diagnostic breakdown",
                 fontsize=12.5, fontweight="bold", color=INK, y=1.0)
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(OUT_DIR / f"figure_vsgold.{ext}", dpi=200, bbox_inches="tight", facecolor="white")
    print("wrote paper/figures/figure_vsgold.pdf",
          f"| answered={answered} unknown={unknown} over={over} exact={exact} under={under}")


if __name__ == "__main__":
    main()
