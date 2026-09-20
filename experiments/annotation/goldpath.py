"""Which adjudicated gold the analysis scripts read.

`pilot_frozen/gold_labels.csv` is the June-2026 adjudicated gold, checksummed and never edited.
`gold_final/gold_labels.csv` exists only after `finalize_gold.py` has locked the outcome of the
two-cell re-adjudication; once it exists every script reads it instead.
"""
from __future__ import annotations

from pathlib import Path

_ANN = Path(__file__).resolve().parent
FROZEN_GOLD = _ANN / "pilot_frozen" / "gold_labels.csv"
FINAL_GOLD = _ANN / "gold_final" / "gold_labels.csv"


def gold_path() -> Path:
    return FINAL_GOLD if FINAL_GOLD.exists() else FROZEN_GOLD
