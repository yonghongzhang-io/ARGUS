"""Multi-variant flaw injection: several naturalistic flaw variants per
identification dimension, driven by ``config/flaw_variants.yaml``.

This generalizes the single-recipe injector in :mod:`argus.evaluation.injection`.
Where ``injection.py`` hardcodes one recipe per flaw (11 total, ~one per
dimension), a *variant* is a YAML-declared perturbation, so each dimension can
carry several flaw variants that differ in flawed prose, section position, and
severity. That turns the ~1-per-dimension synthetic benchmark into a larger,
robustness-oriented one without touching the original 11-flaw pipeline the paper
reports.

Each variant declares:
  - ``target_dimension`` : the dimension it should make ARGUS flag
  - ``flaw_type``        : ``commission`` (replace a section with flawed-but-
                           natural prose) or ``omission`` (remove the supporting
                           evidence)
  - ``severity``         : low | medium | high
  - ``injection``        : the structural edit (``op`` + section/figure/table
                           targets and, for commission, the replacement text)
  - ``expected``         : ``{clean_risk_max, injected_risk_min}`` bounds the
                           audit should satisfy on the target dimension
  - ``forbidden_leakage_terms`` : phrases that must NOT appear post-injection

**Non-circularity is enforced statically, with no API calls.** The injected text
may contain neither the variant's own ``forbidden_leakage_terms`` nor the keyword
detector's per-dimension negative-signal phrases (:data:`argus.agent.loop._NEGATIVE_SIGNALS`).
:func:`validate_variant` checks this and ``tests/test_flaw_variants.py`` runs it
over every variant, so a variant that would make detection circular fails CI
before any model is ever called.

The keyword assessor path (:func:`evaluate_variants` with ``assessor="keyword"``)
is fully deterministic and needs no API, so the whole harness can be exercised
offline. Real per-variant *detection* numbers for the LLM assessor require a
separately authorized model run and are not produced here.
"""

from __future__ import annotations

import copy
from typing import Any, Optional

from ..agent.loop import _NEGATIVE_SIGNALS
from ..pipeline.audit import run_audit
from .injection import (
    _remove_refs,
    _remove_sections,
    _replace_figure_captions,
    _replace_sections,
)
from .metrics import _RANK, evaluate_pair, summarize_results

_FLAW_TYPE_TO_OP = {"commission": "replace", "omission": "remove"}


def _all_text(paper: dict[str, Any]) -> str:
    """Lowercased concatenation of every searchable string in a paper.

    Mirrors what the assessors read (sections, figure captions, table text), so a
    leak check over this string sees exactly what the detector could see.
    """
    parts: list[str] = []
    sections = paper.get("sections")
    if isinstance(sections, dict):
        parts.extend(str(v) for v in sections.values())
    elif isinstance(sections, list):
        for s in sections:
            if isinstance(s, dict):
                parts.extend(str(s.get(k, "")) for k in ("text", "content", "body"))
    for coll in ("figures", "tables"):
        items = paper.get(coll)
        if isinstance(items, list):
            for it in items:
                if isinstance(it, dict):
                    parts.extend(str(it.get(k, "")) for k in ("caption", "text", "title"))
        elif isinstance(items, dict):
            parts.extend(str(v) for v in items.values())
    return "\n".join(parts).lower()


def _op_of(variant: dict[str, Any]) -> str:
    injection = variant.get("injection", {})
    return injection.get("op") or _FLAW_TYPE_TO_OP.get(variant.get("flaw_type", ""), "")


def inject_variant(paper: dict[str, Any], variant: dict[str, Any]) -> dict[str, Any]:
    """Return an injected copy of ``paper`` for one flaw *variant* plus ground truth.

    Mirrors :func:`argus.evaluation.injection.inject_flaw` but is driven by the
    variant's declared ``injection`` block rather than the static recipe table.
    The original ``paper`` is never mutated (deep copy).
    """
    injection = variant["injection"]
    op = _op_of(variant)
    injected = copy.deepcopy(paper)
    injected["id"] = f"{paper.get('id', 'unknown')}__{variant['variant_id']}"

    if op == "remove":
        _remove_sections(injected, injection.get("sections", []))
        _remove_refs(injected, "figures", injection.get("figures", []))
        _remove_refs(injected, "tables", injection.get("tables", []))
    elif op == "replace":
        _replace_sections(injected, injection.get("sections", {}))
        _replace_figure_captions(injected, injection.get("figure_captions", {}))
    else:  # pragma: no cover - guarded by config validation
        raise ValueError(f"unknown injection op: {op!r} for variant {variant['variant_id']}")

    injected["argus_ground_truth"] = {
        "flaw_id": variant["variant_id"],
        "variant_id": variant["variant_id"],
        "target_dimension": variant["target_dimension"],
        "severity": variant["severity"],
        "flaw_type": variant.get("flaw_type"),
        "injection_op": op,
        "expected": variant.get("expected", {}),
    }
    return injected


def validate_variant(paper: dict[str, Any], variant: dict[str, Any]) -> list[str]:
    """Static, no-API non-circularity check for one variant.

    Returns the list of leaked phrases (empty == clean). A variant *leaks* if,
    after injection, the paper text contains either the keyword detector's
    negative-signal phrases for the target dimension or the variant's own
    declared ``forbidden_leakage_terms`` -- either of which would let the baseline
    "detect" the flaw by matching a string the injector itself planted.
    """
    injected = inject_variant(paper, variant)
    text = _all_text(injected)
    target = variant["target_dimension"]
    forbidden = list(_NEGATIVE_SIGNALS.get(target, [])) + list(variant.get("forbidden_leakage_terms", []))
    return [phrase for phrase in forbidden if phrase.lower() in text]


def _meets_expected(clean_risk: str, injected_risk: str, expected: dict[str, Any]) -> bool:
    """Whether the audit satisfies the variant's declared risk bounds."""
    lo = _RANK.get(expected.get("clean_risk_max", "high"), 2)
    hi = _RANK.get(expected.get("injected_risk_min", "low"), 0)
    clean_ok = _RANK.get(clean_risk, -1) <= lo
    injected_ok = _RANK.get(injected_risk, -1) >= hi
    return clean_ok and injected_ok


def evaluate_variants(
    clean_paper: dict[str, Any],
    variant_ids: Optional[list[str]] = None,
    *,
    variants: Optional[dict[str, Any]] = None,
    max_steps: int = 1,
    threshold: str = "medium",
    assessor: str = "keyword",
) -> dict[str, Any]:
    """Run the clean-vs-injected loop over many flaw variants.

    The clean paper is audited **once** and reused across variants (the clean
    audit does not depend on which flaw is injected), so an LLM run costs one
    clean audit plus one audit per variant rather than two per variant.

    With ``assessor="keyword"`` this is fully deterministic and needs no API,
    which is how the harness is smoke-tested. ``assessor="llm"`` issues model
    calls and must be run under an explicit, authorized configuration.
    """
    from ..config import load_flaw_variants  # local import avoids config<->eval cycle

    catalog = variants if variants is not None else load_flaw_variants()
    selected = variant_ids or sorted(catalog)

    clean_audit = run_audit(clean_paper, max_steps=max_steps, assessor=assessor)

    pairs: list[dict[str, Any]] = []
    for vid in selected:
        variant = catalog[vid]
        injected = inject_variant(clean_paper, variant)
        gt = injected["argus_ground_truth"]
        target = gt["target_dimension"]
        injected_audit = run_audit(injected, max_steps=max_steps, assessor=assessor)
        score = evaluate_pair(
            clean_audit.risk_map, injected_audit.risk_map, target, threshold=threshold
        )
        clean_risk = clean_audit.risk_map["by_dimension"].get(target, {}).get("risk", "unknown")
        injected_risk = injected_audit.risk_map["by_dimension"].get(target, {}).get("risk", "unknown")
        score["clean_risk"] = clean_risk
        score["injected_risk"] = injected_risk
        score["meets_expected"] = _meets_expected(clean_risk, injected_risk, gt.get("expected", {}))
        pairs.append({
            "variant_id": vid,
            "ground_truth": gt,
            "score": score,
            "clean_audit": clean_audit,
            "injected_audit": injected_audit,
        })

    scores = [p["score"] for p in pairs]
    return {
        "pairs": pairs,
        "summary": summarize_results(scores),
        "by_dimension": summarize_by_dimension(pairs),
        "n_variants": len(pairs),
    }


def summarize_by_dimension(pairs: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Per-dimension detection / false-alarm / localization breakdown."""
    by_dim: dict[str, list[dict[str, Any]]] = {}
    for pair in pairs:
        by_dim.setdefault(pair["ground_truth"]["target_dimension"], []).append(pair["score"])
    out: dict[str, dict[str, Any]] = {}
    for dim, scores in sorted(by_dim.items()):
        n = len(scores)
        out[dim] = {
            "n": n,
            "detection_rate": sum(bool(s["detected"]) for s in scores) / n,
            "false_alarm_rate": sum(bool(s["false_alarm"]) for s in scores) / n,
            "localization_acc": sum(bool(s["localized"]) for s in scores) / n,
            "meets_expected_rate": sum(bool(s.get("meets_expected")) for s in scores) / n,
        }
    return out


__all__ = [
    "inject_variant",
    "validate_variant",
    "evaluate_variants",
    "summarize_by_dimension",
]
