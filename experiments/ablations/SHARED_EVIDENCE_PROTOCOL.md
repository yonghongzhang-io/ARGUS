# Shared-evidence control: protocol (written before any run)

Status: **zero-call cells run and committed; LLM cells not yet run.** This file fixes the comparison before results exist. Any deviation
after the first model call is logged at the bottom, with the reason.

## Question

Table 1 compares a keyword pipeline (0.182 detection) with the two-stage LLM pipeline
(0.727). The two differ in the judgement policy **and** in the evidence they judge: the
keyword path scores paragraph chunks from `evidence_search` (<= 900 characters, top 5,
one query string); the LLM path re-retrieves whole sections with `retrieve_sections`
(<= 2,000 characters, top 4, 12-16 query terms) and then filters them through a
relevance gate. The paper therefore reports the gap as end to end.

This control asks: **with the evidence text held identical, how much of the gap remains
when only the judgement policy changes?** It can come out either way. The paper's
wording follows the result; the result does not get to follow the wording.

## Design: 2 x 2, evidence bundle x judgement policy, no gate anywhere

| | keyword scorer (`loop._assess_chain`) | LLM adequacy judge (`assess_chain_llm`) |
|---|---|---|
| **bundle K**: stage-2 chunks (`extraction.extract`) | K-kw = the existing baseline, 0 calls | **K-llm** (new) |
| **bundle S**: `retrieve_sections` candidates, all 4, ungated | **S-kw** (new, 0 calls) | **S-llm** (new) |

- Both policies already accept the same input contract, `{"items": [{"source", "text"}]}`.
  Within a column of evidence the two policies receive the **same list object**, serialized
  once to disk first (`shared_evidence_bundles.json`), so identity of the evidence text is
  checkable after the fact by hash, not asserted.
- **The relevance gate is off in all four cells.** Gating only the LLM arm would
  reintroduce a second difference. The gated two-stage pipeline is reported beside the grid
  as a reference row, not as part of the contrast.
- Policy effect at fixed evidence: K-llm vs K-kw, and S-llm vs S-kw.
  Evidence effect at fixed policy: S-llm vs K-llm, and S-kw vs K-kw.

## Items

1. The 11 clear flaws on `clean_supported` (12 papers: 1 clean + 11 injected).
2. The 33-variant benchmark with its clean counterparts.

Every paper is judged on **all 11 dimensions**, clean and injected alike, so localization
and off-target alarms can be scored. Cost: 11 adequacy calls per paper per LLM cell; about
264 calls for the 11-flaw set and roughly 750-800 for the 33 variants across the two LLM
cells (order of US$10 on gpt-4o in total; the 11-flaw set alone is about US$3).

## Fixed settings

- Model `gpt-4o-2024-11-20` (dated snapshot, not the alias), temperature 0, one run. The
  adequacy prompts and JSON schema are the ones printed in the paper's Appendix E, verbatim.
  No prompt, query pack, signal list, or threshold is edited once the first call is made.
- Code state: record `git rev-parse HEAD` in the output file; run from a clean tree.
- **Threshold**: detection and false alarm use risk >= medium, as everywhere in the paper
  (`metrics.evaluate_pair`, `threshold="medium"`).
- **Abstention**: with the gate off neither policy can return `unknown` (the judge schema
  is low/medium/high; the keyword scorer has no such state), so no abstention rule is
  needed. If a call fails after 3 retries the cell is recorded as `error`, counted as *not
  detected* and *not a false alarm*, and listed by id; more than 2 errors voids the run.
- **Empty bundle**: the keyword scorer natively returns `high` on an empty item list; the
  judge receives the literal `(no evidence was retrieved for this dimension)`. Both are
  kept as is and the number of empty-bundle cells is reported per arm, because on omission
  flaws this is where the two policies can differ for reasons other than reading ability.

## Outcomes (all reported for all four cells, plus the gated reference)

1. Detection rate on the target dimension (injected), overall and split commission / omission.
2. False-alarm rate on the target dimension (clean).
3. Localization accuracy as defined in `metrics.evaluate_pair` (top-ranked flagged dimension
   is the target).
4. **Off-target alarm rate**: share of the 10 non-target dimensions rated >= medium on the
   injected paper, and the same share on the clean paper. The current harness does not
   compute this; localization alone cannot show it, so it is added here.
5. Wilson 95% intervals for every rate; exact paired McNemar tests for the two policy
   contrasts and the two evidence contrasts on the same items.

## Reading the result (decided now)

- **Policy explanation supported**: K-llm detects at least 0.30 (absolute) more than K-kw on
  the 11 flaws, the 33-variant contrast points the same way, and K-llm's false-alarm and
  clean off-target rates are not more than 0.10 above K-kw's. Permitted wording: "with
  evidence held identical the adequacy judge detects X vs Y", with n and the paired p-value.
- **Evidence explanation**: K-llm is within 0.10 of K-kw while S-llm is high. Then the gap in
  Table 1 is mostly an evidence-granularity effect and the paper says so.
- **Mixed**: both contrasts are material. Report the decomposition; claim neither alone.
- In every case n = 11 and n = 33 stay too small for more than a directional statement, the
  fixtures and sentinel lists were co-designed with the injector, and a detection gain bought
  with a higher off-target alarm rate is reported as a trade, not a win.

## Outputs

`experiments/ablations/shared_evidence.py` (runner), `shared_evidence_bundles.json` (the
frozen evidence both policies saw, with sha256 per bundle), `shared_evidence.json` (per-item
verdicts for all cells and the summary). The zero-call cells (K-kw, S-kw) are run first and
committed before any model call, so the baseline cannot drift toward the LLM result.

## Deviations

Logged before any model call:

1. *Storage format.* The frozen bundles are written gzip-compressed
   (`shared_evidence_bundles.json.gz`), holding only the two fields either policy reads
   (`source`, `text`) plus a sha256 per bundle.
2. *Item count.* The 11 flaws and the 33 variants are injected into the same clean fixture, so
   there is one clean paper, not two: 45 papers x 11 dimensions = 495 adequacy calls per LLM
   cell, about 990 in total.
3. *Clean tree.* `src/`, `config/`, `examples/` and `experiments/` are clean at the recorded
   commit; the working tree also holds unrelated, uncommitted manuscript edits under `paper/`.
4. *Harness check (not a deviation).* K-kw reproduces the published keyword baseline exactly
   (2/11 detected, the same two omission flaws; 0 false alarms; localization 2/11).
