"""The fixed tool set the bounded loop is allowed to call.

Three tools, no more. Keeping the set small and fixed is part of what bounds the
agent's behaviour and keeps traces comparable across runs.
"""

from __future__ import annotations

from typing import Any


def evidence_search(paper: dict[str, Any], query: str, *, k: int = 5) -> list[dict[str, Any]]:
    """Retrieve up to k passages from the paper relevant to `query`."""
    raise NotImplementedError


def figure_parse(paper: dict[str, Any], figure_ref: str) -> dict[str, Any]:
    """Extract structured content from a figure/table (e.g. event-study plot)."""
    raise NotImplementedError


def policy_lookup(policy_name: str) -> dict[str, Any]:
    """Look up policy metadata (announcement vs. implementation dates, scope)."""
    raise NotImplementedError


DEFAULT_TOOLS = {
    "evidence_search": evidence_search,
    "figure_parse": figure_parse,
    "policy_lookup": policy_lookup,
}
