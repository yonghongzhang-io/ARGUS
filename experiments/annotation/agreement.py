"""Inter-annotator agreement on dimension-level risk labels.

Reads two filled annotation CSVs (same papers, two annotators), aligns on
(paper_id, dimension), and reports Cohen's kappa on the `risk` field plus a list
of disagreements. Also works for ARGUS-vs-human: pass an ARGUS risk CSV
(paper_id,dimension,risk from run_corpus.py) as one side.

Cohen's kappa is computed dependency-free.

Usage:
    PYTHONPATH=src python3 experiments/annotation/agreement.py A.csv B.csv [--field risk]
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path


def load(path: Path, field: str) -> dict[tuple[str, str], str]:
    out: dict[tuple[str, str], str] = {}
    with open(path, encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            val = (row.get(field) or "").strip().lower()
            if val:
                out[(row["paper_id"], row["dimension"])] = val
    return out


def cohen_kappa(pairs: list[tuple[str, str]]) -> float:
    n = len(pairs)
    if n == 0:
        return float("nan")
    labels = sorted({v for p in pairs for v in p})
    po = sum(1 for a, b in pairs if a == b) / n
    a_marg = Counter(a for a, _ in pairs)
    b_marg = Counter(b for _, b in pairs)
    pe = sum((a_marg.get(l, 0) / n) * (b_marg.get(l, 0) / n) for l in labels)
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("csv_a")
    ap.add_argument("csv_b")
    ap.add_argument("--field", default="risk")
    args = ap.parse_args()

    a = load(Path(args.csv_a), args.field)
    b = load(Path(args.csv_b), args.field)
    keys = sorted(set(a) & set(b))
    if not keys:
        raise SystemExit("no overlapping (paper_id, dimension) rows between the two files")

    pairs = [(a[k], b[k]) for k in keys]
    overall = cohen_kappa(pairs)
    pct = sum(1 for x, y in pairs if x == y) / len(pairs)
    print(f"overlap: {len(keys)} (paper, dimension) cells | field: {args.field}")
    print(f"percent agreement: {pct:.3f} | Cohen's kappa: {overall:.3f}\n")

    # per-dimension kappa
    by_dim: dict[str, list[tuple[str, str]]] = {}
    for (paper, dim) in keys:
        by_dim.setdefault(dim, []).append((a[(paper, dim)], b[(paper, dim)]))
    print(f"{'dimension':28}{'n':>4}{'kappa':>8}")
    print("-" * 40)
    for dim in sorted(by_dim):
        ps = by_dim[dim]
        print(f"{dim:28}{len(ps):>4}{cohen_kappa(ps):>8.3f}")

    print("\ndisagreements:")
    for (paper, dim) in keys:
        if a[(paper, dim)] != b[(paper, dim)]:
            print(f"  {paper:16} {dim:26} A={a[(paper, dim)]:8} B={b[(paper, dim)]}")


if __name__ == "__main__":
    main()
