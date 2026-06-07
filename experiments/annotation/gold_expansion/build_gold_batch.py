#!/usr/bin/env python3
"""Generate the blind annotation batch for every paper in the gold-expansion sample.

Reads sample_manifest.csv (from sample_gold_corpus.py), and for each paper:
  * stages the corpus markdown to data/annotations/gold_expansion/papers/<pid>.md
  * writes a blind per-dimension CSV per annotator:
        data/annotations/gold_expansion/<pid>_A.csv  (and _B.csv)
    -- same schema as experiments/annotation/build_tasks.py, so the existing
       agreement.py / adjudicate_v2.py read them unchanged
  * writes a human-facing packet the annotator fills and pastes back:
        data/annotations/gold_expansion/packets/<pid>_A.md  (and _B.md)

ARGUS's own judgement is deliberately NOT included, to avoid anchoring the
annotator (annotation/guideline.md). Run after filling design_type in the
manifest (optional) -- design_type is carried into the packet header so the
annotator knows when a dimension may be N/A for a non-standard design.

Usage:
    PYTHONPATH=src python3 experiments/annotation/gold_expansion/build_gold_batch.py \
        [--annotators A B] [--manifest sample_manifest.csv]
"""
from __future__ import annotations

import argparse
import csv
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from argus.config import load_dimensions  # noqa: E402

DEFAULT_CORPUS_MD = ROOT.parent / "CAUSALVERIFY" / "v11" / "pdfs-corpus" / "converted" / "markdown"
HERE = Path(__file__).resolve().parent
OUT = ROOT / "data" / "annotations" / "gold_expansion"
HUMAN_COLS = ["reported", "evidence_status", "risk", "ambiguity_flag",
              "confidence", "evidence_location", "rationale"]

PACKET_HEADER = """\
# ARGUS annotation packet: {pid} / annotator {ann}

Paper staged at: `{paper_rel}`  (design hint: {design})
Read the full paper. Do NOT consult ARGUS output. Fill every block below.

Allowed values:
- reported: yes / no / unclear
- evidence_status: sufficient / partial / missing / flawed
- risk: low / medium / high          (use n/a only if the dimension does not
        apply to this design -- e.g. staggered timing in a single-shock DID)
- ambiguity_flag: 0 / 1
- confidence: 1 / 2 / 3 / 4 / 5

Paste the completed text back exactly in this block format; I will write it into the CSV.
"""

PACKET_BLOCK = """
## {n}. {dim}

Assumption: {assumption}

Implication: {implication}

Expected evidence: {evidence}

reported:
evidence_status:
risk:
ambiguity_flag:
confidence:
evidence_location:
rationale:
"""


def write_csv(path: Path, pid: str, dims: dict, annotator: str) -> None:
    header = ["paper_id", "dimension", "assumption", "implication",
              "expected_evidence", *HUMAN_COLS, "annotator_id"]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        for dim_id, d in dims.items():
            w.writerow([
                pid, dim_id, d["assumption"].strip(), d["implication"].strip(),
                "; ".join(d.get("evidence", [])),
                "", "", "", "", "", "", "", annotator,
            ])


def write_packet(path: Path, pid: str, dims: dict, annotator: str,
                 paper_rel: str, design: str) -> None:
    parts = [PACKET_HEADER.format(pid=pid, ann=annotator, paper_rel=paper_rel,
                                  design=design or "unspecified")]
    for i, (dim_id, d) in enumerate(dims.items(), 1):
        parts.append(PACKET_BLOCK.format(
            n=i, dim=dim_id, assumption=d["assumption"].strip(),
            implication=d["implication"].strip(),
            evidence="; ".join(d.get("evidence", [])),
        ))
    path.write_text("".join(parts), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default=str(HERE / "sample_manifest.csv"))
    ap.add_argument("--corpus-md", default=str(DEFAULT_CORPUS_MD))
    ap.add_argument("--annotators", nargs="+", default=["A", "B"])
    args = ap.parse_args()

    manifest = Path(args.manifest)
    if not manifest.exists():
        raise SystemExit(f"manifest not found: {manifest}\nrun sample_gold_corpus.py first")
    corpus_md = Path(args.corpus_md)

    dims = load_dimensions()
    papers_dir = OUT / "papers"
    packets_dir = OUT / "packets"
    papers_dir.mkdir(parents=True, exist_ok=True)
    packets_dir.mkdir(parents=True, exist_ok=True)

    rows = list(csv.DictReader(open(manifest, encoding="utf-8")))
    built, missing = 0, []
    for r in rows:
        pid = r["paper_id"]
        src = corpus_md / f"{pid}.md"
        if not src.exists():
            missing.append(pid)
            continue
        staged = papers_dir / f"{pid}.md"
        shutil.copyfile(src, staged)
        paper_rel = staged.relative_to(ROOT).as_posix()
        design = (r.get("design_type") or r.get("design_type_hint") or "").strip()
        for ann in args.annotators:
            write_csv(OUT / f"{pid}_{ann}.csv", pid, dims, ann)
            write_packet(packets_dir / f"{pid}_{ann}.md", pid, dims, ann, paper_rel, design)
        built += 1

    print(f"built blind batch for {built} papers x {len(args.annotators)} annotators "
          f"({built*len(dims)*len(args.annotators)} cells)")
    print(f"  CSVs + papers : {OUT.relative_to(ROOT)}/")
    print(f"  packets       : {(packets_dir).relative_to(ROOT)}/")
    if missing:
        print(f"  WARNING: {len(missing)} papers had no markdown in {corpus_md}:")
        print("   ", ", ".join(missing))
    print("\nNEXT: hand packets/<pid>_A.md to annotator A, _B.md to annotator B;")
    print("      paste filled blocks back into the matching CSV `risk` column;")
    print("      then: agreement.py --dir data/annotations/gold_expansion")


if __name__ == "__main__":
    main()
