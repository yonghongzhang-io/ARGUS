# Gold expansion (AAAI evaluation push)

Scaffolding to grow the expert gold from the **pilot (5 papers / 55 cells / 2 high
cells)** to a **design-balanced ~25-paper set** so ARGUS-vs-gold can support a
main-conference claim. Reuses the pilot annotation flow
(`experiments/annotation/{build_tasks,agreement,adjudicate,compare_argus_gold,
calibrate_argus}.py`) unchanged; only sampling + batch generation + data-driven
adjudication are new.

## Scripts

| script | role |
|--------|------|
| `sample_gold_corpus.py` | stratified sample of DID-family papers from the CausalVerify `index.jsonl` (seeds the 5 pilot, expands to `--total`, strata = `method_family × direction`, length-spread, seed-fixed) → `sample_manifest.csv` |
| `build_gold_batch.py` | per paper × annotator: stage corpus markdown, emit blind `<pid>_{A,B}.csv` + human `packets/<pid>_{A,B}.md` |
| `adjudicate_v2.py` | data-driven adjudication (verdicts in a CSV, not hard-coded) → `gold_labels_expansion.csv` (same schema as the pilot `gold_labels.csv`) |
| `gold_balance_report.py` | risk-class balance (HIGH-cell count vs pilot's 2), per-dimension & per-stratum coverage; `--preview` uses ARGUS predictions as a sampling aid |

## Workflow

```bash
cd <ARGUS root>
PYTH=PYTHONPATH=src

# 1. sample (deterministic). Edit --total / --seed as needed.
python3 experiments/annotation/gold_expansion/sample_gold_corpus.py --total 25
#    -> sample_manifest.csv. Optionally fill the blank `design_type` column
#       (staggered / continuous / environmental / non_standard) -- it drives the
#       "n/a if the dimension doesn't apply" note in each packet.

# 1.5  AUDIT the sampled papers with ARGUS so a prediction exists for every gold
#      paper (needed for the vs-gold comparison). ~17/25 are not yet audited:
$PYTH python3 experiments/real_papers/run_corpus.py --llm --corpus-dir <corpus> ...
#      (extend run_corpus to take the manifest's paper ids, or run per id.)

# 2. build the blind batch (CSVs + human packets)
$PYTH python3 experiments/annotation/gold_expansion/build_gold_batch.py

# 3. hand packets/<pid>_A.md -> annotator A, _B.md -> annotator B (>=2 raters).
#    They paste filled blocks back; transcribe `risk` into the matching CSV.

# 4. inter-annotator agreement (reuses the pilot script, just point --dir here)
$PYTH python3 experiments/annotation/agreement.py --dir data/annotations/gold_expansion

# 5. adjudicate: emit disagreements, fill verdicts, build gold
python3 experiments/annotation/gold_expansion/adjudicate_v2.py --emit-disagreements
#    fill winner{A,B,both}+ambiguous in verdicts_template.csv -> save as verdicts.csv
python3 experiments/annotation/gold_expansion/adjudicate_v2.py

# 6. balance check (is the HIGH count finally adequate?)
python3 experiments/annotation/gold_expansion/gold_balance_report.py --with-pilot

# 7. ARGUS-vs-gold + calibration on the expanded set (reuse pilot scripts,
#    pointed at gold_labels_expansion.csv merged with the pilot gold).
```

## Two caveats baked into the current sample

1. **The CausalVerify corpus is finance-heavy** (JFE / JF / NEJM …). Only ~2
   sampled papers read as environmental by title. With the title now generalized
   to DID broadly this is fine, but do **not** re-narrow the framing to
   environmental policy — the gold won't support it. If an environmental subset is
   wanted, source those papers separately and add them to the manifest by hand.

2. **~17/25 sampled papers are not yet ARGUS-audited** (`--preview` shows which).
   Run step 1.5 before the vs-gold comparison, or the comparison only covers the
   8 overlapping papers.

## Notes
- `sample_manifest.csv` is committed (reproducible); the per-paper CSVs, staged
  `papers/`, and `packets/` live under `data/` and are gitignored (paper-derived
  text), matching the pilot.
- Targets: 25 papers × 11 dims × 2 annotators = **550 cells (275 adjudicated)**,
  ~5× the pilot. Aim for **≥15 high cells** so high precision/recall stabilize
  (`gold_balance_report.py` flags this).
