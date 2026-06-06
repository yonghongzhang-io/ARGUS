# ARGUS dimension-level identification-risk annotation protocol

**Version:** 0.1 · **Target:** calibrate ARGUS against expert judgement on real
DID papers. Built to reuse the CausalVerify
labeling apparatus (protocol, multiple annotators, $\kappa$ target, blind
relabel, ambiguity flag), but at a **finer granularity**: CausalVerify labels a
paper's *method family* and *conclusion direction*; here we label
**identification risk per assumption**.

## 1. Unit of annotation
One row = **(paper, identification dimension)**. Each paper contributes 11 rows,
one per rubric dimension (`config/identification_dimensions.yaml`).

## 2. What you judge (blind — do not look at ARGUS's output)
Read the paper for the named dimension and fill these fields. The two-level
`reported` / `adequacy` split is deliberate: it separates *reporting* a check
from the check being *adequate* — the construct-validity distinction ARGUS is
built around (reported-evidence adequacy is a proxy for identification validity).

| field | values | meaning |
|---|---|---|
| `reported` | yes / no / unclear | Does the paper report *any* evidence or check for this assumption? |
| `evidence_status` | sufficient / partial / missing / flawed | Quality of what is reported (missing = nothing; flawed = reported but the evidence itself signals a problem). |
| `risk` | low / medium / high | Overall identification risk for this dimension, given the reported evidence. |
| `ambiguity_flag` | 0 / 1 | Set 1 if this is a genuinely contested call experts could reasonably disagree on. **Explain in `rationale`.** Ambiguity is signal, not noise. |
| `confidence` | 1–5 | Your confidence in the `risk` label. |
| `evidence_location` | free text | Section / table / figure / page you relied on (or "none found"). |
| `rationale` | one sentence | Why — especially if `ambiguity_flag=1`. |

Mapping guide (not a rule): sufficient→low, partial→medium, missing/flawed→high.
Deviate when warranted and say why.

## 3. Process
1. Annotator A and Annotator B label the **same** papers **independently** (no
   discussion, no ARGUS output visible).
2. Compute agreement on `risk` (Cohen's $\kappa$) per dimension
   (`experiments/annotation/agreement.py`). Target $\kappa \ge 0.6$; report it
   honestly whatever it is — low agreement on a dimension is itself a finding
   (the dimension is intrinsically contested).
3. Adjudicate disagreements (a third reader, or discussion) into a gold label.
4. Only then compare ARGUS's `risk` against the gold, and check whether ARGUS's
   `unknown` lines up with human "could not assess / no evidence found".

## 4. Bootstrapping a task sheet
`experiments/annotation/build_tasks.py PAPER.md` emits a blind per-paper CSV
(11 rows, dimension prompts pre-filled, human columns blank). Fill it, save as
`data/annotations/<paper_id>_<annotator>.csv` (gitignored — not committed).

See `paper/contributions.md` and the construct-validity paragraph in the paper
(`paper/sections/discussion.tex`) for why this annotation layer is the central
next step.
