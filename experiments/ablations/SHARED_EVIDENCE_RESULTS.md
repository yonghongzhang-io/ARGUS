# Shared-evidence control: results

Run 2026-09-20, `gpt-4o-2024-11-20`, temperature 0, one run; 990 adequacy calls, 0 errors.
Protocol and decision rule: `SHARED_EVIDENCE_PROTOCOL.md` (committed before any model call;
zero-call cells committed in 58c6605 before the paid stage). Per-item verdicts:
`shared_evidence.json`; frozen evidence with sha256 per bundle: `shared_evidence_bundles.json.gz`.

| cell | det (11) | fa (11) | loc (11) | det (33) | comm / omit (33) | fa (33) | loc (33) | off-target, injected (33) | clean dims flagged |
|---|---|---|---|---|---|---|---|---|---|
| K-kw  | 2/11  | 0/11 | 2/11  | 8/33  | 3/22, 5/11   | 0/33 | 8/33  | 0.000 | none |
| K-llm | 10/11 | 1/11 | 8/11  | 31/33 | 20/22, 11/11 | 3/33 | 22/33 | 0.152 | SUTVA |
| S-kw  | 1/11  | 0/11 | 1/11  | 2/33  | 0/22, 2/11   | 0/33 | 2/33  | 0.000 | none |
| S-llm | 11/11 | 0/11 | 11/11 | 31/33 | 20/22, 11/11 | 0/33 | 22/33 | 0.164 | none |
| gated two-stage (reference, gpt-4o alias) | 8/11 | 0/11 | 8/11 | 25/33 | 20/22, 5/11 | 3/33 | 0.66 (3-run mean) | n/a | inference |

K = the keyword pipeline's stage-2 chunks; S = the LLM path's four section candidates, ungated.
No gate in any of the four cells, so none can abstain. Off-target rate on the 11 flaws: 0.109 in
both LLM cells, 0.000 in both keyword cells.

## Paired contrasts (exact McNemar on the same items)

- Policy at fixed evidence K: detection 2 -> 10 of 11 (8 gained, 0 lost, p = 0.008);
  8 -> 31 of 33 (23 gained, 0 lost, p < 0.001). False alarms 0 -> 1 of 11 (p = 1.0), 0 -> 3 of 33 (p = 0.25).
- Policy at fixed evidence S: 1 -> 11 of 11 (p = 0.002); 2 -> 31 of 33 (p < 0.001). No false alarms.
- Evidence at fixed LLM judge: 10 vs 11 of 11; 31 vs 31 of 33. False alarms 1 -> 0 and 3 -> 0.
- Evidence at fixed keyword scorer: 2 vs 1 of 11; 8 vs 2 of 33 (p = 0.03): whole sections bleed
  topic vocabulary into the keyword scorer.

## Reading, by the pre-specified rule

**Policy explanation supported.** K-llm exceeds K-kw by 0.73 on the 11 flaws (rule: >= 0.30),
the 33-variant contrast points the same way, and K-llm's false-alarm and clean off-target rates
are 0.091 above K-kw's (rule: <= 0.10). The false-alarm criterion is met narrowly.

What this does and does not license:

- Licensed: "with evidence held identical, the adequacy judge detects 10 of 11 planted flaws
  against the keyword scorer's 2 (p = 0.008), and 31 against 8 of 33 variants."
- The gain is a trade. The judge rates 11-16% of non-target dimensions medium or higher on
  injected papers, the keyword scorer none; localization on the variants is 22/33.
- Every false alarm in the K-llm row is ONE verdict (SUTVA rated medium on the clean paper's
  keyword chunks), counted once per flaw targeting that dimension. Both benchmarks share a single
  clean fixture, so all false-alarm rates in this project rest on one clean audit of eleven
  dimensions, not on 11 or 33 independent trials.
- The ungated S-llm cell out-detects the gated pipeline (11/11 vs 8/11; omissions 11/11 vs 5/11).
  That is the trade the paper already describes: on a short fixture a judge shown four sections
  notices the deleted one, where the gate abstains. It also raises no false alarm, whereas the
  gated pipeline flags inference on the clean fixture: relative to ungated top-4 retrieval the
  gate narrows the evidence and does not reduce alarms here. The reference row used the gpt-4o
  alias, so this comparison is indicative only.
- Both LLM cells miss the same two commission variants
  (`parallel_trends_commission_01`, `robustness_placebo_commission_02`).
- n = 11 and n = 33; fixtures, sentinel lists and injector are co-designed. Directional evidence.

## Note on recorded commit ids

`shared_evidence.json` stores the commit the code was at when each stage ran
(`git.head` = `5f6e4ef...`, `git_llm_stage.head` = `bfd8fac...`). Commit messages in this
repository were later rewritten, which renames commits without changing any file. Those two
states are now `5d530a0` and `58c6605`; their file trees are unchanged and can be checked
with `git rev-parse <commit>^{tree}`:

- stage "zero" code state: tree `a6588c60b7706811977dd4be2f3bc9bdcfdfa7e1`
- stage "llm" code state:  tree `c800a2129cc79b2bc14d7deaf742745a5cb24dd4`

The recorded values are left as written at run time.
