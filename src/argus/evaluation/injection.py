"""Inject exactly one known flaw into a credible DID paper.

Each flaw in config/flaw_taxonomy.yaml targets a single identification dimension,
so the injected version has local ground truth: ARGUS should flag that dimension
(and only that one) relative to the clean version.
"""

from __future__ import annotations

from typing import Any

from ..config import load_flaws


def inject_flaw(paper: dict[str, Any], flaw_id: str) -> dict[str, Any]:
    """Return an injected copy of `paper` plus its ground-truth label."""
    flaws = load_flaws()
    if flaw_id not in flaws:
        raise KeyError(f"unknown flaw: {flaw_id}")
    flaw = flaws[flaw_id]
    # The actual perturbation (editing event-study, removing a robustness check,
    # etc.) is per-flaw and not implemented yet.
    raise NotImplementedError(
        f"injection for '{flaw_id}' (target dimension: {flaw['target_dimension']}) "
        "not implemented yet"
    )
