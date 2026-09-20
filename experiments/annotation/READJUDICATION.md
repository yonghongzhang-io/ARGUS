# Re-adjudication of two pilot cells, and how the final gold is locked

## Why

The pilot gold (5 papers x 11 dimensions, adjudicated in June 2026) is frozen with checksums
in `pilot_frozen/`. In a later oracle-evidence pass, the annotator recorded that the
parallel-trends dimension does not apply to two of the five studies because they are not
treated-control DID designs:

| cell | adjudicated gold (June) | oracle-stage note |
|---|---|---|
| `paper_01` / `parallel_trends` | high (flagged ambiguous) | dimension not applicable to the design |
| `paper_08` / `parallel_trends` | medium (flagged ambiguous) | dimension not applicable to the design |

The annotation guideline covers such cells: flag them ambiguous, judge the design-specific
analogue of the assumption, default to *medium*, and use *high* only if that analogue is
itself weakly supported. The two passes may have answered different questions (does the
dimension apply, versus how risky is its analogue), so the basis of both labels is confirmed
by the original annotators. Nobody else decides these cells, and the frozen gold is never
edited.

## Procedure

1. Annotators A and B each answer, independently and per cell, from the paper alone:
   whether the dimension applies as conventionally defined; if not, what the design-specific
   analogue is and what the paper reports for it; and the label under the guideline.
   They do not see system outputs, each other's answers, or any agreement statistic.
2. If A and B differ, they discuss and record one decision per cell.
3. The decision goes into `readjudication.csv`, one row per cell: `decision` is `keep`
   (label stands), `relabel` (with `new_label`), or `exclude` (the dimension does not apply
   and the cell leaves the gold), plus `rationale`, `decided_by`, `date`.
4. Lock, once:

       python3 experiments/annotation/finalize_gold.py --check   # validates the two rows
       python3 experiments/annotation/finalize_gold.py           # writes gold_final/ + LOCK.json

   The script refuses incomplete rows and refuses to run a second time. After the lock the
   gold is not adjusted again.
5. Regenerate everything that reads the gold (no model access):

       PYTHONPATH=src python3 experiments/ablations/uncertainty.py
       PYTHONPATH=src python3 experiments/ablations/calibration_recheck.py
       python3 experiments/ablations/lopo_calibration.py
       python3 experiments/ablations/oracle_evidence_audit.py
       PYTHONPATH=src python3 experiments/make_camera_ready_figures.py
       PYTHONPATH=src python3 experiments/verify_paper_numbers.py

   `verify_paper_numbers.py` recomputes every number the paper reports and lists each claim
   whose value no longer matches the text. If both labels are kept, nothing changes. The
   paper is edited until the script exits 0, then rebuilt and tagged.

`goldpath.py` is the single place that decides which gold the scripts read: `gold_final/`
once it exists, otherwise `pilot_frozen/`.
