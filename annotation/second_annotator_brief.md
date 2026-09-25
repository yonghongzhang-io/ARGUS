> **SUPERSEDED (25 September 2026).** This document describes the June 2026 labels, which are replaced by the two-annotator gold of `annotation/human_pilot/PROTOCOL.md` and `experiments/annotation/gold_final/` (provenance note in `experiments/annotation/pilot_frozen/PROVENANCE.md`). Kept for the record.

# ARGUS pilot annotation brief

Thank you for helping with this pilot. The goal is to measure whether humans
can consistently judge identification-risk dimensions in real DID papers, and
then calibrate ARGUS against that human judgement.

## What to read

Please read the full PDF for each paper, not ARGUS output or parsed markdown:

| sheet | PDF |
|---|---|
| `paper_01_B.csv` | `../CAUSALVERIFY/v11/pdfs-corpus/raw/paper_01.pdf` |
| `paper_03_B.csv` | `../CAUSALVERIFY/v11/pdfs-corpus/raw/paper_03.pdf` |
| `paper_07_B.csv` | `../CAUSALVERIFY/v11/pdfs-corpus/raw/paper_07.pdf` |
| `paper_08_B.csv` | `../CAUSALVERIFY/v11/pdfs-corpus/raw/paper_08.pdf` |
| `paper_10_B.csv` | `../CAUSALVERIFY/v11/pdfs-corpus/raw/paper_10.pdf` |

The annotation sheets are in `data/annotations/`. Each sheet has 11 rows, one
per identification dimension. The assumption/implication columns are pre-filled;
please fill only the blank human columns.

## Rules

- Work independently. Do not discuss labels with Annotator A until all sheets
  are complete.
- Do not look at ARGUS reports, risk outputs, or LLM outputs.
- Use `annotation/guideline.md` as the label protocol.
- Read enough of the full PDF to judge each dimension; record the page/section,
  table, or figure you relied on in `evidence_location`.
- Set `ambiguity_flag=1` when reasonable experts could disagree, and explain why
  in `rationale`.

## Fields to fill

| field | allowed values |
|---|---|
| `reported` | `yes`, `no`, `unclear` |
| `evidence_status` | `sufficient`, `partial`, `missing`, `flawed` |
| `risk` | `low`, `medium`, `high` |
| `ambiguity_flag` | `0`, `1` |
| `confidence` | integer `1` to `5` |
| `evidence_location` | section/page/table/figure, or `none found` |
| `rationale` | one concise sentence |

Mapping guide, not a hard rule: `sufficient -> low`, `partial -> medium`,
`missing/flawed -> high`. Deviate when warranted and explain the deviation.

## After completion

Return the filled `*_B.csv` files. Agreement will be computed with:

```bash
PYTHONPATH=src python3 experiments/annotation/agreement.py --dir data/annotations
```

Low agreement is not a failure of the pilot; it identifies dimensions where
identification credibility is intrinsically contested.
