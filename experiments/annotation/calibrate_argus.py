"""Apply a lightweight deterministic calibration layer to rich ARGUS labels.

The calibration uses only ARGUS-visible fields (`risk`, `evidence_status`,
`retrieval_quality`, and `rationale`). It does not inspect the human gold label.

Run:
    PYTHONPATH=src python3 experiments/annotation/calibrate_argus.py
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_IN = ROOT / "data" / "annotations" / "argus_rich_gold5.csv"
DEFAULT_OUT = ROOT / "data" / "annotations" / "argus_rich_gold5_calibrated.csv"


def rel(path: Path) -> str:
    path = path.resolve()
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def signals_contradiction(rationale: str) -> bool:
    text = rationale.lower()
    return any(
        token in text
        for token in (
            "contradict",
            "conflict",
            "opposite",
            "significant pre-treatment",
            "pre-treatment divergence",
            "wrong level",
            "inappropriate",
        )
    )


def calibrated_risk(row: dict[str, str]) -> tuple[str, str]:
    risk = (row.get("risk") or "").strip().lower()
    if risk != "high":
        return risk, "unchanged"

    evidence_status = (row.get("evidence_status") or "").strip().lower()
    retrieval_quality = (row.get("retrieval_quality") or "").strip().lower()
    rationale = row.get("rationale") or ""
    contradiction = signals_contradiction(rationale)

    if evidence_status == "missing" and retrieval_quality in {"weak", "failed"} and not contradiction:
        return "unknown", "retrieval_failure_high_to_unknown"

    if evidence_status == "partial" and not contradiction:
        return "medium", "partial_evidence_high_to_medium"

    return risk, "unchanged"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_IN)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    rows = list(csv.DictReader(args.input.open(encoding="utf-8")))
    if not rows:
        raise SystemExit(f"no rows in {args.input}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "paper_id",
        "dimension",
        "risk",
        "original_risk",
        "calibration_rule",
        "evidence_status",
        "retrieval_quality",
        "rationale",
    ]
    out_rows = []
    for row in rows:
        new_risk, rule = calibrated_risk(row)
        out_rows.append({
            "paper_id": row["paper_id"],
            "dimension": row["dimension"],
            "risk": new_risk,
            "original_risk": row.get("risk", ""),
            "calibration_rule": rule,
            "evidence_status": row.get("evidence_status", ""),
            "retrieval_quality": row.get("retrieval_quality", ""),
            "rationale": row.get("rationale", ""),
        })

    with args.out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(out_rows)

    print(f"input: {rel(args.input)}")
    print(f"output: {rel(args.out)}")
    print("original risk distribution:", dict(Counter(r.get("risk", "") for r in rows)))
    print("calibrated risk distribution:", dict(Counter(r["risk"] for r in out_rows)))
    print("calibration rules:", dict(Counter(r["calibration_rule"] for r in out_rows)))


if __name__ == "__main__":
    main()
