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
The dominant rule: a weak-retrieval `high` (no contradiction signalled in the
rationale) is either demoted to `medium` (`--weak-high-action medium`, keep
coverage) or set to `unknown` (`--weak-high-action unknown`, abstain). It fired on
20 cells. Smaller rules soften a few anachronistic-standard / inference-reporting-
gap / concurrent-policy-closure `high`s (1 each). Nothing is upgraded; a `high`
whose rationale signals the evidence *contradicts* the assumption is kept.

## Before vs after (vs adjudicated gold, 55 cells)

| metric | before | demote→medium | abstain→unknown |
|---|---:|---:|---:|
| over-severe (of answered) | 29 | 18 | 6 |
| high precision | 0.04 | 0.50 | 0.50 |
| high recall | 0.50 | 0.50 | 0.50 |
| exact agreement (answered) | 0.12 | 0.46 | 0.54 |
| weighted kappa (answered) | 0.06 | 0.13 | 0.25 |
| answered / unknown | 33 / 22 | 33 / 22 | 13 / 42 |

## Reading
Both policies cut over-severity and **preserve high-risk recall (0.50)** — severity
is reduced without losing detection. The keep-coverage (medium) policy keeps all
33 answers and lifts exact agreement 0.12→0.46; the abstain (unknown) policy
reaches the highest weighted kappa (0.25) but collapses coverage to 13 answered
cells. Neither fixes the root cause — weak retrieval — so the lift that adds
*correct* coverage must come from better evidence grounding. Central message:
**human gold is not only evaluative — it directly calibrates audit severity**.

Caveats: pilot scale (gold has 2 `high` cells, so high precision/recall are
noisy); the abstain-policy kappa is on 13 answered cells. The robust claims are
the one-directional over-severity drop and preserved recall.

Reproduce:
```
PYTHONPATH=src python3 experiments/annotation/run_gold_papers_rich.py   # needs OPENAI_API_KEY
PYTHONPATH=src python3 experiments/annotation/calibrate_argus.py --weak-high-action medium
PYTHONPATH=src python3 experiments/annotation/calibrate_argus.py --weak-high-action unknown
```
