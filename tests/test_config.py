"""Minimal tests: the config contract must hold even while modules are stubs.

Every flaw must target a real identification dimension, and ids must be unique.
"""

from argus.config import load_dimensions, load_flaws


def test_dimensions_load_and_have_required_fields():
    dims = load_dimensions()
    assert len(dims) >= 10
    for d in dims.values():
        assert d["assumption"] and d["implication"] and d["evidence"]


def test_flaws_target_real_dimensions():
    dims = load_dimensions()
    flaws = load_flaws()
    assert flaws, "flaw taxonomy is empty"
    for flaw_id, flaw in flaws.items():
        assert flaw["target_dimension"] in dims, (
            f"flaw {flaw_id} targets unknown dimension {flaw['target_dimension']}"
        )


def test_every_dimension_has_at_least_one_flaw():
    dims = load_dimensions()
    flaws = load_flaws()
    covered = {f["target_dimension"] for f in flaws.values()}
    assert covered == set(dims), f"uncovered dimensions: {set(dims) - covered}"
