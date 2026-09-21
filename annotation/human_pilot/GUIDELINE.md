# Annotation guideline: identification risk in five DID-style papers

You will read five published empirical papers and, for each of eleven identification
dimensions, judge how well the paper's **reported evidence** supports the assumption. You are
not asked whether the paper's conclusion is true.

Time: about one hour per paper. Please work alone.

## Ground rules

1. **Read the PDF yourself.** Do not use ChatGPT, Claude, Copilot or any other AI tool to read
   the paper, find passages, choose labels or write rationales. Searching inside the PDF with
   Ctrl/Cmd-F is fine.
2. **Work independently.** Do not discuss these papers or your labels with the other annotator
   until both workbooks have been returned.
3. **Do not look at any output of the ARGUS system** for these papers, and do not try to guess
   what it said. There is no "expected" answer.
4. Judge what the paper **reports**. If a check may have been run but is not reported, it
   counts as not reported.
5. Short rationales in your own words are enough: one or two sentences.

## What to fill in for each dimension

| column | values | meaning |
|---|---|---|
| **applicability** | conventional / analogue / not applicable | Does this assumption have a counterpart in the paper's design? *conventional*: it applies as usually defined for DID. *analogue*: the design is not a canonical treated-versus-control DID (continuous exposure, event study, shift-share, cross-sectional shock), but an equivalent assumption must hold; judge that analogue. *not applicable*: there is no counterpart at all; leave risk empty and say why. |
| **reported** | yes / no / unclear | Does the paper report any evidence or check that bears on this assumption (or its analogue)? |
| **evidence location** | free text | Section, table, figure or page you relied on; "none found" if none. |
| **verbatim quote** (optional) | pasted text | One to three sentences copied exactly from the PDF that you relied on most. Leave empty if nothing fits. |
| **risk** | low / medium / high | Identification risk on this dimension given the reported evidence (definitions below). Empty only when not applicable. |
| **confidence** | 1 to 5 | How sure you are of the risk label (5 = very sure). |
| **rationale** | one or two sentences | Why this label. If you chose *analogue*, name the analogue. If you think experts could reasonably disagree, say so. |

## Risk levels

- **low**: a relevant check is reported and its result directly supports the assumption (for
  example an event study with flat, insignificant pre-period coefficients that are shown).
- **medium**: partial support with a named, unresolved risk. The check is reported but
  incomplete, weak or not fully shown, or a credible threat is acknowledged and only partly
  addressed. *Medium* needs a specific residual risk in the rationale; it is not a way of
  saying "unsure" (use the confidence column for that).
- **high**: the assumption is barely mentioned or not addressed and no diagnostic evidence is
  given, or the reported evidence itself points to a violation.

## Conventions for common borderline cases

These were fixed before annotation began, so that both annotators draw the same lines.

- A design that is not a canonical DID does not make a dimension high by itself. Judge the
  analogue: *high* only if the analogue is itself weakly supported or contradicted, *low* if it
  is well supported.
- Concurrent policies discussed and partly, but not fully, isolated: medium.
- Surprise or event logic without a formal test of leads: medium. An explicit test of leads
  with insignificant coefficients: low is defensible.
- A defined sample window with some robustness checks but no endpoint sensitivity: medium.
- Well-defined exposure with unresolved network or spatial interference: medium, unless the
  interference plainly breaks the design (then high).
- No heterogeneity-robust staggered-DID estimator in a paper written before such estimators
  existed: medium, not high.
- Transparent measurement with acknowledged limitations: low, unless a limitation threatens
  identification (then medium).
- Inference: clustering at the level at which treatment varies, with enough clusters: low. A
  clearly wrong clustering level: up to high.

## The eleven dimensions

The workbook lists, for each dimension, the assumption and the kind of evidence a credible
paper would report. They are the same for every paper.

## When you are done

Fill in the *Sign-off* sheet (name, dates, approximate hours, four confirmations) and return
the workbook to the person who sent it. Thank you.
