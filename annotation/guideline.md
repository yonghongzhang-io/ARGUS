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

### Severity anchors (v0.1 draft — finalize in the calibration round)
The pilot found that **96% of A/B disagreements are one severity step**, and most
are the low↔medium boundary — i.e. `medium` was acting as a dustbin. Anchor it:

- **low** — a relevant check is reported *and* its result directly supports the
  assumption (e.g. an event study with flat, insignificant pre-trends shown).
- **medium** — *partial support with a substantive unresolved risk*: the check is
  reported but its result is incomplete/weak/not fully shown, OR a credible threat
  is acknowledged but only partly addressed. `medium` requires a *named* residual
  risk in the rationale — not "I'm unsure".
- **high** — the assumption is only vaguely mentioned or not addressed, no
  diagnostic evidence, OR the reported evidence itself signals a violation.

If two annotators land on adjacent levels and both can defend it, set
`ambiguity_flag=1` and record both readings — that is a finding, not an error.

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
