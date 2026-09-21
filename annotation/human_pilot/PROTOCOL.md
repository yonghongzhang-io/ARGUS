# Human annotation pilot: protocol and analysis plan

Status: **written and committed before any annotation was returned.** Deviations are logged at
the bottom with their reason.

## Why this exists

The labels that the submitted version of the paper compared ARGUS against
(`experiments/annotation/pilot_frozen/gold_labels.csv`) cannot be documented as the work of two
independent human annotators. The session record of 6 June 2026 shows both label sets being
pasted in as blocks of text by one person, minutes apart, within an hour of the annotation form
being created, some of it in the voice of a chat assistant; no trace of a second annotator
exists; and the later "evidence spans" are paraphrases, not quotations from the articles. The
description "two annotators independently labelled ... adjudicated expert gold" is therefore
not supported. This pilot replaces those labels with ones whose provenance is recorded.

## Design

- **Items.** The same five papers as before (`paper_01`, `paper_03`, `paper_07`, `paper_08`,
  `paper_10`; chosen in June 2026 before any label existed) by the eleven rubric dimensions:
  55 cells.
- **Annotators.** Two people with doctoral-level training in empirical finance or economics
  (faculty, postdoctoral researchers or advanced doctoral students who work with
  difference-in-differences designs), neither of them the first author and neither involved in
  building the system. They may be co-authors or external colleagues; which, and their relation
  to the authors, is reported in the paper. Each signs the workbook's sign-off sheet (name,
  dates, hours, and four confirmations).
- **Independence and blinding.** Each annotator reads the full PDFs alone, uses no AI tool to
  read, locate evidence, choose labels or write rationales, sees no ARGUS output for these
  papers, and does not discuss labels with the other annotator before both workbooks are
  returned. An annotator who is a co-author has seen the manuscript's aggregate results (for
  example that the system tends to be over-severe) but no cell-level system output and none of
  the earlier cell-level labels; this is disclosed in the paper as a limitation. An external
  annotator is told nothing about the system's results.
- **The first author** prepares the materials and runs the scripts. They have seen the system
  outputs and the earlier labels, so they label nothing and adjudicate nothing.
- **Instrument.** `GUIDELINE.md` and one workbook per annotator
  (`build_kit.py`). Per cell: applicability (conventional / analogue / not applicable),
  reported, evidence location, optional verbatim quote, risk (low / medium / high),
  confidence, rationale.
- **Receipt.** On return, each workbook's SHA-256 is recorded in
  `experiments/annotation/human_pilot/RECEIPT.json` before anything is computed from it.
- **Reconciliation.** Cells on which the two differ (applicability or risk) are listed with
  both labels and both rationales, and nothing else. The two annotators discuss them and record
  one final label per cell, or mark the cell *unresolved*; a third qualified person who has not
  seen system outputs decides unresolved cells. The first author takes no part.
- **Gold.** Agreed or reconciled risk per cell. A cell that ends as *not applicable* leaves
  the gold and is counted separately. The gold is locked once
  (`experiments/annotation/gold_final/LOCK.json`) and is not adjusted afterwards.

## What the system side is

The ARGUS outputs compared against the gold were produced in June and July 2026 and are frozen
with checksums (`experiments/annotation/pilot_frozen/argus_rich_gold5.csv`; corpus run
`experiments/real_papers/corpus_results/did_llm_risks.csv`). Nothing is re-run after labels
arrive. The calibration rules are those of `calibrate_argus_v1_pilot.py` (sha256 `e7c21bf3…`,
committed 20 September 2026). They were derived from an error analysis against the earlier
labels, so against the human gold they are a fixed, previously specified rule set; they are
not re-tuned.

## Analyses fixed now (all reported, whatever they show)

1. Inter-annotator agreement on the independent labels: applicability agreement; on cells both
   rated, exact agreement, Cohen's kappa, quadratic-weighted kappa, share of disagreements one
   step apart.
2. Gold distribution; number of cells not applicable; number reconciled, unresolved,
   tie-broken.
3. ARGUS vs gold: abstentions; among answered cells, exact / more severe / less severe; Cohen
   and weighted kappa (coverage and strict policies); high precision and recall.
4. Abstentions: of the cells ARGUS abstained on, how many the annotators marked
   *reported = yes* with a location (both, either, neither). This separates "retrieval failed"
   from "the paper does not report it" without any further model call.
5. Calibration, primary: rule 1 alone (weak-retrieval high to medium, or to unknown): exact
   agreement, over-severe cells, cells fixed / broken, exact McNemar, per-paper sign test.
   Exploratory: rules 1 to 4.
6. Uncertainty: cell bootstrap for agreement with the caveat that cells are nested in five
   papers; leave-one-paper-out recurrence of the over-severity pattern.
7. Side by side with the earlier LLM-assisted labels: how many cells change, and how each
   headline number moves. Both sets stay in the repository, each described as what it is.

The oracle-evidence experiment of the submitted version is withdrawn: its "spans" are not
quotations. It returns only if both annotators supply verbatim quotes for every rated cell.

## Deviations

- 21 September 2026, before any workbook was returned: the annotators need not be co-authors.
  The first version of this protocol required two co-authors; availability before the
  camera-ready deadline is uncertain, so qualified external annotators are also admitted. The
  instrument, the blinding rules and the analysis plan are unchanged.
