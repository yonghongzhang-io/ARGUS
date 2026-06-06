"""Patch 1 — section-level retrieval with dimension-specific query packs.

The keyword baseline retrieves small token-matched chunks, which on real papers
surfaces the wrong passage for a dimension (e.g. an abortion-rate table for
parallel trends). This module retrieves at *section* granularity using a richer
per-dimension query pack, so the relevance gate and adequacy assessor get whole
sections to work with rather than a stray sentence.

Deterministic and dependency-free; used only by the LLM assessment path so the
keyword baseline (and its frozen numbers) is untouched.
"""

from __future__ import annotations

from typing import Any

from .tools import _iter_blocks, _query_tokens

# Richer query packs than the baseline's single search string. Casting a wider
# net is fine here because the LLM relevance gate (Patch 2) filters afterwards.
DIMENSION_QUERIES: dict[str, str] = {
    "parallel_trends": (
        "parallel trend pre-trend pretrend pre-treatment event study event-study "
        "lead coefficients dynamic effects before treatment placebo timing common trend"
    ),
    "no_anticipation": (
        "anticipation announcement pre-policy response policy announcement before "
        "implementation rollout forward-looking expectation timing of effect"
    ),
    "treatment_timing": (
        "staggered adoption treatment timing two-way fixed effects twfe callaway "
        "santanna sun abraham goodman bacon heterogeneous dynamic event study cohort"
    ),
    "treatment_definition_sutva": (
        "sutva spillover interference neighboring contamination spatial effects border "
        "adjacent regions leakage displacement general equilibrium treatment definition"
    ),
    "control_group": (
        "control group comparison group balance table matched matching synthetic control "
        "donor pool covariate balance pre-treatment characteristics comparable"
    ),
    "specification": (
        "specification robustness fixed effects controls covariates functional form "
        "alternative specifications bad control collider post-treatment control"
    ),
    "inference": (
        "standard errors clustering clustered wild cluster bootstrap inference serial "
        "correlation autocorrelation few clusters significance level"
    ),
    "sample_period": (
        "sample period time window study period start year end year panel balanced "
        "unbalanced attrition entry exit window sensitivity"
    ),
    "concurrent_policies": (
        "concurrent policy co-timed simultaneous other policies confounding intervention "
        "contemporaneous reform policy controls placebo periods omitted policy"
    ),
    "robustness_placebo": (
        "placebo falsification permutation randomization inference robustness check "
        "placebo treatment placebo outcome sensitivity analysis"
    ),
    "data_measurement": (
        "data source measurement definition stability reporting change missing data "
        "measurement error coverage consistency variable construction"
    ),
}


def _query_for(dimension: dict[str, Any]) -> str:
    dim_id = dimension.get("id")
    if dim_id in DIMENSION_QUERIES:
        return DIMENSION_QUERIES[dim_id]
    parts = [
        dimension.get("name", ""),
        dimension.get("assumption", ""),
        dimension.get("implication", ""),
        " ".join(dimension.get("expected_evidence", []) or []),
    ]
    return " ".join(p for p in parts if p)


def retrieve_sections(
    paper: dict[str, Any],
    dimension: dict[str, Any],
    *,
    k: int = 4,
    max_chars: int = 2000,
) -> list[dict[str, Any]]:
    """Return up to k whole sections most relevant to `dimension`.

    Sections (and figure/table caption blocks) are scored by overlap with the
    dimension's query pack and returned at full granularity (truncated to
    `max_chars`), not as small chunks.
    """
    tokens = _query_tokens(_query_for(dimension))
    if not tokens:
        return []

    scored: list[dict[str, Any]] = []
    for block in _iter_blocks(paper):
        text = block["text"]
        low = text.lower()
        matched = [t for t in tokens if t in low]
        if not matched:
            continue
        score = sum(low.count(t) for t in matched)
        scored.append(
            {
                "source": block["source"],
                "text": text[:max_chars],
                "score": score,
                "matched_terms": matched[:12],
            }
        )

    scored.sort(key=lambda it: (it["score"], len(it["matched_terms"])), reverse=True)
    return scored[:k]
