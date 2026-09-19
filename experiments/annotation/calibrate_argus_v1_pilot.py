# PROVENANCE -- pilot calibration layer, version 1 (the version behind Table 14 of the
# ClimateNLP 2026 camera-ready and experiments/annotation/CALIBRATION.md).
#
# This file was never committed: it was created on 2026-06-06T18:34:34Z and rewritten
# three minutes later (18:37:38Z) into the two-rule calibrate_argus.py that commit
# dc97a9f records. It was recovered on 2026-09-19 from the authoring session log
# (apply_patch "Add File" record) and is reproduced below BYTE-FOR-BYTE; nothing
# under this comment block has been edited. sha256 of the recovered body:
#   e7c21bf3ec75cd5ea9120eb956a21b30ecc6d0de29ce53b959e9bd0996282688
# Re-running it on the frozen pilot inputs reproduces both historical outputs cell
# for cell (55/55); see experiments/ablations/calibration_recheck.py.
#
# Scope: all four rules were written after an over-severity error analysis of the SAME
# five-paper pilot they are evaluated on. They never read the gold label at run time,
# but they are in-sample, exploratory rules, not a validated calibration method.
# The default --input/--out paths point at the uncommitted data/ directory; pass
# --input experiments/annotation/pilot_frozen/argus_rich_gold5.csv to use the frozen copy.
"""Apply a lightweight deterministic calibration layer to rich ARGUS labels.

The calibration uses only ARGUS-visible fields (`risk`, `evidence_status`,
`retrieval_quality`, and `rationale`). It does not inspect the human gold label.

Two weak-retrieval policies are supported:

- `medium`  : keep coverage and demote weak-retrieval high labels to medium.
- `unknown` : abstain on weak-retrieval high labels.

Run:
    PYTHONPATH=src python3 experiments/annotation/calibrate_argus.py --weak-high-action medium
    PYTHONPATH=src python3 experiments/annotation/calibrate_argus.py --weak-high-action unknown
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_IN = ROOT / "data" / "annotations" / "argus_rich_gold5.csv"
DEFAULT_OUT = ROOT / "data" / "annotations" / "argus_rich_gold5_calibrated.csv"

MODERN_DID_TERMS = (
    "callaway",
    "sun-abraham",
    "goodman-bacon",
    "modern estimator",
    "modern estimators",
)


def rel(path: Path) -> str:
    path = path.resolve()
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def calibrated_risk(row: dict[str, str], *, weak_high_action: str) -> tuple[str, str]:
    risk = (row.get("risk") or "").strip().lower()
    if risk != "high":
        return risk, "unchanged"

    dimension = row.get("dimension", "")
    evidence_status = (row.get("evidence_status") or "").strip().lower()
    retrieval_quality = (row.get("retrieval_quality") or "").strip().lower()
    rationale = (row.get("rationale") or "").lower()

    if retrieval_quality == "weak":
        return weak_high_action, f"weak_retrieval_high_to_{weak_high_action}"

    if dimension == "treatment_timing" and any(term in rationale for term in MODERN_DID_TERMS):
        return "medium", "modern_did_standard_high_to_medium"

    if (
        dimension == "inference"
        and evidence_status == "missing"
        and ("cluster" in rationale or "robust standard errors" in rationale)
    ):
        return "medium", "inference_reporting_gap_high_to_medium"

    if dimension == "concurrent_policies" and retrieval_quality == "good":
        return "medium", "concurrent_policy_closure_high_to_medium"

    return risk, "unchanged"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_IN)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--weak-high-action",
        choices=["medium", "unknown"],
        default="medium",
        help="How to calibrate ARGUS high labels when retrieval_quality is weak.",
    )
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
        new_risk, rule = calibrated_risk(row, weak_high_action=args.weak_high_action)
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
