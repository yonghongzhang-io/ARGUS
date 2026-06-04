"""Evaluation metrics for the flaw-injection loop.

Given a clean audit and an injected audit (with the injected flaw's target
dimension as ground truth), compute:
  - detection_rate    : did the injected version raise risk on the flaw?
  - false_alarm_rate  : did the clean version stay quiet?
  - localization_acc  : was the *right* dimension flagged?
"""

from __future__ import annotations

from typing import Any

_RANK = {"low": 0, "medium": 1, "high": 2, "unknown": -1}


def _risk(audit: dict[str, Any], dim_id: str) -> int:
    return _RANK.get(audit["by_dimension"].get(dim_id, {}).get("risk", "unknown"), -1)


def evaluate_pair(
    clean_risk_map: dict[str, Any],
    injected_risk_map: dict[str, Any],
    target_dimension: str,
    *,
    threshold: str = "medium",
) -> dict[str, Any]:
    """Score one (clean, injected) pair against a single injected flaw."""
    if threshold not in _RANK:
        raise ValueError(f"unknown threshold: {threshold}")
    thr = _RANK[threshold]
    detected = _risk(injected_risk_map, target_dimension) >= thr
    clean_quiet = _risk(clean_risk_map, target_dimension) < thr

    # localization: top-ranked flagged dimension on the injected version
    ranked = injected_risk_map.get("ranked", [])
    flagged = [dim_id for dim_id in ranked if _risk(injected_risk_map, dim_id) >= thr]
    top = flagged[0] if flagged else None
    localized = top == target_dimension

    return {
        "target_dimension": target_dimension,
        "detected": detected,
        "false_alarm": not clean_quiet,
        "localized": localized,
    }


def summarize_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate pair-level booleans into evaluation rates."""
    if not results:
        raise ValueError("cannot summarize an empty result list")
    n = len(results)
    return {
        "n": n,
        "detection_rate": sum(bool(r["detected"]) for r in results) / n,
        "false_alarm_rate": sum(bool(r["false_alarm"]) for r in results) / n,
        "localization_acc": sum(bool(r["localized"]) for r in results) / n,
    }
