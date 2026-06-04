"""Inject exactly one known flaw into a credible DID paper.

Each flaw in config/flaw_taxonomy.yaml targets a single identification dimension,
so the injected version has local ground truth: ARGUS should flag that dimension
(and only that one) relative to the clean version.
"""

from __future__ import annotations

import copy
from typing import Any

from ..config import load_flaws

_INJECTION_TEXT = {
    "pretrend_divergence": (
        "Injected identification flaw: treated and control units have different "
        "pre-treatment trends, with significant leads and non-zero pre-period coefficients."
    ),
    "anticipation_effect": (
        "Injected identification flaw: the policy announcement precedes implementation, "
        "and behavior shifts before implementation with a significant lead coefficient."
    ),
    "forbidden_comparison": (
        "Injected identification flaw: the design uses plain TWFE for staggered adoption, "
        "allowing already-treated units as controls and negative-weight forbidden comparison."
    ),
    "spillover_contamination": (
        "Injected identification flaw: spillover contamination leaves adjacent provinces "
        "as controls, with no interference discussion and treated as clean controls."
    ),
    "noncomparable_controls": (
        "Injected identification flaw: controls show large pre-treatment imbalance, "
        "are poorly matched, and the study has no balance table."
    ),
    "bad_control": (
        "Injected identification flaw: the specification adds a bad control, a "
        "post-treatment control on the causal path that is outcome-affected."
    ),
    "understated_se": (
        "Injected identification flaw: unclustered standard errors are reported, "
        "while serial correlation ignored and spatial correlation ignored."
    ),
    "cherrypicked_window": (
        "Injected identification flaw: a cherry-picked window creates the result, "
        "with no window sensitivity and the result concentrated in a narrow span."
    ),
    "confounding_policy": (
        "Injected identification flaw: a confounding policy is an unaddressed "
        "concurrent policy, and another policy explains the outcome change."
    ),
    "missing_placebo": (
        "Injected identification flaw: missing placebo evidence; no placebo, "
        "no falsification, and no permutation checks are reported."
    ),
    "measurement_break": (
        "Injected identification flaw: a measurement break and definition change "
        "create a measurement regime shift that coincides with treatment."
    ),
}


def inject_flaw(paper: dict[str, Any], flaw_id: str) -> dict[str, Any]:
    """Return an injected copy of `paper` plus its ground-truth label."""
    flaws = load_flaws()
    if flaw_id not in flaws:
        raise KeyError(f"unknown flaw: {flaw_id}")
    flaw = flaws[flaw_id]
    injected = copy.deepcopy(paper)
    injected["id"] = f"{paper.get('id', 'unknown')}__{flaw_id}"

    sections = injected.setdefault("sections", {})
    if isinstance(sections, dict):
        sections[f"injected:{flaw['target_dimension']}"] = _INJECTION_TEXT[flaw_id]
    elif isinstance(sections, list):
        sections.append(
            {
                "title": f"injected:{flaw['target_dimension']}",
                "text": _INJECTION_TEXT[flaw_id],
            }
        )
    else:
        injected["sections"] = {
            f"injected:{flaw['target_dimension']}": _INJECTION_TEXT[flaw_id],
        }

    injected["argus_ground_truth"] = {
        "flaw_id": flaw_id,
        "target_dimension": flaw["target_dimension"],
        "severity": flaw["severity"],
        "description": flaw["description"],
    }
    return injected
