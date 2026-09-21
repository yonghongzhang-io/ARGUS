# Provenance of the labels in this folder

`gold_labels.csv` and the calibrated outputs scored against it reproduce the numbers of the
version submitted to ClimateNLP 2026. They are kept for that purpose only.

These labels cannot be documented as independent human annotations. The session record of
6 June 2026 shows both label sets ("A" and "B") being pasted in as blocks of text by one person,
minutes apart and within an hour of the annotation form being created, some of it in the voice of
a chat assistant. No trace of a second annotator exists. The 27 "adjudicated" disagreements were
encoded about eighty minutes later. Treat the file as **LLM-assisted reference labels compiled by
the first author**, not as an expert gold.

The human annotation that replaces it is specified in `annotation/human_pilot/PROTOCOL.md`; once
collected and locked it lives in `experiments/annotation/gold_final/`, and every analysis script
reads that instead (`goldpath.py`).
