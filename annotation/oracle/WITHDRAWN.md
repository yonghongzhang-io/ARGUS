# Withdrawn

The "oracle-evidence" experiment that used this folder (`experiments/ablations/oracle_evidence.py`,
reported in the version submitted to ClimateNLP 2026) is withdrawn from the paper.

Its input, `evidence_spans_completed.csv` (not tracked), was described as passages an expert
located in the five pilot papers. A check of the 103 entries against the PDFs found none of them
in the text: they are one-sentence paraphrases, not quotations, and how they were produced is not
documented. An experiment that feeds them to the judge therefore does not test what happens when
the judge is given the paper's own evidence, and its results (`oracle_evidence.json`) should not
be cited.

The protocol and the annotation page are kept because the design is sound; a valid run needs
verbatim passages collected under `annotation/human_pilot/PROTOCOL.md`.
