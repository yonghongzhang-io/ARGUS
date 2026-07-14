"""Regression tests for the multi-variant flaw-injection harness.

The load-bearing guarantee is non-circularity: every variant must be leak-free,
i.e. after injection the paper must not contain the keyword detector's own
sentinel phrases for the target dimension (nor the variant's declared forbidden
terms). Otherwise "detection" would just be the injector planting the string the
detector greps for. These tests are deterministic and make no API calls.
"""

import json
from pathlib import Path

import pytest

from argus.config import load_flaw_variants
from argus.evaluation.variants import (
    evaluate_variants,
    inject_variant,
    validate_variant,
)

ROOT = Path(__file__).resolve().parents[1]
CLEAN_PAPER = ROOT / "examples" / "papers" / "clean_supported.json"


def _variant_ids() -> list[str]:
    # Tolerate an absent catalog so collection never hard-fails before the YAML exists.
    try:
        return sorted(load_flaw_variants())
    except FileNotFoundError:
        return []


@pytest.fixture(scope="module")
def clean_paper() -> dict:
    return json.loads(CLEAN_PAPER.read_text(encoding="utf-8"))


def test_variant_catalog_loads_and_is_nonempty():
    variants = load_flaw_variants()
    assert variants, "no flaw variants defined"
    # every dimension targeted should have at least one variant
    dims = {v["target_dimension"] for v in variants.values()}
    assert len(dims) >= 1


@pytest.mark.parametrize("vid", _variant_ids())
def test_variant_is_leak_free(vid, clean_paper):
    """Non-circularity: no detector sentinel / forbidden phrase in the injected text."""
    variant = load_flaw_variants()[vid]
    leaked = validate_variant(clean_paper, variant)
    assert not leaked, f"{vid} leaked detector/forbidden phrases: {leaked}"


@pytest.mark.parametrize("vid", _variant_ids())
def test_inject_variant_does_not_mutate_original(vid, clean_paper):
    before = json.dumps(clean_paper, sort_keys=True)
    injected = inject_variant(clean_paper, load_flaw_variants()[vid])
    assert "argus_ground_truth" not in clean_paper
    assert injected["argus_ground_truth"]["variant_id"] == vid
    assert json.dumps(clean_paper, sort_keys=True) == before


def test_keyword_dryrun_never_false_alarms(clean_paper):
    """The clean paper must stay quiet on every target dimension (keyword, no API)."""
    result = evaluate_variants(clean_paper, assessor="keyword", max_steps=1)
    assert result["summary"]["false_alarm_rate"] == 0.0
    assert 0.0 <= result["summary"]["detection_rate"] <= 1.0


def test_evaluate_variants_returns_wellformed_scores(clean_paper):
    """The keyword dry run produces well-formed scores for every variant.

    Note: we deliberately do NOT assert that omission variants are keyword-detected.
    The keyword baseline catches an omission only when the removed section's
    vocabulary is not echoed elsewhere (e.g. measurement_break); when it bleeds
    across sections (e.g. placebo terms appear in other sections) the baseline is
    blind by design -- catching those is the LLM assessor's job, not this
    deterministic check."""
    result = evaluate_variants(clean_paper, assessor="keyword", max_steps=1)
    assert result["n_variants"] == len(load_flaw_variants())
    for p in result["pairs"]:
        s = p["score"]
        assert set(("detected", "false_alarm", "localized", "clean_risk",
                    "injected_risk", "meets_expected")) <= set(s)
        assert isinstance(s["detected"], bool)
    # per-dimension breakdown covers every targeted dimension
    targeted = {v["target_dimension"] for v in load_flaw_variants().values()}
    assert set(result["by_dimension"]) == targeted
