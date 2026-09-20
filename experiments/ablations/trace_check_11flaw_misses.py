"""Were the two-stage pipeline's three 11-flaw misses abstentions? (no model access)

`twostage_11flaw_fresh.json` (2026-07-15) records only detected / localized per flaw. The
paper says the three misses are omission flaws on which the gate fails and the pipeline
answers `unknown`. This script checks that against the per-dimension traces the pipeline
wrote during that run (`results/traces/`, local and gitignored): a trace is attributed to an
injected paper when its retrieval candidates equal the candidates `retrieve_sections` returns
for that paper on the flaw's target dimension (retrieval is deterministic and lexical).

    PYTHONPATH=src python3 experiments/ablations/trace_check_11flaw_misses.py

Writes `twostage_11flaw_misses.json`. Without the local traces it only re-reads that file.
"""
from __future__ import annotations

import datetime as dt
import glob
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from argus.agent.retrieval import retrieve_sections  # noqa: E402
from argus.config import load_dimensions  # noqa: E402
from argus.evaluation.injection import _INJECTIONS, inject_flaw  # noqa: E402

ABL = ROOT / "experiments" / "ablations"
TRACES = ROOT / "results" / "traces"
OUT = ABL / "twostage_11flaw_misses.json"
# The run file was written 2026-07-15 19:47:30 local time; its traces start at 19:04:48.
WINDOW = (dt.datetime(2026, 7, 15, 19, 4, 0), dt.datetime(2026, 7, 15, 19, 47, 31))
DAY = (dt.datetime(2026, 7, 15, 0, 0, 0), dt.datetime(2026, 7, 16, 2, 0, 0))


def _key(items: list[dict]) -> set[tuple[str, str]]:
    return {(i.get("source"), i.get("text")) for i in items}


def main() -> None:
    run = json.loads((ABL / "twostage_11flaw_fresh.json").read_text())
    missed = [r["flaw"] for r in run["per_flaw"] if not r["detected"]]
    if not TRACES.is_dir():
        print("no local traces; committed summary:")
        print(OUT.read_text())
        return
    dims = load_dimensions()
    dims = dims if isinstance(dims, dict) else {d["id"]: d for d in dims}
    clean = json.loads((ROOT / "examples" / "papers" / "clean_supported.json").read_text())
    rows = []
    for flaw in missed:
        injected = inject_flaw(clean, flaw)
        injected = injected[0] if isinstance(injected, tuple) else injected
        from argus.config import load_flaws
        target = load_flaws()[flaw]["target_dimension"]
        want = _key(retrieve_sections(injected, dims[target]))
        in_window, same_day_failed, same_day_answered = [], 0, []
        for path in glob.glob(str(TRACES / f"assess_llm_{target}-*.json")):
            mtime = dt.datetime.fromtimestamp(os.path.getmtime(path))
            if not DAY[0] <= mtime <= DAY[1]:
                continue
            trace = json.loads(Path(path).read_text())
            if "candidates" in trace and _key(trace["candidates"]) == want:
                same_day_failed += 1
                if WINDOW[0] <= mtime <= WINDOW[1]:
                    in_window.append({"time": mtime.strftime("%H:%M:%S"),
                                      "risk": trace["judgement"]["risk"],
                                      "retrieval_quality": trace["retrieval_quality"]})
            elif "relevant_items" in trace:
                kept = _key(trace["relevant_items"])
                if kept <= want and not kept <= _key(retrieve_sections(clean, dims[target])):
                    same_day_answered.append(trace["judgement"]["risk"])
        rows.append({
            "flaw": flaw, "op": _INJECTIONS[flaw]["op"], "target_dimension": target,
            "traces_in_run_window": in_window,
            "same_day_failed_gate_traces": same_day_failed,
            "same_day_answered_traces_on_this_paper": sorted(same_day_answered),
        })
    ok = all(r["op"] == "remove" and r["traces_in_run_window"]
             and all(t["risk"] == "unknown" for t in r["traces_in_run_window"])
             and all(x in ("medium", "high") for x in r["same_day_answered_traces_on_this_paper"])
             for r in rows)
    out = {
        "source": "results/traces (local, gitignored); run window 2026-07-15 19:04-19:47 local time",
        "reading": ("A miss is a target-dimension verdict below medium, i.e. low or unknown. Every "
                    "trace in the run window on a missed flaw's target dimension is a failed gate "
                    "scored unknown, and no trace that day gives such a paper a low verdict (the "
                    "answered ones are medium or high, which would have counted as detected)."),
        "missed_flaws": rows,
        "all_three_misses_are_omission_abstentions": ok,
    }
    OUT.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
