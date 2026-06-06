"""Aggregate error analysis for ARGUS-vs-gold over-severity.

Raw human labels and per-cell rationales stay in gitignored `data/annotations/`.
This script writes:

- a gitignored per-cell diagnostic CSV for local inspection; and
- a committed aggregate Markdown report with counts only.

Run:
    PYTHONPATH=src python3 experiments/annotation/analyze_overseverity.py
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GOLD = ROOT / "data" / "annotations" / "gold_labels.csv"
DEFAULT_RICH = ROOT / "data" / "annotations" / "argus_rich_gold5.csv"
DEFAULT_DETAIL = ROOT / "data" / "annotations" / "argus_overseverity_cases.csv"
DEFAULT_OUT = ROOT / "experiments" / "annotation" / "OVERSEVERITY_ANALYSIS.md"

ORDER = ["low", "medium", "high"]
RANK = {label: i for i, label in enumerate(ORDER)}


def rel(path: Path) -> str:
    path = path.resolve()
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def load_gold(path: Path) -> dict[tuple[str, str], dict[str, str]]:
    out: dict[tuple[str, str], dict[str, str]] = {}
    with path.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            out[(row["paper_id"], row["dimension"])] = {
                "risk": row["gold_risk"].strip().lower(),
                "ambiguous": row.get("ambiguous", "0").strip(),
            }
    return out


def load_rich(path: Path) -> dict[tuple[str, str], dict[str, str]]:
    out: dict[tuple[str, str], dict[str, str]] = {}
    with path.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            out[(row["paper_id"], row["dimension"])] = row
    return out


def relation(gold: str, argus: str) -> str:
    if argus == "unknown":
        return "unknown"
    if argus == gold:
        return "equal"
    if RANK[argus] > RANK[gold]:
        return "over"
    return "under"


def write_detail(
    rows: list[dict[str, str]],
    gold: dict[tuple[str, str], dict[str, str]],
    out: Path,
) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "paper_id",
        "dimension",
        "gold_risk",
        "argus_risk",
        "severity_gap",
        "evidence_status",
        "retrieval_quality",
        "ambiguous_gold",
        "rationale",
    ]
    with out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            key = (row["paper_id"], row["dimension"])
            g = gold[key]["risk"]
            a = row["risk"]
            writer.writerow({
                "paper_id": key[0],
                "dimension": key[1],
                "gold_risk": g,
                "argus_risk": a,
                "severity_gap": str(RANK[a] - RANK[g]),
                "evidence_status": row.get("evidence_status", ""),
                "retrieval_quality": row.get("retrieval_quality", ""),
                "ambiguous_gold": gold[key].get("ambiguous", "0"),
                "rationale": row.get("rationale", ""),
            })


def table(counter: Counter, columns: tuple[str, str]) -> list[str]:
    lines = [
        f"| {columns[0]} | {columns[1]} |",
        "|---|---:|",
    ]
    for key, value in sorted(counter.items(), key=lambda kv: (-kv[1], str(kv[0]))):
        lines.append(f"| {key} | {value} |")
    return lines


def render_report(
    keys: list[tuple[str, str]],
    gold: dict[tuple[str, str], dict[str, str]],
    rich: dict[tuple[str, str], dict[str, str]],
    detail_path: Path,
    rich_path: Path,
) -> str:
    answered = [key for key in keys if rich[key]["risk"] != "unknown"]
    over = [key for key in answered if relation(gold[key]["risk"], rich[key]["risk"]) == "over"]
    under = [key for key in answered if relation(gold[key]["risk"], rich[key]["risk"]) == "under"]
    equal = [key for key in answered if relation(gold[key]["risk"], rich[key]["risk"]) == "equal"]
    high_over = [key for key in over if rich[key]["risk"] == "high"]

    over_rows = [rich[key] for key in over]
    over_by_dim = Counter(key[1] for key in over)
    over_by_status = Counter(rich[key].get("evidence_status", "") for key in over)
    over_by_retrieval = Counter(rich[key].get("retrieval_quality", "") for key in over)
    over_by_pattern = Counter(
        f"{rich[key]['risk']} vs gold={gold[key]['risk']} | "
        f"{rich[key].get('evidence_status', '')}/{rich[key].get('retrieval_quality', '')}"
        for key in over
    )

    weak_high = [
        key for key in answered
        if rich[key]["risk"] == "high" and rich[key].get("retrieval_quality") == "weak"
    ]
    missing_high = [
        key for key in answered
        if rich[key]["risk"] == "high" and rich[key].get("evidence_status") == "missing"
    ]

    lines = [
        "# ARGUS Over-Severity Error Analysis",
        "",
        "Aggregate-only report. Per-cell diagnostics are written to a gitignored CSV.",
        "",
        "## Inputs",
        "",
        f"- Rich ARGUS labels: `{rel(rich_path)}`",
        f"- Detail CSV: `{rel(detail_path)}`",
        "",
        "## Headline",
        "",
        f"- Gold-overlap cells: {len(keys)}.",
        f"- ARGUS answered {len(answered)}/{len(keys)} cells and abstained on {len(keys) - len(answered)}.",
        f"- Among answered cells: over-severe {len(over)}, equal {len(equal)}, under-severe {len(under)}.",
        f"- High-risk over-severity: {len(high_over)} over-severe cells where ARGUS used `high`.",
        f"- Weak-retrieval high labels: {len(weak_high)}.",
        f"- Missing-evidence high labels: {len(missing_high)}.",
        "",
        "## Over-Severity By Evidence Status",
        "",
        *table(over_by_status, ("evidence_status", "over-severe cells")),
        "",
        "## Over-Severity By Retrieval Quality",
        "",
        *table(over_by_retrieval, ("retrieval_quality", "over-severe cells")),
        "",
        "## Over-Severity By Dimension",
        "",
        *table(over_by_dim, ("dimension", "over-severe cells")),
        "",
        "## Dominant Patterns",
        "",
        *table(over_by_pattern, ("ARGUS/gold and evidence pattern", "over-severe cells")),
        "",
        "## Reading",
        "",
        (
            "The dominant failure is not random disagreement. Most over-severe "
            "answered cells are `high` labels attached to `missing` evidence under "
            "weak retrieval. This indicates a severity-calibration problem: ARGUS "
            "often turns thin or weakly retrieved evidence into substantive high risk "
            "instead of a medium flag or an abstention."
        ),
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gold", type=Path, default=DEFAULT_GOLD)
    parser.add_argument("--rich", type=Path, default=DEFAULT_RICH)
    parser.add_argument("--detail", type=Path, default=DEFAULT_DETAIL)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    gold = load_gold(args.gold)
    rich = load_rich(args.rich)
    keys = sorted(set(gold) & set(rich))
    if not keys:
        raise SystemExit("no overlapping (paper_id, dimension) rows")

    answered = [key for key in keys if rich[key]["risk"] != "unknown"]
    over = [
        rich[key] for key in answered
        if relation(gold[key]["risk"], rich[key]["risk"]) == "over"
    ]
    write_detail(over, gold, args.detail)
    args.out.write_text(render_report(keys, gold, rich, args.detail, args.rich), encoding="utf-8")

    print(f"overlap: {len(keys)}")
    print(f"answered: {len(answered)} | unknown: {len(keys) - len(answered)}")
    print(f"over-severe answered: {len(over)}")
    print(f"wrote {rel(args.out)}")
    print(f"wrote {rel(args.detail)}")


if __name__ == "__main__":
    main()
