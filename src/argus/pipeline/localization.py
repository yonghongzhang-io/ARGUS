"""Stage 4 — localization (deterministic).

Aggregate per-dimension judgements into a risk map: which identification
dimensions carry the weakest support. No agency; pure aggregation.
"""

from __future__ import annotations

from typing import Any

_RANK = {"low": 0, "medium": 1, "high": 2}


def localize(assessed: dict[str, Any]) -> dict[str, Any]:
    judgements = assessed["judgements"]
    risk_map = {
        dim_id: {
            "risk": (j or {}).get("risk", "unknown"),
            "rationale": (j or {}).get("rationale"),
            "cited_evidence": (j or {}).get("cited_evidence", []),
            "retrieval_quality": (j or {}).get("retrieval_quality"),
            "evidence_status": (j or {}).get("evidence_status"),
        }
        for dim_id, j in judgements.items()
    }
    ranked = sorted(
        risk_map.items(),
        key=lambda kv: _RANK.get(kv[1]["risk"], -1),
        reverse=True,
    )
    return {"by_dimension": risk_map, "ranked": [k for k, _ in ranked]}
