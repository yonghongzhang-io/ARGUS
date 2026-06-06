"""Figure: keyword vs two-stage LLM risk distribution on real DID papers.

Reads the per-paper-per-dimension CSVs written by run_corpus.py for both
assessors and draws, per identification dimension, the share of papers in each
risk bucket (high / medium / low / unknown). The contrast is the story: the
keyword baseline is almost all `low` (credulous), while the two-stage LLM shows
a differentiated profile including `unknown` (honest retrieval failure) instead
of false `high`.

Run (after running run_corpus.py for both assessors at the same --n):
    PYTHONPATH=src python3 experiments/real_papers/make_realcorpus_figure.py
"""

from __future__ import annotations

import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from argus.config import load_dimensions  # noqa: E402

RES = Path(__file__).resolve().parent / "corpus_results"
OUT_DIR = ROOT / "paper" / "figures"
BUCKETS = ["high", "medium", "low", "unknown"]
COLORS = {"high": "#c0473f", "medium": "#cdb24a", "low": "#3a9d6a", "unknown": "#9a9483"}


def load_counts(path: Path) -> tuple[dict[str, Counter], int]:
    """dimension -> Counter(risk); also the number of distinct papers."""
    counts: dict[str, Counter] = defaultdict(Counter)
    papers: set[str] = set()
    with open(path, encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            counts[row["dimension"]][row["risk"]] += 1
            papers.add(row["paper_id"])
    return counts, len(papers)


def panel(ax, counts: dict[str, Counter], dims: list[str], title: str) -> None:
    y = range(len(dims))
    for i, dim in enumerate(reversed(dims)):
        c = counts.get(dim, Counter())
        total = sum(c.values()) or 1
        left = 0.0
        for b in BUCKETS:
            frac = c.get(b, 0) / total
            if frac:
                ax.barh(i, frac, left=left, color=COLORS[b], edgecolor="white", linewidth=0.5)
            left += frac
    ax.set_yticks(list(y))
    ax.set_yticklabels(list(reversed(dims)), fontsize=8.5)
    ax.set_xlim(0, 1)
    ax.set_xlabel("share of papers", fontsize=9)
    ax.set_title(title, fontsize=11, fontweight="bold", loc="left")
    ax.spines[["top", "right"]].set_visible(False)


def main() -> None:
    kw_path = RES / "did_keyword_risks.csv"
    llm_path = RES / "did_llm_risks.csv"
    if not (kw_path.exists() and llm_path.exists()):
        sys.exit("Run run_corpus.py for BOTH --assessor keyword and --llm first "
                 f"(missing {kw_path.name} or {llm_path.name}).")

    dims = list(load_dimensions())
    kw, n_kw = load_counts(kw_path)
    llm, n_llm = load_counts(llm_path)

    fig, axes = plt.subplots(1, 2, figsize=(12, 5.2), sharey=True)
    fig.patch.set_facecolor("white")
    panel(axes[0], kw, dims, f"keyword baseline (n={n_kw})")
    panel(axes[1], llm, dims, f"two-stage LLM (n={n_llm})")
    fig.suptitle("Per-dimension risk distribution on real DID papers",
                 fontsize=12.5, fontweight="bold", y=0.99)
    fig.legend(handles=[Patch(facecolor=COLORS[b], label=b) for b in BUCKETS],
               loc="lower center", ncol=4, fontsize=9, frameon=False, bbox_to_anchor=(0.5, -0.02))
    fig.tight_layout(rect=[0, 0.04, 1, 0.96])

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(OUT_DIR / f"figure_realcorpus.{ext}", dpi=200, bbox_inches="tight", facecolor="white")
    print(f"wrote paper/figures/figure_realcorpus.pdf  (keyword n={n_kw}, llm n={n_llm})")


if __name__ == "__main__":
    main()
