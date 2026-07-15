# ARGUS gold-expansion annotation brief (round 2)

This extends the pilot to 10 more papers with a **two-stage** label per
dimension. The pilot showed that much "expert disagreement" was really
disagreement about whether a dimension *applies* to a non-standard design;
round 2 separates that question from severity.

## What to read

Read the full PDF for each paper (not ARGUS output, not parsed markdown):

| paper_id | PDF |
|---|---|
| paper_120 | `../CAUSALVERIFY/v11/pdfs-corpus/raw/paper_120.pdf` |
| paper_126 | `../CAUSALVERIFY/v11/pdfs-corpus/raw/paper_126.pdf` |
| paper_145 | `../CAUSALVERIFY/v11/pdfs-corpus/raw/paper_145.pdf` |
| paper_164 | `../CAUSALVERIFY/v11/pdfs-corpus/raw/paper_164.pdf` |
| paper_165 | `../CAUSALVERIFY/v11/pdfs-corpus/raw/paper_165.pdf` |
| paper_14  | `../CAUSALVERIFY/v11/pdfs-corpus/raw/paper_14.pdf` |
| paper_100 | `../CAUSALVERIFY/v11/pdfs-corpus/raw/paper_100.pdf` |
| paper_113 | `../CAUSALVERIFY/v11/pdfs-corpus/raw/paper_113.pdf` |
| paper_124 | `../CAUSALVERIFY/v11/pdfs-corpus/raw/paper_124.pdf` |
| paper_130 | `../CAUSALVERIFY/v11/pdfs-corpus/raw/paper_130.pdf` |

The sheet is `gold_expansion_template.csv` (110 rows; assumption columns
pre-filled). Fill only the blank columns.

## Stage A: applicability (fill first, for every row)

`applicability` — does this identification dimension meaningfully apply to
this paper's research design?

- `applicable` — the assumption is part of this design's identification
  argument (the usual case).
- `not_applicable` — the dimension does not arise for this design. Examples:
  *staggered-timing handling* for a single-date, two-group DID; *no
  anticipation* when treatment assignment is retroactive; dimensions defined
  for discrete adoption when the paper uses a continuous exposure measure and
  the analogous check appears under another dimension.
- `unclear` — reasonable experts could disagree about whether it applies
  (say why in `notes`).

If `not_applicable` or `unclear`: **leave `evidence_risk` blank** and move on.

## Stage B: evidence risk (only when applicable)

`evidence_risk` — given the evidence the paper actually reports, how much
identification risk remains on this dimension?

- `low` — reported evidence adequately supports the assumption.
- `medium` — partial or indirect support; gaps a referee would probe.
- `high` — evidence is absent, seriously incomplete, or reveals a flaw.

Judge **reported evidence**, not your prior about the true effect and not the
paper's reputation.

## Evidence span (both stages)

- `evidence_span`: paste verbatim the 1--4 sentences (or table/figure caption
  plus the key line) your judgement rests on. If the paper reports nothing for
  an applicable dimension, write `NONE REPORTED`.
- `evidence_location`: `text` / `table` / `figure` / `footnote` / `appendix` /
  `none` (optionally add the section, e.g. `text: Section 5.2`).
- `confidence`: `high` / `low`.

## Rules (unchanged from the pilot)

- Work independently; do not discuss labels with the other annotator until all
  sheets are complete.
- Do not look at ARGUS reports, risk outputs, or any LLM output.
- Disagreements go to one adjudication round afterwards; the adjudicator
  records the reason for each resolution in `notes`.
