"""Batch-audit real DID papers from the CausalVerify corpus.

Filters the CausalVerify index for a method family (default DID), ingests each
paper's parsed Markdown, audits it with ARGUS, and aggregates the per-dimension
risk distribution. This is the small-scale external-validity check on real
published papers — no annotation required.

Usage:
    # keyword baseline (no key), first 15 DID papers:
    PYTHONPATH=src python3 experiments/real_papers/run_corpus.py --n 15
    # LLM assessor (needs OPENAI_API_KEY):
    PYTHONPATH=src python3 experiments/real_papers/run_corpus.py --n 15 --llm

Default corpus path assumes CAUSALVERIFY is a sibling of ARGUS under papers/.
Outputs a per-paper-per-dimension CSV to experiments/real_papers/corpus_results/.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from argus.config import load_dimensions  # noqa: E402
from argus.ingest import ingest_file  # noqa: E402
from argus.pipeline.audit import run_audit  # noqa: E402

DEFAULT_CORPUS = ROOT.parent / "CAUSALVERIFY" / "v11" / "pdfs-corpus"
OUT_DIR = Path(__file__).resolve().parent / "corpus_results"
_RISK_ORDER = ["high", "medium", "low", "unknown"]


def select_papers(corpus: Path, method: str, n: int) -> list[str]:
    index = corpus / "index.jsonl"
    ids: list[str] = []
    for line in index.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        if rec.get("method_family", "").upper() == method.upper():
            ids.append(rec["id"])
    return ids[:n] if n > 0 else ids


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus-dir", default=str(DEFAULT_CORPUS))
    ap.add_argument("--method", default="DID")
    ap.add_argument("--n", type=int, default=15, help="number of papers (0 = all)")
    ap.add_argument("--llm", action="store_true", help="LLM assessor (needs OPENAI_API_KEY)")
    ap.add_argument("--max-steps", type=int, default=1)
    args = ap.parse_args()

    corpus = Path(args.corpus_dir)
    md_dir = corpus / "converted" / "markdown"
    assessor = "llm" if args.llm else "keyword"
    dims = list(load_dimensions())

    paper_ids = select_papers(corpus, args.method, args.n)
    print(f"{args.method} papers selected: {len(paper_ids)} | assessor: {assessor}\n")

    # dimension -> Counter(risk)
    dist: dict[str, Counter] = defaultdict(Counter)
    rows: list[tuple[str, str, str]] = []
    audited = skipped = 0

    for pid in paper_ids:
        md = md_dir / f"{pid}.md"
        if not md.exists():
            print(f"  skip {pid}: no markdown")
            skipped += 1
            continue
        try:
            paper = ingest_file(md, paper_id=pid)
            if not paper.get("sections"):
                print(f"  skip {pid}: no sections parsed")
                skipped += 1
                continue
            result = run_audit(paper, max_steps=args.max_steps, assessor=assessor)
        except Exception as exc:  # keep the batch going; report at the end
            print(f"  skip {pid}: {type(exc).__name__}: {exc}")
            skipped += 1
            continue
        audited += 1
        for dim_id, d in result.risk_map["by_dimension"].items():
            risk = str(d["risk"])
            dist[dim_id][risk] += 1
            rows.append((pid, dim_id, risk))
        print(f"  audited {pid}")

    print(f"\naudited {audited}, skipped {skipped}\n")
    if not audited:
        print("nothing audited — check --corpus-dir / markdown path.")
        return

    # aggregate table
    print(f"per-dimension risk distribution over {audited} {args.method} papers ({assessor}):")
    print("{:28}{:>6}{:>8}{:>6}{:>9}".format("dimension", "high", "medium", "low", "unknown"))
    print("-" * 57)
    for dim_id in dims:
        c = dist[dim_id]
        print("{:28}{:>6}{:>8}{:>6}{:>9}".format(
            dim_id, c.get("high", 0), c.get("medium", 0), c.get("low", 0), c.get("unknown", 0)))
    totals = Counter()
    for c in dist.values():
        totals.update(c)
    print("-" * 48)
    print("totals:", {k: totals.get(k, 0) for k in _RISK_ORDER if totals.get(k, 0)})

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_csv = OUT_DIR / f"{args.method.lower()}_{assessor}_risks.csv"
    with open(out_csv, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["paper_id", "dimension", "risk"])
        w.writerows(rows)
    print(f"\nwrote {out_csv.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
