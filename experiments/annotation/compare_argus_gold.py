"""Compare ARGUS risk labels against adjudicated human gold.

The gold labels are intentionally gitignored (`data/annotations/gold_labels.csv`);
this script reports only aggregate calibration statistics. It evaluates two
unknown-handling policies:

1. Coverage mode: drop ARGUS `unknown` cells and score answered cells.
2. Strict mode: keep all cells and count `unknown` as a mismatch.

Run:
    PYTHONPATH=src python3 experiments/annotation/compare_argus_gold.py
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GOLD = ROOT / "data" / "annotations" / "gold_labels.csv"
DEFAULT_ARGUS = ROOT / "experiments" / "real_papers" / "corpus_results" / "did_llm_risks.csv"
DEFAULT_OUT = ROOT / "experiments" / "annotation" / "ARGUS_VS_GOLD.md"

ORDER = ["low", "medium", "high"]
ARGUS_ORDER = ["low", "medium", "high", "unknown"]
RANK = {label: i for i, label in enumerate(ORDER)}


def load_gold(path: Path) -> dict[tuple[str, str], dict[str, str]]:
    rows: dict[tuple[str, str], dict[str, str]] = {}
    with path.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            key = (row["paper_id"], row["dimension"])
            rows[key] = {
                "risk": (row.get("gold_risk") or "").strip().lower(),
                "ambiguous": (row.get("ambiguous") or "0").strip(),
            }
    return rows


def load_argus(path: Path) -> dict[tuple[str, str], str]:
    rows: dict[tuple[str, str], str] = {}
    with path.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            key = (row["paper_id"], row["dimension"])
            rows[key] = (row.get("risk") or "").strip().lower()
    return rows


def cohen_kappa(pairs: list[tuple[str, str]]) -> float:
    n = len(pairs)
    if not n:
        return float("nan")
    labels = sorted({v for pair in pairs for v in pair})
    po = sum(1 for a, b in pairs if a == b) / n
    a_marg = Counter(a for a, _ in pairs)
    b_marg = Counter(b for _, b in pairs)
    pe = sum((a_marg[label] / n) * (b_marg[label] / n) for label in labels)
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)


def weighted_kappa(pairs: list[tuple[str, str]], weight: str = "quadratic") -> float:
    ordinal = [(RANK[a], RANK[b]) for a, b in pairs if a in RANK and b in RANK]
    n = len(ordinal)
    if not n:
        return float("nan")
    k = len(ORDER)

    def cost(i: int, j: int) -> float:
        distance = abs(i - j) / (k - 1)
        return distance * distance if weight == "quadratic" else distance

    observed = Counter(ordinal)
    a_marg = Counter(a for a, _ in ordinal)
    b_marg = Counter(b for _, b in ordinal)
    numerator = sum(cost(i, j) * count for (i, j), count in observed.items())
    denominator = sum(
        cost(i, j) * (a_marg[i] * b_marg[j] / n)
        for i in range(k)
        for j in range(k)
    )
    return 1.0 - numerator / denominator if denominator else float("nan")


def fmt(x: float) -> str:
    return "nan" if x != x else f"{x:.3f}"


def pct(num: int, den: int) -> str:
    return "nan" if not den else f"{num / den:.3f}"


def confusion(
    keys: list[tuple[str, str]],
    gold: dict[tuple[str, str], dict[str, str]],
    argus: dict[tuple[str, str], str],
) -> dict[str, Counter[str]]:
    matrix: dict[str, Counter[str]] = {risk: Counter() for risk in ORDER}
    for key in keys:
        matrix[gold[key]["risk"]][argus[key]] += 1
    return matrix


def adjacent_share(pairs: list[tuple[str, str]]) -> float:
    disagreements = [
        (g, a) for g, a in pairs
        if g != a and g in RANK and a in RANK
    ]
    if not disagreements:
        return float("nan")
    adjacent = sum(1 for g, a in disagreements if abs(RANK[g] - RANK[a]) == 1)
    return adjacent / len(disagreements)


def binary_pairs(pairs: list[tuple[str, str]]) -> list[tuple[str, str]]:
    return [
        ("flag" if g != "low" else "low", "flag" if a != "low" else "low")
        for g, a in pairs
    ]


def summarize(
    keys: list[tuple[str, str]],
    gold: dict[tuple[str, str], dict[str, str]],
    argus: dict[tuple[str, str], str],
) -> dict[str, object]:
    pairs_all = [(gold[key]["risk"], argus[key]) for key in keys]
    answered_keys = [key for key in keys if argus[key] != "unknown"]
    pairs_answered = [(gold[key]["risk"], argus[key]) for key in answered_keys]
    strict_matches = sum(1 for g, a in pairs_all if g == a)
    answered_matches = sum(1 for g, a in pairs_answered if g == a)

    over = sum(1 for g, a in pairs_answered if RANK[a] > RANK[g])
    under = sum(1 for g, a in pairs_answered if RANK[a] < RANK[g])
    equal = sum(1 for g, a in pairs_answered if RANK[a] == RANK[g])

    high_flags = [key for key in answered_keys if argus[key] == "high"]
    false_high = [key for key in high_flags if gold[key]["risk"] != "high"]
    true_high = [key for key in high_flags if gold[key]["risk"] == "high"]
    gold_high = [key for key in keys if gold[key]["risk"] == "high"]
    unknown_keys = [key for key in keys if argus[key] == "unknown"]

    binary_answered = binary_pairs(pairs_answered)
    binary_matches = sum(1 for g, a in binary_answered if g == a)

    return {
        "n": len(keys),
        "answered_n": len(answered_keys),
        "unknown_n": len(unknown_keys),
        "coverage": len(answered_keys) / len(keys) if keys else float("nan"),
        "strict_exact": strict_matches / len(keys) if keys else float("nan"),
        "strict_kappa_4label": cohen_kappa(pairs_all),
        "answered_exact": answered_matches / len(answered_keys) if answered_keys else float("nan"),
        "answered_kappa": cohen_kappa(pairs_answered),
        "answered_weighted_kappa": weighted_kappa(pairs_answered),
        "answered_binary_kappa": cohen_kappa(binary_answered),
        "answered_binary_agreement": binary_matches / len(binary_answered) if binary_answered else float("nan"),
        "answered_adjacent_share": adjacent_share(pairs_answered),
        "over_n": over,
        "under_n": under,
        "equal_n": equal,
        "high_flags_n": len(high_flags),
        "true_high_n": len(true_high),
        "false_high_n": len(false_high),
        "gold_high_n": len(gold_high),
        "high_precision": len(true_high) / len(high_flags) if high_flags else float("nan"),
        "gold_high_recall": len(true_high) / len(gold_high) if gold_high else float("nan"),
        "argus_dist": Counter(a for _, a in pairs_all),
        "gold_dist": Counter(g for g, _ in pairs_all),
        "unknown_by_gold": Counter(gold[key]["risk"] for key in unknown_keys),
        "matrix": confusion(keys, gold, argus),
    }


def per_dimension(
    keys: list[tuple[str, str]],
    gold: dict[tuple[str, str], dict[str, str]],
    argus: dict[tuple[str, str], str],
) -> list[dict[str, object]]:
    by_dim: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for key in keys:
        by_dim[key[1]].append((gold[key]["risk"], argus[key]))

    rows = []
    for dim, pairs in sorted(by_dim.items()):
        answered = [(g, a) for g, a in pairs if a != "unknown"]
        high_false = sum(1 for g, a in answered if a == "high" and g != "high")
        rows.append({
            "dimension": dim,
            "n": len(pairs),
            "answered": len(answered),
            "unknown": sum(1 for _, a in pairs if a == "unknown"),
            "strict_exact": sum(1 for g, a in pairs if g == a) / len(pairs),
            "answered_exact": (
                sum(1 for g, a in answered if g == a) / len(answered)
                if answered else float("nan")
            ),
            "false_high": high_false,
        })
    return rows


def render_markdown(
    summary: dict[str, object],
    per_dim: list[dict[str, object]],
    gold_path: Path,
    argus_path: Path,
) -> str:
    argus_dist: Counter[str] = summary["argus_dist"]  # type: ignore[assignment]
    gold_dist: Counter[str] = summary["gold_dist"]  # type: ignore[assignment]
    unknown_by_gold: Counter[str] = summary["unknown_by_gold"]  # type: ignore[assignment]
    matrix: dict[str, Counter[str]] = summary["matrix"]  # type: ignore[assignment]

    lines = [
        "# ARGUS vs Adjudicated Human Gold",
        "",
        "Aggregate-only comparison; raw human labels remain gitignored in `data/annotations/`.",
        "",
        "## Inputs",
        "",
        f"- Gold: `{gold_path.relative_to(ROOT)}`",
        f"- ARGUS: `{argus_path.relative_to(ROOT)}`",
        "",
        "## Headline",
        "",
        "| unknown policy | n scored | exact agreement | Cohen's kappa | weighted kappa | binary flag kappa |",
        "|---|---:|---:|---:|---:|---:|",
        (
            "| exclude unknown | "
            f"{summary['answered_n']} | {fmt(summary['answered_exact'])} | "
            f"{fmt(summary['answered_kappa'])} | {fmt(summary['answered_weighted_kappa'])} | "
            f"{fmt(summary['answered_binary_kappa'])} |"
        ),
        (
            "| unknown = mismatch | "
            f"{summary['n']} | {fmt(summary['strict_exact'])} | "
            f"{fmt(summary['strict_kappa_4label'])} | n/a | n/a |"
        ),
        "",
        "## Coverage And Distributions",
        "",
        f"- ARGUS answered {summary['answered_n']}/{summary['n']} cells "
        f"({fmt(summary['coverage'])}); `unknown` = {summary['unknown_n']}.",
        f"- Gold distribution: low {gold_dist['low']}, medium {gold_dist['medium']}, high {gold_dist['high']}.",
        (
            "- ARGUS distribution on the gold subset: "
            f"low {argus_dist['low']}, medium {argus_dist['medium']}, "
            f"high {argus_dist['high']}, unknown {argus_dist['unknown']}."
        ),
        (
            "- Unknown-by-gold: "
            f"low {unknown_by_gold['low']}, medium {unknown_by_gold['medium']}, "
            f"high {unknown_by_gold['high']}."
        ),
        "",
        "## High-Risk Calibration",
        "",
        (
            f"- ARGUS emitted `high` on {summary['high_flags_n']}/{summary['n']} gold-subset cells; "
            f"gold has `high` on {summary['gold_high_n']}/{summary['n']} cells."
        ),
        (
            f"- ARGUS high precision: {summary['true_high_n']}/{summary['high_flags_n']} = "
            f"{fmt(summary['high_precision'])}; false-high count = {summary['false_high_n']}."
        ),
        (
            f"- Gold-high recall: {summary['true_high_n']}/{summary['gold_high_n']} = "
            f"{fmt(summary['gold_high_recall'])}."
        ),
        (
            f"- On answered cells, ARGUS is more severe than gold in {summary['over_n']}, "
            f"less severe in {summary['under_n']}, equal in {summary['equal_n']}."
        ),
        "",
        "## Confusion Matrix",
        "",
        "| gold \\ ARGUS | low | medium | high | unknown |",
        "|---|---:|---:|---:|---:|",
    ]
    for risk in ORDER:
        c = matrix[risk]
        lines.append(f"| {risk} | {c['low']} | {c['medium']} | {c['high']} | {c['unknown']} |")

    lines.extend([
        "",
        "## Per-Dimension Summary",
        "",
        "| dimension | n | answered | unknown | strict exact | answered exact | false high |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ])
    for row in per_dim:
        lines.append(
            "| {dimension} | {n} | {answered} | {unknown} | {strict_exact} | {answered_exact} | {false_high} |".format(
                dimension=row["dimension"],
                n=row["n"],
                answered=row["answered"],
                unknown=row["unknown"],
                strict_exact=fmt(row["strict_exact"]),  # type: ignore[arg-type]
                answered_exact=fmt(row["answered_exact"]),  # type: ignore[arg-type]
                false_high=row["false_high"],
            )
        )
    lines.extend([
        "",
        "## Reading",
        "",
        (
            "ARGUS is not merely noisy; on cells where it answers, it is strongly "
            "severity-biased upward. The key failure mode is false-high inflation, "
            "while `unknown` remains a useful abstention channel that should be "
            "reported separately from substantive high risk."
        ),
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold", type=Path, default=DEFAULT_GOLD)
    ap.add_argument("--argus", type=Path, default=DEFAULT_ARGUS)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    gold = load_gold(args.gold)
    argus = load_argus(args.argus)
    keys = sorted(set(gold) & set(argus))
    if not keys:
        raise SystemExit("no overlapping (paper_id, dimension) rows")

    summary = summarize(keys, gold, argus)
    dim_rows = per_dimension(keys, gold, argus)
    report = render_markdown(summary, dim_rows, args.gold, args.argus)
    args.out.write_text(report + "\n", encoding="utf-8")

    print(f"overlap: {summary['n']} cells")
    print(f"answered: {summary['answered_n']} | unknown: {summary['unknown_n']}")
    print(f"exclude unknown exact: {fmt(summary['answered_exact'])}")
    print(f"exclude unknown kappa: {fmt(summary['answered_kappa'])}")
    print(f"exclude unknown weighted kappa: {fmt(summary['answered_weighted_kappa'])}")
    print(f"unknown=mismatch exact: {fmt(summary['strict_exact'])}")
    print(f"unknown=mismatch kappa: {fmt(summary['strict_kappa_4label'])}")
    print(
        "ARGUS high precision: "
        f"{summary['true_high_n']}/{summary['high_flags_n']} = {fmt(summary['high_precision'])}"
    )
    print(f"wrote {args.out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
