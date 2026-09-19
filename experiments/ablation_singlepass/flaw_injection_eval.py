#!/usr/bin/env python3
# =====================================================================
# ARGUS -- flaw-injection evaluation harness (assessor-agnostic)
# ---------------------------------------------------------------------
# Scores ANY assessor policy (single-pass LLM, or a mock) under the SAME
# flaw-injection protocol, so the comparison isolates how each JUDGES the
# evidence. Loads the CANONICAL rubric via argus.config.load_dimensions()
# -- the exact file the pipeline runs on -- so M4 is not run on a hand-
# copied parallel rubric.
#
# Manifest schema (JSON list); one row per (base_paper, flaw):
#   {
#     "base_paper": "clean_supported",
#     "flaw_id": "pretrend_divergence",
#     "target_dimension": "parallel_trends",
#     "clean_path": "fixtures/clean_supported.txt",
#     "injected_path": "fixtures/clean_supported__pretrend_divergence.txt"
#   }
#
# Metrics (scored against the INJECTED FLAW as local ground truth):
#   detection   : injected target-dim risk in {medium, high}
#   false_alarm : clean   target-dim risk in {medium, high}
#   localization: target dim is the unique argmax-risk dimension on the
#                 injected version (ties / all-unknown count as a miss)
#
# Emits per-flaw rows + per-base-paper aggregates (mean +/- SD), so a
# headline number is reported WITH paper-level variance (M1), not pooled
# over flaws on a single fixture.
# =====================================================================
from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(HERE))

from argus.config import load_dimensions  # noqa: E402

RISK_RANK = {"unknown": -1, "low": 0, "medium": 1, "high": 2}
FLAGGED = {"medium", "high"}

# Flaw -> dimension map (mirrors config/flaw_taxonomy.yaml; verified against it
# at runtime via argus.config.load_flaws()).
FLAW_TO_DIM = {
    "pretrend_divergence": "parallel_trends",
    "anticipation_effect": "no_anticipation",
    "forbidden_comparison": "treatment_timing",
    "spillover_contamination": "treatment_definition_sutva",
    "noncomparable_controls": "control_group",
    "bad_control": "specification",
    "understated_se": "inference",
    "cherrypicked_window": "sample_period",
    "confounding_policy": "concurrent_policies",
    "missing_placebo": "robustness_placebo",
    "measurement_break": "data_measurement",
}


def _localizes(judged: dict, target: str) -> bool:
    """True iff target dim is the (unique) most-severe flagged dimension."""
    ranks = {d: RISK_RANK.get(c["risk"], -1) for d, c in judged.items()}
    top = max(ranks.values())
    if top < RISK_RANK["medium"]:
        return False
    winners = [d for d, r in ranks.items() if r == top]
    return winners == [target]


def evaluate(manifest: list[dict],
             assessor: Callable[[str, dict], dict],
             dims: dict[str, Any],
             read_text: Callable[[str], str] = lambda p: Path(p).read_text(encoding="utf-8")) -> dict:
    rows = []
    for row in manifest:
        tdim = row["target_dimension"]
        assert FLAW_TO_DIM.get(row["flaw_id"], tdim) == tdim, \
            f"flaw {row['flaw_id']} should target {FLAW_TO_DIM.get(row['flaw_id'])}"
        clean = assessor(read_text(row["clean_path"]), dims)
        inj = assessor(read_text(row["injected_path"]), dims)
        detected = inj[tdim]["risk"] in FLAGGED
        false_alarm = clean[tdim]["risk"] in FLAGGED
        localized = _localizes(inj, tdim)
        rows.append({
            "base_paper": row["base_paper"], "flaw_id": row["flaw_id"],
            "target_dimension": tdim,
            "clean_risk": clean[tdim]["risk"], "injected_risk": inj[tdim]["risk"],
            "detected": detected, "false_alarm": false_alarm, "localized": localized,
        })

    n = len(rows)
    pooled = {
        "n_flaws": n,
        "detection": sum(r["detected"] for r in rows) / n,
        "false_alarm": sum(r["false_alarm"] for r in rows) / n,
        "localization": sum(r["localized"] for r in rows) / n,
    }
    by_paper = defaultdict(list)
    for r in rows:
        by_paper[r["base_paper"]].append(r)
    per_paper = {}
    for p, rs in by_paper.items():
        k = len(rs)
        per_paper[p] = {
            "n_flaws": k,
            "detection": sum(r["detected"] for r in rs) / k,
            "false_alarm": sum(r["false_alarm"] for r in rs) / k,
            "localization": sum(r["localized"] for r in rs) / k,
        }
    det = [m["detection"] for m in per_paper.values()]
    summary = {
        "pooled": pooled,
        "per_paper": per_paper,
        "paper_level": {
            "n_papers": len(per_paper),
            "detection_mean": statistics.mean(det),
            "detection_sd": statistics.pstdev(det) if len(det) > 1 else 0.0,
        },
    }
    return {"rows": rows, "summary": summary}


# ---------------------------------------------------------------------
# Self-test: a deterministic MOCK assessor validates the metric logic
# end-to-end without any LLM. Flags a dimension `high` when its trigger
# phrase is ABSENT (omission-style detector), `low` otherwise.
# ---------------------------------------------------------------------
_TRIGGERS = {
    "parallel_trends": "event-study pre-trend test null leads",
    "robustness_placebo": "placebo falsification test",
    "data_measurement": "consistent measurement across the panel",
}


def _mock_assessor(text: str, dims: dict[str, Any]) -> dict:
    out = {}
    for did in dims:
        trig = _TRIGGERS.get(did)
        if trig is None:
            out[did] = {"risk": "low", "evidence": "", "rationale": "n/a"}
        else:
            present = trig in text
            out[did] = {
                "risk": "low" if present else "high",
                "evidence": trig if present else "",
                "rationale": "present" if present else "absent",
            }
    return out


def _self_test() -> None:
    dims = load_dimensions()  # CANONICAL rubric
    clean = ("event-study pre-trend test null leads. "
             "placebo falsification test. "
             "consistent measurement across the panel.")
    injected = clean.replace("placebo falsification test. ", "")
    texts = {"c.txt": clean, "i.txt": injected}
    manifest = [{
        "base_paper": "fixtureA", "flaw_id": "missing_placebo",
        "target_dimension": "robustness_placebo",
        "clean_path": "c.txt", "injected_path": "i.txt",
    }]
    res = evaluate(manifest, _mock_assessor, dims, read_text=lambda p: texts[p])
    r = res["rows"][0]
    assert r["detected"] is True, r
    assert r["false_alarm"] is False, r
    assert r["localized"] is True, r
    manifest2 = [{
        "base_paper": "fixtureA", "flaw_id": "understated_se",
        "target_dimension": "inference",
        "clean_path": "c.txt", "injected_path": "i.txt",
    }]
    res2 = evaluate(manifest2, _mock_assessor, dims, read_text=lambda p: texts[p])
    assert res2["rows"][0]["detected"] is False, res2["rows"][0]
    print("self-test OK  (canonical rubric:", len(dims), "dims)")
    print("  detected/false_alarm/localized:", r["detected"], r["false_alarm"], r["localized"])
    print("  pooled:", res["summary"]["pooled"])
    print("  paper_level:", res["summary"]["paper_level"])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", help="flaw manifest JSON")
    ap.add_argument("--assessor", choices=["single_pass", "mock"], default="mock")
    ap.add_argument("--model", default=None, help="overrides ARGUS_LLM_MODEL/gpt-4o")
    ap.add_argument("--out", default="ablation_results.json")
    args = ap.parse_args()

    dims = load_dimensions()  # the SAME rubric the pipeline runs on
    if not args.manifest:
        _self_test()
        raise SystemExit(0)

    if args.assessor == "single_pass":
        from argus.agent.single_pass_assessor import make_single_pass_assessor
        assessor = make_single_pass_assessor(model=args.model)
    else:
        assessor = _mock_assessor

    manifest = json.load(open(args.manifest, encoding="utf-8"))
    res = evaluate(manifest, assessor, dims)
    json.dump(res, open(args.out, "w", encoding="utf-8"), indent=2)
    print(json.dumps(res["summary"], indent=2))
