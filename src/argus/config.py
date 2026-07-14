"""Loaders for the identification rubric and flaw taxonomy.

These two YAML files in `config/` are the contract the whole system runs on, so
they are loaded and lightly validated here rather than parsed ad hoc elsewhere.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"
_DIMENSION_FIELDS = ("id", "name", "assumption", "implication", "evidence")
_FLAW_FIELDS = ("id", "target_dimension", "severity", "description", "injection_method", "detection_signal")
_VARIANT_FIELDS = ("variant_id", "target_dimension", "flaw_type", "severity", "injection", "expected")
_SEVERITIES = {"low", "medium", "high"}
_FLAW_TYPES = {"commission", "omission"}


def _load(name: str) -> dict[str, Any]:
    with open(CONFIG_DIR / name, encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    if not isinstance(raw, dict):
        raise ValueError(f"{name} must contain a mapping")
    return raw


def _index_by_id(
    rows: Any, *, collection: str, required_fields: tuple[str, ...], id_field: str = "id"
) -> dict[str, Any]:
    if not isinstance(rows, list):
        raise ValueError(f"{collection} must be a list")

    indexed: dict[str, Any] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError(f"each {collection} entry must be a mapping")
        missing = [field for field in required_fields if field not in row or row[field] in (None, "", [])]
        if missing:
            raise ValueError(f"{collection} entry missing required fields: {missing}")
        row_id = row[id_field]
        if row_id in indexed:
            raise ValueError(f"duplicate {collection} id: {row_id}")
        indexed[row_id] = row
    return indexed


def load_dimensions() -> dict[str, Any]:
    """Identification dimensions keyed by id."""
    raw = _load("identification_dimensions.yaml")
    dimensions = _index_by_id(
        raw.get("dimensions"),
        collection="dimensions",
        required_fields=_DIMENSION_FIELDS,
    )
    for dim_id, dimension in dimensions.items():
        if not isinstance(dimension["evidence"], list):
            raise ValueError(f"dimension {dim_id} evidence must be a list")
    return dimensions


def load_flaws() -> dict[str, Any]:
    """Flaw taxonomy keyed by id."""
    raw = _load("flaw_taxonomy.yaml")
    flaws = _index_by_id(
        raw.get("flaws"),
        collection="flaws",
        required_fields=_FLAW_FIELDS,
    )
    for flaw_id, flaw in flaws.items():
        if flaw["severity"] not in _SEVERITIES:
            raise ValueError(f"flaw {flaw_id} has unknown severity: {flaw['severity']}")
    return flaws


def load_flaw_variants() -> dict[str, Any]:
    """Flaw variants keyed by variant_id (config/flaw_variants.yaml).

    Each variant is a YAML-declared perturbation targeting one dimension, letting
    a dimension carry several flaw variants (differing prose, position, severity)
    rather than the single recipe in flaw_taxonomy.yaml. See
    ``argus.evaluation.variants`` for how variants are injected and validated.
    """
    raw = _load("flaw_variants.yaml")
    variants = _index_by_id(
        raw.get("variants"),
        collection="variants",
        required_fields=_VARIANT_FIELDS,
        id_field="variant_id",
    )
    for vid, variant in variants.items():
        if variant["severity"] not in _SEVERITIES:
            raise ValueError(f"variant {vid} has unknown severity: {variant['severity']}")
        if variant["flaw_type"] not in _FLAW_TYPES:
            raise ValueError(f"variant {vid} has unknown flaw_type: {variant['flaw_type']}")
        if not isinstance(variant["injection"], dict):
            raise ValueError(f"variant {vid} injection must be a mapping")
        if not isinstance(variant["expected"], dict):
            raise ValueError(f"variant {vid} expected must be a mapping")
    return variants
