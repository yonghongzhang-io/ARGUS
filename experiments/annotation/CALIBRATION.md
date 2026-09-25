> **SUPERSEDED (25 September 2026).** This document describes the June 2026 labels, which are replaced by the two-annotator gold of `annotation/human_pilot/PROTOCOL.md` and `experiments/annotation/gold_final/` (provenance note in `experiments/annotation/pilot_frozen/PROVENANCE.md`). Kept for the record.

# Calibration layer — from diagnosis to improvement (aggregate)

Closes the loop: human gold -> ARGUS-vs-gold diagnosis -> error analysis ->
deterministic calibration -> re-measure. Aggregate only; raw labels gitignored.

## Diagnosis (over-severity error analysis)
On the 5 gold papers ARGUS is over-severe in 29/33 answered cells and never
under-severe. Of its over-severe `high` cells, **23/24 are
`evidence_status=missing`** and **20/24 are `retrieval_quality=weak`** — ARGUS
treats "weak retrieval found nothing" as a substantive `high`, conflating
*retrieval failure* with *the paper lacking the evidence*.

## Calibration rules (deterministic, ARGUS-visible fields only)
The table below is produced by **version 1** of the layer, `calibrate_argus_v1_pilot.py`
(recovered from the authoring session log; see the provenance block at the top of that
file). The committed `calibrate_argus.py` is a later two-rule rewrite and does **not**
reproduce these numbers.

Version 1 has four rules, applied to `high` cells only, first match wins:

1. *Dominant rule.* `retrieval_quality == weak` -> `medium` (`--weak-high-action medium`,
   keep coverage) or `unknown` (`--weak-high-action unknown`, abstain). Fires on 20 cells.
2. `dimension == treatment_timing` and the rationale names a modern DID estimator
   (Callaway, Sun-Abraham, Goodman-Bacon, "modern estimator(s)") -> `medium`. 1 cell.
3. `dimension == inference`, `evidence_status == missing`, and the rationale mentions
   "cluster" or "robust standard errors" -> `medium`. 1 cell.
4. `dimension == concurrent_policies` and `retrieval_quality == good` -> `medium`. 1 cell.

Nothing is upgraded. Version 1 has no contradiction guard (that belongs to the rewrite).
Rules 2-4 are crude string/field tests written minutes after the over-severity analysis
of this same pilot; each fires on one cell, and rule 4 has no content condition at all
(finding relevant evidence is not the same as the evidence supporting the assumption).
They are recorded as historical exploratory rules, not as a validated method.

## Before vs after (vs adjudicated gold, 55 cells)

| metric | before | demote→medium | abstain→unknown |
|---|---:|---:|---:|
| over-severe (of answered) | 29 | 18 | 6 |
| high precision | 0.04 | 0.50 | 0.50 |
| high recall | 0.50 | 0.50 | 0.50 |
| exact agreement (answered) | 0.12 | 0.45 | 0.54 |
| weighted kappa (answered) | 0.06 | 0.13 | 0.25 |
| answered / unknown | 33 / 22 | 33 / 22 | 13 / 42 |

## Reading
Both policies cut over-severity and **preserve high-risk recall (0.50)** — severity
is reduced without losing detection. The keep-coverage (medium) policy keeps all
33 answers and lifts exact agreement 0.12→0.45; the abstain (unknown) policy
reaches the highest weighted kappa (0.25) but collapses coverage to 13 answered
cells. Neither fixes the root cause — weak retrieval — so the lift that adds
*correct* coverage must come from better evidence grounding. Central message:
**human gold is not only evaluative — it directly calibrates audit severity**.

Caveats: pilot scale (gold has 2 `high` cells, so high precision/recall are
noisy); the abstain-policy kappa is on 13 answered cells. The robust claims are
the one-directional over-severity drop and preserved recall.

## Dominant rule alone vs all four rules
`experiments/ablations/calibration_recheck.py` re-runs version 1 on the frozen inputs in
`pilot_frozen/` (55/55 cells identical to the historical outputs under both policies) and
separates the dominant rule from rules 2-4 (demote-to-medium policy, 33 answered cells):

| rule set | exact agreement | over-severe | high precision | weighted kappa |
|---|---:|---:|---:|---:|
| before | 4/33 = 0.12 | 29 | 1/25 | 0.06 |
| dominant rule only | 12/33 = 0.36 | 21 | 1/5 | 0.21 |
| all four rules | 15/33 = 0.45 | 18 | 1/2 | 0.13 |

Paired on the same 33 cells the dominant rule fixes 8 cells and breaks none (exact McNemar
p = 0.008); four rules fix 11 (p = 0.001). By paper the lift appears in 4 of 5 papers with
one tie (sign test, ties dropped, p = 0.125) and in 5 of 5 (p = 0.0625). Cells are nested
in papers and every rule was written on this pilot, so these are in-sample results with a
consistent direction, not evidence of held-out generalization. Under the abstain policy the
dominant rule fixes no cell (it only removes 20 answers: 4/13 = 0.31 exact); the 0.54 in the
table above comes from the lost coverage plus the three cells rules 2-4 fix.

Reproduce:
```
PYTHONPATH=src python3 experiments/annotation/run_gold_papers_rich.py   # needs OPENAI_API_KEY
python3 experiments/annotation/calibrate_argus_v1_pilot.py --weak-high-action medium \
    --input experiments/annotation/pilot_frozen/argus_rich_gold5.csv --out /tmp/cal_medium.csv
python3 experiments/ablations/calibration_recheck.py                     # no model access
```
