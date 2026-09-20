"""Shared-evidence control (see SHARED_EVIDENCE_PROTOCOL.md, fixed before any run).

2 x 2: evidence bundle (K = stage-2 keyword chunks, S = ungated section candidates)
x judgement policy (keyword scorer, LLM adequacy judge). Within a bundle both
policies read the SAME frozen item list; the relevance gate is off in every cell.

    # zero-call cells first (K-kw, S-kw) -- freezes the bundles, no model access
    PYTHONPATH=src python3 experiments/ablations/shared_evidence.py --stage zero
    # then the two LLM cells (PAID: ~990 adequacy calls, gpt-4o-2024-11-20)
    PYTHONPATH=src python3 experiments/ablations/shared_evidence.py --stage llm \
        --i-understand-this-costs-money
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from argus.agent.llm_assessor import assess_chain_llm, make_client  # noqa: E402
from argus.agent.loop import _assess_chain  # noqa: E402
from argus.agent.retrieval import retrieve_sections  # noqa: E402
from argus.config import load_flaw_variants, load_flaws  # noqa: E402
from argus.evaluation.injection import _INJECTIONS, inject_flaw  # noqa: E402
from argus.evaluation.metrics import evaluate_pair  # noqa: E402
from argus.evaluation.variants import inject_variant  # noqa: E402
from argus.pipeline import extraction  # noqa: E402
from argus.pipeline.decomposition import decompose  # noqa: E402
from argus.pipeline.localization import localize  # noqa: E402
from uncertainty import mcnemar_exact, wilson  # noqa: E402

ABL = Path(__file__).resolve().parent
PAPER = ROOT / "examples" / "papers" / "clean_supported.json"
BUNDLES = ABL / "shared_evidence_bundles.json.gz"
OUT = ABL / "shared_evidence.json"
CHECKPOINT = ROOT / "results" / "shared_evidence_calls.jsonl"  # gitignored; resumable
MODEL = "gpt-4o-2024-11-20"
CELLS = ("K-kw", "S-kw", "K-llm", "S-llm")
FLAGGED = {"medium", "high"}


def build_papers() -> dict[str, dict]:
    """clean + 11 injected flaws + 33 injected variants, keyed by paper id."""
    clean = json.loads(PAPER.read_text(encoding="utf-8"))
    papers = {"clean": {"paper": clean, "set": None, "target": None, "flaw_type": None}}
    for fid, flaw in sorted(load_flaws().items()):
        ftype = "omission" if _INJECTIONS[fid]["op"] == "remove" else "commission"
        papers[f"flaw:{fid}"] = {"paper": inject_flaw(clean, fid), "set": "11flaws",
                                 "target": flaw["target_dimension"], "flaw_type": ftype}
    for vid, var in sorted(load_flaw_variants().items()):
        papers[f"variant:{vid}"] = {"paper": inject_variant(clean, var), "set": "33variants",
                                    "target": var["target_dimension"], "flaw_type": var["flaw_type"]}
    return papers


def slim(items: list[dict]) -> list[dict]:
    """The only fields either policy reads."""
    return [{"source": it.get("source", "unknown"), "text": it.get("text", "")} for it in items]


def freeze_bundles(papers: dict[str, dict]) -> dict:
    frozen: dict = {}
    for pid, rec in papers.items():
        skeleton = decompose(rec["paper"])
        k_ev = extraction.extract(rec["paper"], skeleton, max_steps=1)["evidence"]
        frozen[pid] = {}
        for dim_id, dim in skeleton["dimensions"].items():
            for name, items in (("K", slim(k_ev[dim_id].get("items") or [])),
                                ("S", slim(retrieve_sections(rec["paper"], dim)))):
                blob = json.dumps(items, sort_keys=True, ensure_ascii=False).encode("utf-8")
                frozen[pid].setdefault(dim_id, {})[name] = {
                    "sha256": hashlib.sha256(blob).hexdigest(), "items": items}
    with gzip.open(BUNDLES, "wt", encoding="utf-8") as fh:
        json.dump(frozen, fh, ensure_ascii=False)
    return frozen


def load_bundles() -> dict:
    with gzip.open(BUNDLES, "rt", encoding="utf-8") as fh:
        return json.load(fh)


def dims() -> dict:
    return decompose(json.loads(PAPER.read_text(encoding="utf-8")))["dimensions"]


def run_keyword(frozen: dict, bundle: str) -> dict:
    dimensions = dims()
    return {pid: {d: _assess_chain(f"assess_chain:{d}", {"dimension": dimensions[d],
                                                          "evidence": {"items": by_dim[d][bundle]["items"]}})
                  for d in dimensions} for pid, by_dim in frozen.items()}


def run_llm(frozen: dict, bundle: str, client) -> dict:
    dimensions = dims()
    cell = f"{bundle}-llm"
    done: dict[tuple, dict] = {}
    if CHECKPOINT.exists():
        for line in CHECKPOINT.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            if r["cell"] == cell and r["model"] == MODEL and r["judgement"].get("risk") != "error":
                done[(r["paper_id"], r["dimension"], r["bundle_sha256"])] = r["judgement"]
    CHECKPOINT.parent.mkdir(parents=True, exist_ok=True)
    lock = threading.Lock()
    todo = [(pid, d) for pid in frozen for d in dimensions
            if (pid, d, frozen[pid][d][bundle]["sha256"]) not in done]
    print(f"[{cell}] {len(done)} cached, {len(todo)} calls to make", flush=True)

    def call(job: tuple[str, str]) -> None:
        pid, d = job
        b = frozen[pid][d][bundle]
        judgement = {"risk": "error", "rationale": ""}
        for attempt in range(3):
            try:
                judgement = dict(assess_chain_llm(dimensions[d], {"items": b["items"]},
                                                  client=client, model=MODEL)["judgement"])
                break
            except Exception as exc:  # noqa: BLE001 - recorded, then retried
                judgement = {"risk": "error", "rationale": f"{type(exc).__name__}: {exc}"[:300]}
                time.sleep(2 * (attempt + 1))
        with lock:
            done[(pid, d, b["sha256"])] = judgement
            with CHECKPOINT.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps({"cell": cell, "model": MODEL, "paper_id": pid, "dimension": d,
                                     "bundle_sha256": b["sha256"], "judgement": judgement},
                                    ensure_ascii=False) + "\n")

    with ThreadPoolExecutor(max_workers=6) as pool:
        for i, _ in enumerate(pool.map(call, todo), 1):
            if i % 50 == 0:
                print(f"  [{cell}] {i}/{len(todo)}", flush=True)
    return {pid: {d: done[(pid, d, frozen[pid][d][bundle]["sha256"])] for d in dimensions} for pid in frozen}


def rate(k: int, n: int) -> dict:
    lo, hi = wilson(k, n)
    return {"k": k, "n": n, "rate": round(k / n, 3), "ci95": [round(lo, 3), round(hi, 3)]}


def score_cell(judgements: dict, papers: dict, frozen: dict, bundle: str) -> dict:
    maps = {pid: localize({"judgements": j}) for pid, j in judgements.items()}
    clean = maps["clean"]
    out: dict = {"errors": sorted(f"{pid}|{d}" for pid, j in judgements.items()
                                  for d, v in j.items() if v.get("risk") == "error"),
                 "clean_dimensions_flagged": sorted(d for d, v in clean["by_dimension"].items() if v["risk"] in FLAGGED)}
    for set_name in ("11flaws", "33variants"):
        items = []
        for pid, rec in papers.items():
            if rec["set"] != set_name:
                continue
            target = rec["target"]
            s = evaluate_pair(clean, maps[pid], target, threshold="medium")
            others = [d for d in maps[pid]["by_dimension"] if d != target]
            items.append({"id": pid, "target_dimension": target, "flaw_type": rec["flaw_type"], **s,
                          "target_risk_injected": maps[pid]["by_dimension"][target]["risk"],
                          "target_risk_clean": clean["by_dimension"][target]["risk"],
                          "target_bundle_empty": not frozen[pid][target][bundle]["items"],
                          "offtarget_flagged_injected": sum(maps[pid]["by_dimension"][d]["risk"] in FLAGGED for d in others),
                          "offtarget_flagged_clean": sum(clean["by_dimension"][d]["risk"] in FLAGGED for d in others)})
        n = len(items)
        by_type = {t: [i for i in items if i["flaw_type"] == t] for t in ("commission", "omission")}
        out[set_name] = {
            "detection": rate(sum(i["detected"] for i in items), n),
            "detection_commission": rate(sum(i["detected"] for i in by_type["commission"]), len(by_type["commission"])),
            "detection_omission": rate(sum(i["detected"] for i in by_type["omission"]), len(by_type["omission"])),
            "false_alarm": rate(sum(i["false_alarm"] for i in items), n),
            "localization": rate(sum(i["localized"] for i in items), n),
            "offtarget_alarm_injected": rate(sum(i["offtarget_flagged_injected"] for i in items), 10 * n),
            "offtarget_alarm_clean": rate(sum(i["offtarget_flagged_clean"] for i in items), 10 * n),
            "empty_target_bundles": sum(i["target_bundle_empty"] for i in items),
            "items": items}
    return out


def contrasts(cells: dict) -> list[dict]:
    rows = []
    pairs = [("policy @ K", "K-kw", "K-llm"), ("policy @ S", "S-kw", "S-llm"),
             ("evidence @ llm", "K-llm", "S-llm"), ("evidence @ kw", "K-kw", "S-kw")]
    for label, a, b in pairs:
        if a not in cells or b not in cells:
            continue
        for set_name in ("11flaws", "33variants"):
            for key in ("detected", "false_alarm"):
                xa = {i["id"]: i[key] for i in cells[a][set_name]["items"]}
                xb = {i["id"]: i[key] for i in cells[b][set_name]["items"]}
                only_a = sum(1 for k in xa if xa[k] and not xb[k])
                only_b = sum(1 for k in xa if xb[k] and not xa[k])
                rows.append({"contrast": label, "a": a, "b": b, "set": set_name, "outcome": key,
                             "rate_a": round(sum(xa.values()) / len(xa), 3), "rate_b": round(sum(xb.values()) / len(xb), 3),
                             "discordant_a_only_b_only": [only_a, only_b],
                             "mcnemar_exact_p": round(mcnemar_exact(only_a, only_b), 4)})
    return rows


def git_state() -> dict:
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain", "--", "src", "config", "examples", "experiments"],
                           cwd=ROOT, capture_output=True, text=True).stdout.strip().splitlines()
    return {"head": head, "dirty_code_paths": dirty}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stage", choices=["zero", "llm"], required=True)
    ap.add_argument("--i-understand-this-costs-money", action="store_true")
    args = ap.parse_args()
    papers = build_papers()

    if args.stage == "zero":
        frozen = freeze_bundles(papers)
        result = {"protocol": "SHARED_EVIDENCE_PROTOCOL.md", "stage": "zero-call cells only",
                  "git": git_state(), "n_papers": len(papers), "cells": {}}
        for bundle in ("K", "S"):
            result["cells"][f"{bundle}-kw"] = score_cell(run_keyword(frozen, bundle), papers, frozen, bundle)
    else:
        if not args.i_understand_this_costs_money:
            print("Paid run (~990 gpt-4o calls); re-run with --i-understand-this-costs-money", file=sys.stderr)
            return 2
        frozen = load_bundles()
        result = json.loads(OUT.read_text(encoding="utf-8"))
        result.update({"stage": "all four cells", "model": MODEL, "temperature": 0, "git_llm_stage": git_state()})
        client = make_client()
        for bundle in ("K", "S"):
            result["cells"][f"{bundle}-llm"] = score_cell(run_llm(frozen, bundle, client), papers, frozen, bundle)

    result["contrasts"] = contrasts(result["cells"])
    OUT.write_text(json.dumps(result, indent=1, ensure_ascii=False), encoding="utf-8")
    for cell in CELLS:
        if cell not in result["cells"]:
            continue
        for set_name in ("11flaws", "33variants"):
            c = result["cells"][cell][set_name]
            print(f"{cell:6s} {set_name:10s} det {c['detection']['k']:2d}/{c['detection']['n']} "
                  f"(comm {c['detection_commission']['k']}/{c['detection_commission']['n']}, "
                  f"omit {c['detection_omission']['k']}/{c['detection_omission']['n']})  "
                  f"fa {c['false_alarm']['k']}/{c['false_alarm']['n']}  loc {c['localization']['k']}/{c['localization']['n']}  "
                  f"off-target inj {c['offtarget_alarm_injected']['rate']:.3f} clean {c['offtarget_alarm_clean']['rate']:.3f}  "
                  f"empty-target {c['empty_target_bundles']}  errors {len(result['cells'][cell]['errors'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
