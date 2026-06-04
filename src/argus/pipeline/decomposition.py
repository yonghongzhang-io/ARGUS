"""Stage 1 — decomposition (deterministic).

Map the paper onto the ~10 identification dimensions from the rubric. No model
agency here: this just instantiates the dimension skeleton the later stages fill.
"""

from __future__ import annotations

from typing import Any

from ..config import load_dimensions


def decompose(paper: dict[str, Any]) -> dict[str, Any]:
    dimensions = load_dimensions()
    return {
        "paper_id": paper.get("id", "unknown"),
        "dimensions": {
            dim_id: {
                "id": dim_id,
                "name": d["name"],
                "assumption": d["assumption"],
                "implication": d["implication"],
                "expected_evidence": d["evidence"],
            }
            for dim_id, d in dimensions.items()
        },
    }
