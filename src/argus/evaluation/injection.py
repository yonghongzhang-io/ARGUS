"""Inject exactly one known flaw into a credible DID paper.

Each flaw in config/flaw_taxonomy.yaml targets a single identification dimension,
so the injected version has local ground truth: ARGUS should flag that dimension
(and only that one) relative to the clean version.

Injection performs a *realistic structural perturbation* of the paper, not the
insertion of a sentinel sentence that names the flaw. There are two operations:

  - ``remove``  : delete the section / figure / table that supplies the support
                  for the target dimension (models an *omission*-type threat).
                  An auditor can flag this non-circularly, by noticing the
                  *absence* of evidence.
  - ``replace`` : overwrite a section with flawed prose written the way a real,
                  flawed paper would write it (models a *commission*-type threat
                  where flawed evidence is present).

Crucially, the replacement prose does **not** contain the negative-signal phrases
the baseline detector greps for. If it did, detection would be circular — the
injector would be planting the exact string the detector looks for. The flawed
prose therefore describes the design in neutral language and leaves detection as
a genuine (and, for the keyword baseline, often unsolved) task.
"""

from __future__ import annotations

import copy
from typing import Any

from ..config import load_flaws

# Per-flaw perturbation recipe. Keys reference the section / figure / table ids
# used by the parsed-paper fixtures. Missing targets are skipped gracefully.
_INJECTIONS: dict[str, dict[str, Any]] = {
    # ---- omission-type: remove the supporting evidence -------------------
    "spillover_contamination": {
        "op": "remove",
        "sections": ["sutva"],
    },
    "noncomparable_controls": {
        "op": "remove",
        "sections": ["control group"],
        "tables": ["table_balance"],
    },
    "cherrypicked_window": {
        "op": "remove",
        "sections": ["sample period"],
    },
    "confounding_policy": {
        "op": "remove",
        "sections": ["concurrent policies"],
    },
    "missing_placebo": {
        "op": "remove",
        "sections": ["robustness placebo"],
    },
    "measurement_break": {
        "op": "remove",
        "sections": ["data measurement"],
    },
    # ---- commission-type: replace with flawed-but-natural prose -----------
    "pretrend_divergence": {
        "op": "replace",
        "sections": {
            "parallel trends": (
                "Figure 2 plots event-study estimates around the pilot launch. "
                "The pre-period point estimates drift upward for treated provinces "
                "relative to controls, and the paper proceeds to the main results "
                "without reconciling this pattern."
            ),
        },
        "figure_captions": {
            "fig_event_study": (
                "Event-study estimates for the pilot, with pre-period coefficients "
                "drifting upward before treatment."
            ),
        },
    },
    "anticipation_effect": {
        "op": "replace",
        "sections": {
            "no anticipation": (
                "Outcomes begin moving in pilot provinces during the gap between "
                "the 2011 policy announcement and the 2013-2014 rollout. Treatment "
                "is coded at the rollout date used throughout the analysis."
            ),
        },
    },
    "forbidden_comparison": {
        "op": "replace",
        "sections": {
            "treatment timing": (
                "Effects are estimated with a two-way fixed-effects regression that "
                "pools all province-years, so later adopters are compared against "
                "earlier adopters as the timing varies across pilots."
            ),
        },
    },
    "bad_control": {
        "op": "replace",
        "sections": {
            "specification": (
                "The preferred specification conditions on firm-level energy "
                "intensity measured after the pilot began, alongside province and "
                "year fixed effects, and reports the resulting estimates."
            ),
        },
    },
    "understated_se": {
        "op": "replace",
        "sections": {
            "inference": (
                "Standard errors are computed at the firm-year level, treating each "
                "observation as independent across the panel."
            ),
        },
    },
}


def _remove_sections(paper: dict[str, Any], keys: list[str]) -> None:
    sections = paper.get("sections")
    if isinstance(sections, dict):
        for key in keys:
            sections.pop(key, None)
    elif isinstance(sections, list):
        paper["sections"] = [
            s
            for s in sections
            if not (isinstance(s, dict) and (s.get("title") or s.get("name")) in keys)
        ]


def _remove_refs(paper: dict[str, Any], collection: str, ids: list[str]) -> None:
    items = paper.get(collection)
    if isinstance(items, list):
        paper[collection] = [
            it
            for it in items
            if not (isinstance(it, dict) and (it.get("id") or it.get("label")) in ids)
        ]
    elif isinstance(items, dict):
        for ref in ids:
            items.pop(ref, None)


def _replace_sections(paper: dict[str, Any], mapping: dict[str, str]) -> None:
    sections = paper.get("sections")
    if isinstance(sections, dict):
        for key, text in mapping.items():
            if key in sections:
                sections[key] = text
    elif isinstance(sections, list):
        for s in sections:
            if isinstance(s, dict):
                title = s.get("title") or s.get("name")
                if title in mapping:
                    if "text" in s:
                        s["text"] = mapping[title]
                    elif "content" in s:
                        s["content"] = mapping[title]
                    else:
                        s["text"] = mapping[title]


def _replace_figure_captions(paper: dict[str, Any], mapping: dict[str, str]) -> None:
    figures = paper.get("figures")
    if isinstance(figures, list):
        for fig in figures:
            if isinstance(fig, dict) and fig.get("id") in mapping:
                fig["caption"] = mapping[fig["id"]]


def inject_flaw(paper: dict[str, Any], flaw_id: str) -> dict[str, Any]:
    """Return an injected copy of `paper` plus its ground-truth label.

    The original `paper` is never mutated (deep copy), and the perturbation is a
    realistic structural edit rather than a sentinel sentence.
    """
    flaws = load_flaws()
    if flaw_id not in flaws:
        raise KeyError(f"unknown flaw: {flaw_id}")
    if flaw_id not in _INJECTIONS:
        raise KeyError(f"no injection recipe for flaw: {flaw_id}")

    flaw = flaws[flaw_id]
    recipe = _INJECTIONS[flaw_id]
    injected = copy.deepcopy(paper)
    injected["id"] = f"{paper.get('id', 'unknown')}__{flaw_id}"

    if recipe["op"] == "remove":
        _remove_sections(injected, recipe.get("sections", []))
        _remove_refs(injected, "figures", recipe.get("figures", []))
        _remove_refs(injected, "tables", recipe.get("tables", []))
    elif recipe["op"] == "replace":
        _replace_sections(injected, recipe.get("sections", {}))
        _replace_figure_captions(injected, recipe.get("figure_captions", {}))
    else:  # pragma: no cover - guarded by the static recipe table
        raise ValueError(f"unknown injection op: {recipe['op']}")

    injected["argus_ground_truth"] = {
        "flaw_id": flaw_id,
        "target_dimension": flaw["target_dimension"],
        "severity": flaw["severity"],
        "description": flaw["description"],
        "injection_op": recipe["op"],
    }
    return injected
