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


ORDER = ["low", "medium", "high"]  # ordinal severity (unknown excluded from weighted/ordinal stats)


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


def weighted_kappa(pairs: list[tuple[str, str]], weight: str = "quadratic") -> float:
    """Ordinal weighted kappa over ORDER; pairs with off-scale labels are dropped."""
    idx = {l: i for i, l in enumerate(ORDER)}
    ps = [(idx[a], idx[b]) for a, b in pairs if a in idx and b in idx]
    n, k = len(ps), len(ORDER)
    if not ps:
        return float("nan")

    def w(i: int, j: int) -> float:
        d = abs(i - j) / (k - 1)
        return d * d if weight == "quadratic" else d

    obs = Counter(ps)
    am = Counter(i for i, _ in ps)
    bm = Counter(j for _, j in ps)
    num = sum(w(i, j) * c for (i, j), c in obs.items())
    den = sum(w(i, j) * (am.get(i, 0) * bm.get(j, 0) / n) for i in range(k) for j in range(k))
    return 1.0 - num / den if den else float("nan")


def load_many(paths: list[Path], field: str) -> dict[tuple[str, str], str]:
    merged: dict[tuple[str, str], str] = {}
    for p in paths:
        merged.update(load(p, field))
    return merged


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("csv_a", nargs="?")
    ap.add_argument("csv_b", nargs="?")
    ap.add_argument("--dir", help="directory of *_A.csv / *_B.csv sheets (overrides positional)")
    ap.add_argument("--field", default="risk")
    args = ap.parse_args()

    if args.dir:
        d = Path(args.dir)
        a = load_many(sorted(d.glob("*_A.csv")), args.field)
        b = load_many(sorted(d.glob("*_B.csv")), args.field)
        if not a or not b:
            raise SystemExit(f"no *_A.csv / *_B.csv with filled '{args.field}' in {d}")
    else:
        if not (args.csv_a and args.csv_b):
            raise SystemExit("pass two CSVs, or --dir <folder of *_A.csv/*_B.csv>")
        a = load(Path(args.csv_a), args.field)
        b = load(Path(args.csv_b), args.field)
    keys = sorted(set(a) & set(b))
    if not keys:
        raise SystemExit("no overlapping (paper_id, dimension) rows between the two files")

    pairs = [(a[k], b[k]) for k in keys]
    n = len(pairs)
    pct = sum(1 for x, y in pairs if x == y) / n

    # binary: flagged (medium+high) vs low
    binf = [("flag" if x != "low" else "low", "flag" if y != "low" else "low") for x, y in pairs]
    bin_pct = sum(1 for x, y in binf if x == y) / n
    # adjacent-disagreement share (of disagreements, fraction that are one ordinal step)
    idx = {l: i for i, l in enumerate(ORDER)}
    disagree = [(x, y) for x, y in pairs if x != y and x in idx and y in idx]
    adj = sum(1 for x, y in disagree if abs(idx[x] - idx[y]) == 1)
    adj_share = adj / len(disagree) if disagree else float("nan")

    print(f"overlap: {n} (paper, dimension) cells | field: {args.field}\n")
    print("headline four numbers:")
    print(f"  exact 3-level agreement : {pct:.3f}")
    print(f"  weighted kappa (quad)   : {weighted_kappa(pairs):.3f}")
    print(f"  binary flag-vs-low kappa: {cohen_kappa(binf):.3f}  (agreement {bin_pct:.3f})")
    print(f"  adjacent-disagreement   : {adj_share:.3f}  of disagreements are one step")
    print(f"  [Cohen's kappa 3-level  : {cohen_kappa(pairs):.3f}]\n")

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
