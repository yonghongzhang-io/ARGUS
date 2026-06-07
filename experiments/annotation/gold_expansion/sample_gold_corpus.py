#!/usr/bin/env python3
"""Stratified sampler for the ARGUS gold-expansion (AAAI evaluation push).

The pilot gold is 5 papers / 55 cells / 2 high cells -- too small to support
main-conference claims. This script draws a larger, design-balanced sample of
DID-family papers from the CausalVerify corpus index so the expanded expert gold
covers the design types a reviewer expects (staggered / continuous-shock /
event-study / environmental-policy) instead of one fixture.

What it does (deterministic, seed-fixed):
  * read CAUSALVERIFY/.../pdfs-corpus/index.jsonl
  * keep DID-family, well-formed, ok-extraction papers of sane length
  * ALWAYS include the 5 pilot papers as the seed (we expand, never discard gold)
  * stratify the remaining pool by (method_family x direction) and allocate the
    new slots proportionally, spreading length within each stratum
  * tag a heuristic design_type from the title (environmental / event_study / ...)
    -- a *hint* the annotation lead can correct in the manifest

Output: experiments/annotation/gold_expansion/sample_manifest.csv
  columns: paper_id, method_family, direction, year, venue, md_size_bytes,
           stratum, design_type_hint, design_type, include_reason
  (design_type is left blank for the lead to fill: staggered / continuous /
   environmental / non_standard / ... -- used later for applicability N/A.)

Usage:
    python3 experiments/annotation/gold_expansion/sample_gold_corpus.py \
        --total 25 --seed 20260607
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CORPUS = ROOT.parent / "CAUSALVERIFY" / "v11" / "pdfs-corpus"
OUT = Path(__file__).resolve().parent / "sample_manifest.csv"

# DID-family methods worth auditing with the DID identification rubric.
DID_FAMILY = {"DID", "EVENTSTUDY"}
# The pilot gold already annotated -- seed the expansion with these.
PILOT = ["paper_01", "paper_03", "paper_07", "paper_08", "paper_10"]
# Sane length window (bytes of converted markdown): drop truncated/garbage & giants.
MD_MIN, MD_MAX = 20_000, 600_000

ENVIRO_RE = re.compile(
    r"emission|carbon|pollut|\bETS\b|environment|climate|\benergy\b|green|"
    r"clean air|coal|renewable|CO2|greenhouse",
    re.I,
)


def design_type_hint(rec: dict) -> str:
    title = rec.get("title", "") or ""
    if ENVIRO_RE.search(title):
        return "environmental"
    if rec.get("method_family", "").upper() == "EVENTSTUDY":
        return "event_study"
    if re.search(r"stagger|rollout|roll-out|adoption|phase-?in", title, re.I):
        return "staggered"
    return "did_standard"


def load_pool(corpus: Path) -> dict[str, dict]:
    index = corpus / "index.jsonl"
    if not index.exists():
        raise SystemExit(f"corpus index not found: {index}\n"
                         "point --corpus-dir at CAUSALVERIFY/v11/pdfs-corpus")
    pool: dict[str, dict] = {}
    for line in index.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        pool[r["id"]] = r
    return pool


def eligible(rec: dict) -> bool:
    if rec.get("method_family", "").upper() not in DID_FAMILY:
        return False
    if str(rec.get("well_formed", "")).lower() not in ("true", "1"):
        return False
    if str(rec.get("extraction_status", "")).lower() not in ("ok", ""):
        return False
    try:
        size = int(rec.get("md_size_bytes", 0))
    except (TypeError, ValueError):
        size = 0
    return MD_MIN <= size <= MD_MAX


def spread_by_length(recs: list[dict], k: int) -> list[dict]:
    """Pick k records spread across the length distribution (diverse, not all short)."""
    if k <= 0 or not recs:
        return []
    s = sorted(recs, key=lambda r: int(r.get("md_size_bytes", 0)))
    if k >= len(s):
        return s
    # evenly spaced indices across the sorted-by-length list
    idx = [round(i * (len(s) - 1) / (k - 1)) for i in range(k)] if k > 1 else [len(s) // 2]
    seen, out = set(), []
    for i in idx:
        while i in seen and i < len(s) - 1:
            i += 1
        seen.add(i)
        out.append(s[i])
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus-dir", default=str(DEFAULT_CORPUS))
    ap.add_argument("--total", type=int, default=25,
                    help="target total papers including the 5 pilot (default 25)")
    ap.add_argument("--seed", type=int, default=20260607)
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()

    rng = random.Random(args.seed)
    pool = load_pool(Path(args.corpus_dir))

    elig = {pid: r for pid, r in pool.items() if eligible(r)}
    # never sample the pilot again from the pool; they are seeded separately
    new_pool = [r for pid, r in elig.items() if pid not in PILOT]

    n_new = max(0, args.total - len(PILOT))

    # stratify new_pool by (method_family, direction)
    strata: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in new_pool:
        key = (r.get("method_family", "?").upper(), (r.get("direction") or "?").lower())
        strata[key].append(r)

    total_pool = sum(len(v) for v in strata.values()) or 1
    # proportional allocation (largest-remainder), then length-spread within stratum
    raw = {k: n_new * len(v) / total_pool for k, v in strata.items()}
    alloc = {k: int(x) for k, x in raw.items()}
    remainder = n_new - sum(alloc.values())
    for k, _ in sorted(raw.items(), key=lambda kv: kv[1] - int(kv[1]), reverse=True)[:remainder]:
        alloc[k] += 1

    picked: list[dict] = []
    for key, recs in sorted(strata.items()):
        rng.shuffle(recs)               # seed-stable tiebreak within stratum
        picked.extend(spread_by_length(recs, alloc.get(key, 0)))

    # assemble rows: pilot seed first, then new picks
    rows = []
    for pid in PILOT:
        r = pool.get(pid, {"id": pid})
        rows.append((r, "pilot_seed"))
    for r in picked:
        rows.append((r, "expansion"))

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["paper_id", "method_family", "direction", "year", "venue",
                    "md_size_bytes", "stratum", "design_type_hint", "design_type",
                    "include_reason"])
        for r, reason in rows:
            mf = r.get("method_family", "")
            direction = r.get("direction", "")
            w.writerow([
                r.get("id", ""), mf, direction, r.get("year", ""),
                r.get("venue", ""), r.get("md_size_bytes", ""),
                f"{mf}|{direction}", design_type_hint(r), "",  # design_type blank
                reason,
            ])

    # report
    print(f"wrote {Path(args.out).relative_to(ROOT) if str(args.out).startswith(str(ROOT)) else args.out}")
    print(f"  eligible DID-family pool: {len(elig)}  (excluding pilot: {len(new_pool)})")
    print(f"  target total: {args.total}  = {len(PILOT)} pilot + {len(picked)} new "
          f"(requested {n_new})\n")
    print("  stratum (method|direction)      pool  picked")
    print("  " + "-" * 44)
    for key in sorted(strata):
        print(f"  {key[0]+'|'+key[1]:30}{len(strata[key]):>6}{alloc.get(key,0):>8}")
    hints = defaultdict(int)
    for r, _ in rows:
        hints[design_type_hint(r) if r.get("title") else "pilot(unknown)"] += 1
    print("\n  design_type_hint distribution:", dict(hints))
    print(f"\n  cells after annotation: {args.total} papers x 11 dims x 2 annotators "
          f"= {args.total*11*2}  ({args.total*11} adjudicated)")
    print("  NEXT: fill the blank `design_type` column, then run build_gold_batch.py")


if __name__ == "__main__":
    main()
