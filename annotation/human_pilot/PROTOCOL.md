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

Names of the annotators, their addresses and their names inside returned file names are
replaced by "annotator A" and "annotator B" in this log, in `RECEIPT.json` and in
`gold_final/LOCK.json`; the private, untracked `data/annotations/human_pilot/` keeps the
original files and names, and the annotators' identities are known to the authors. On
25 September 2026 both annotators agreed to be named in the paper's acknowledgments (as
reported by the first author); the records here stay anonymised.

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
- 24 September 2026, provenance of workbook B (facts established from the files; details and
  hashes in `RECEIPT.json` → `provenance_B`; the files are kept unchanged in
  `data/annotations/human_pilot/returned/provenance_B/`). The file whose receipt was recorded on
  23 September at 18:04 CEST (SHA-256 `ec694838…`, e-mailed by the annotator as
  `annotatorB-ARGUS_annotation_B.xlsx`) is **not** the annotator's own last version. The first
  author's WeChat file cache holds four versions, all of 23 September 2026 (CEST):
  (1) 12:57, `annotatorB-v1-ARGUS_annotation_B.xlsx`, last saved by annotator B: all 55 rows and the sign-off
  filled, but the `paper_07` sheet is an exact copy of her `paper_03` sheet (77 of 77 answer
  cells identical; nine of its eleven verbatim quotes occur in `paper_03.pdf`, none in
  `paper_07.pdf`), evidently a paste into the wrong sheet; (2) 13:13,
  `annotatorB-v2-ARGUS_annotation_B.xlsx`, last saved by annotator B: `paper_07` redone for the kit's NBER paper
  (all eleven quotes occur in `paper_07.pdf`; 45 cells of that sheet changed, including
  3 applicability and 5 risk labels); (3) 13:15, `Copy of annotatorB-v2-ARGUS_annotation_B.xlsx`, saved by
  the first author's Excel for Mac, no answer cell changed; (4) 14:35,
  `Copy of annotatorB-v2-ARGUS_annotation_B(1).xlsx`, saved by the first author's Excel: the eleven
  `paper_07` evidence-location cells replaced by the version-1 locations (which refer to
  `paper_03`'s article), and the `paper_07` specification rationale truncated by its last
  sentence; labels, quotes and confidences unchanged from (2). Version (4) was then sent to the
  annotator over WeChat and came back as the e-mail attachment recorded at 18:04 (identical
  bytes). Consequences: the annotator's work is version (2), and the receipt, the private labels,
  `agreement.json` and `reconcile.xlsx` are to be rebuilt from it (labels are identical between
  (2) and (4), so the agreement figures do not change; twelve non-label cells do). Version (1)
  stays on record as the annotator's first submission, and the paper reports that the annotator
  first returned `paper_07` filled with `paper_03`'s content and corrected it sixteen minutes
  later. First author's statement, 24 September 2026: nothing was said to the annotator
  between versions (1) and (2); she noticed the wrong paste herself and sent the corrected
  file. On version (4), the first author states that they only opened the workbook to check it
  and made no deliberate change; how the eleven location cells came to hold the version-1 text
  and the rationale lost its last sentence is not known. The first author therefore had
  workbook B open on 23 September, before workbook A was returned on 24 September. None of the
  twelve cells enters the analysis, since the record is rebuilt from version (2). The verbatim quotes of both
  annotators were checked against the kit PDFs: A, 50
  of 55 exact and 4 partial; B version (2), 49 exact, 4 partial, 1 empty; the one quote of each
  not found is the same cell (`paper_01`, inference).
- 24 September 2026, workbook A: the annotator's covering e-mail (Thu 24 Sept, 04:0x CEST) says
  the sign-off sheet was completed, but in the file the eight answer cells of that sheet exist
  and are empty (checked in the raw sheet XML). The workbook was last saved by WPS Office at
  10:01 on the annotator's local clock.
- 24 September 2026, 19:26 CEST, workbook A resolved: the annotator re-sent the workbook by
  e-mail with the Sign-off sheet completed in her own hand (annotator A; 24/09/2026; 5 hours;
  "yes" to all four confirmations), last saved by her WPS Office. All 385 answer cells are
  identical to the first return. This signed workbook (SHA-256 `2a21fba9…`) is the record of
  annotator A's work; the relayed sign-off of earlier today is superseded and kept as
  `signoff_relayed_A.superseded.json` (it had said 6 hours; the annotator's own figure is
  5). The first, unsigned return stays in `RECEIPT.json` as `A_unsigned_294e7b34`. Annotator
  A's confirmations are therefore signed, not relayed, and the paper reports them as such.
- 25 September 2026, 00:26 CEST, reconciliation returned: annotator B e-mailed the filled
  reconciliation on behalf of both ("[annotator A] and I have gone through the 13 differences together").
  Instead of the generated `reconcile` sheet they returned a table of their own layout (one
  sheet; paper, workbook row number, dimension name, FINAL applicability, FINAL risk, status,
  decided by, deciding note), saved by annotator B in WPS. `pilot.py gold` reads it by its
  header text and identifies each dimension by the workbook row number cross-checked against
  the dimension name; no other adaptation. All 13 rows are `agreed` and decided by "both annotators",
  each with a note; no row is unresolved, so no third person was needed. The first author took
  no part. The file's SHA-256 is in `RECEIPT.json` (`reconcile`) and in `gold_final/LOCK.json`.
- 25 September 2026, first author's statements on the labels of the submitted version (the
  June 2026 set in `pilot_frozen/`): first that they were produced by one person other than
  the first author working with AI assistance, then, about half an hour later, that they were
  produced by two people working with AI assistance who sent them together to the first
  author, who entered them. No record of those people's work, identity or sign-off exists on
  the first author's machine (a search was started and stopped at the first author's request
  for lack of time). The paper reports the two-person account as the first author's account,
  states that no annotation record exists, and does not treat those labels as an annotation.
