"""Patch 2 — LLM relevance gate.

Before judging adequacy, decide whether each retrieved section is actually
evidence *for this dimension*. This stops the assessor from treating an
off-target passage (an abortion-rate table retrieved for parallel trends) as
weak/absent evidence and over-flagging the dimension. The gate does ONE simple
job per item — relevant? high / partial / none — not a risk judgement.

Output also yields a `retrieval_quality` so the system can say "I could not find
relevant evidence" (retrieval failed) instead of "the paper has no evidence"
(a substantive high-risk claim). See assessment.py for how this becomes a
`risk: unknown` rather than `risk: high`.
"""

from __future__ import annotations

import json
from typing import Any, Optional

from .llm_assessor import make_client

_SYSTEM = (
    "You are screening retrieved passages for a difference-in-differences (DID) "
    "identification audit. For ONE identification dimension, decide whether each "
    "passage is actually evidence about THAT dimension's assumption. This is a "
    "relevance check, NOT a quality or risk judgement. Mark a passage 'high' if it "
    "directly concerns the assumption (e.g. an event-study / pre-trend discussion "
    "for parallel trends), 'partial' if it touches it indirectly, and 'none' if it "
    "is about something else. Be strict: a passage that merely shares vocabulary "
    "but is about a different topic is 'none'."
)

_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "index": {"type": "integer"},
                    "relevance": {"type": "string", "enum": ["high", "partial", "none"]},
                    "reason": {"type": "string"},
                },
                "required": ["index", "relevance", "reason"],
            },
        }
    },
    "required": ["items"],
}


def filter_relevant(
    dimension: dict[str, Any],
    candidates: list[dict[str, Any]],
    *,
    client: Optional[Any] = None,
    model: Optional[str] = None,
) -> dict[str, Any]:
    """Keep only candidates the model judges relevant. Returns {retrieval_quality, items}."""
    if not candidates:
        return {"retrieval_quality": "failed", "items": []}

    client = make_client(client)
    import os

    model = model or os.environ.get("ARGUS_LLM_MODEL", "gpt-4o")

    listing = "\n\n".join(
        f"[{i}] ({c.get('source', '?')}) {str(c.get('text', '')).strip()[:1200]}"
        for i, c in enumerate(candidates)
    )
    user = (
        f"Identification dimension: {dimension.get('name', dimension.get('id'))}\n"
        f"Assumption: {dimension.get('assumption', '')}\n"
        f"Testable implication: {dimension.get('implication', '')}\n\n"
        f"Candidate passages:\n{listing}\n\n"
        f"Classify each passage's relevance to this dimension."
    )
    from .llm_assessor import create_structured

    resp = create_structured(
        client,
        model=model,
        temperature=0,
        messages=[{"role": "system", "content": _SYSTEM}, {"role": "user", "content": user}],
        response_format={
            "type": "json_schema",
            "json_schema": {"name": "relevance", "strict": True, "schema": _SCHEMA},
        },
    )
    verdicts = {v["index"]: v for v in json.loads(resp.choices[0].message.content or "{}").get("items", [])}

    kept: list[dict[str, Any]] = []
    any_high = any_partial = False
    for i, c in enumerate(candidates):
        v = verdicts.get(i, {})
        rel = v.get("relevance", "none")
        if rel == "high":
            any_high = True
        elif rel == "partial":
            any_partial = True
        if rel in ("high", "partial"):
            kept.append({**c, "relevance": rel, "relevance_reason": v.get("reason", "")})

    quality = "good" if any_high else ("weak" if any_partial else "failed")
    return {"retrieval_quality": quality, "items": kept}
