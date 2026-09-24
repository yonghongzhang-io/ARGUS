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
- **Annotators.** Two people with graduate-level training in finance or economics and active
  research or teaching experience with empirical, regression-based studies (faculty,
  postdoctoral researchers or advanced doctoral students), able to read the five English-language
  articles in full, neither of them the first author and neither involved in
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
- 21 September 2026, before any workbook was returned: the qualification is stated as
  graduate-level training with active empirical research or teaching experience, not as a
  doctorate, so that an experienced faculty member without a PhD can take part. Each
  annotator's actual background is reported in the paper as it is.
- 24 September 2026, after both workbooks were returned and before anything was computed:
  annotator A returned the workbook with all 55 rows complete but the Sign-off sheet
  empty, and said they had no time to fill it in. The sign-off (name, date 24 September 2026,
  about 6 hours, and "yes" to the four confirmations) was given by the annotator to the first
  author on 24 September 2026 and recorded by the first author in
  `data/annotations/human_pilot/signoff_relayed_A.json`; the workbook itself is unchanged (SHA-256
  `294e7b34…`, receipt 13:20 CEST). `pilot.py` takes a relayed sign-off only when the workbook's
  own Sign-off sheet is entirely empty, and marks it as relayed in `RECEIPT.json`,
  `agreement.json` and `signoff.json`. The paper reports annotator A's confirmations as relayed,
  not signed. The first ingest attempt (13:20 CEST) was rejected for the empty sheet and is
  recorded in `RECEIPT.json`.
- 24 September 2026, receipt note on workbook B: the file whose receipt was recorded on
  23 September 2026 at 18:04 CEST (SHA-256 `ec694838…`) carries the document properties
  `lastModifiedBy = Yonghong Zhang`, application Microsoft Excel for Mac, last saved
  2026-09-23 12:35:54 UTC (14:35:54 CEST), and an identical copy named
  `Copy of annotatorB-v2-ARGUS_annotation_B.xlsx` with that modification time exists in the first author's
  Downloads folder. So the workbook on record was last saved from the first author's Excel three
  and a half hours before its receipt was recorded, and no earlier copy from the annotator has
  been found on the first author's machine. The first author is to state here how this came
  about (for example, whether the annotator filled the workbook on the first author's computer)
  and whether a copy as sent by the annotator exists elsewhere (e-mail or messaging attachment)
  so that its hash can be recorded and compared cell by cell. Workbook A carries
  `lastModifiedBy = the annotator's WPS user id` (WPS Office), last saved 2026-09-24 10:01 local time.
