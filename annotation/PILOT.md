# Second-annotator pilot (5 papers)

Goal: the first **inter-annotator agreement** on dimension-level identification
risk, and the first material to **calibrate ARGUS against humans**. Read
`guideline.md` before starting.

> **The second annotator must be a qualified human** (econ-literate, understands
> DID identification). It cannot be an LLM — the point is human ground truth to
> calibrate an LLM system.

## Papers (read the full PDF, not the parsed markdown)
PDFs: `../CAUSALVERIFY/v11/pdfs-corpus/raw/<id>.pdf`

| id | title | year |
|---|---|---|
| paper_01 | The Effect of the Banking Panic on the Supply of Credit… | 2010 |
| paper_03 | The Effects of State-Level Banking Competition on Innovation | 2015 |
| paper_07 | Do Credit Market Shocks Affect the Real Economy? | 2014 |
| paper_08 | Cyclicality of Credit Supply: Firm-Level Evidence | 2011 |
| paper_10 | Does Stock Liquidity Enhance or Impede Firm Innovation? | 2014 |

Reading the **full** paper (not the markdown ARGUS saw) is deliberate: it lets us
tell whether ARGUS's `unknown` means the paper truly lacks the evidence vs. ARGUS's
retrieval missed it.

## Blank sheets (already generated, gitignored)
`data/annotations/<id>_A.csv` and `<id>_B.csv` — 11 rows each (one per dimension),
assumption/implication pre-filled, human columns blank.
Regenerate: `PYTHONPATH=src python3 experiments/annotation/build_tasks.py <pdf-or-md> --annotator A`

## Workflow
1. **Annotator A** (you) fill every `*_A.csv`; **Annotator B** (the second human)
   fill every `*_B.csv` — **independently**, no discussion, no looking at ARGUS
   output. Open the CSVs in Excel/Numbers. Fields + label guidance: `guideline.md`.
2. Agreement:
   ```bash
   PYTHONPATH=src python3 experiments/annotation/agreement.py --dir data/annotations
   ```
   → percent agreement + Cohen's kappa overall and per dimension, plus the
   disagreement list. Report kappa honestly; low kappa on a dimension is a finding.
3. Adjudicate disagreements into a gold label (third reader or discussion).
4. **ARGUS vs human** (after gold exists): compare the gold risk against ARGUS's
   `experiments/real_papers/corpus_results/did_llm_risks.csv` (overlap on the 5
   papers) with the same script.

## What this yields for the paper
- inter-annotator kappa (does the construct hold for humans?),
- a characterization of which dimensions are intrinsically contested (`ambiguity_flag`),
- the first ARGUS-vs-expert calibration — turning the §5.1 distribution from
  "behaviour" into "accuracy against experts".
