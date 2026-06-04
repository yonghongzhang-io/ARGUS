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
_SEVERITIES = {"low", "medium", "high"}


def _load(name: str) -> dict[str, Any]:
    with open(CONFIG_DIR / name, encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    if not isinstance(raw, dict):
        raise ValueError(f"{name} must contain a mapping")
    return raw


def _index_by_id(rows: Any, *, collection: str, required_fields: tuple[str, ...]) -> dict[str, Any]:
    if not isinstance(rows, list):
        raise ValueError(f"{collection} must be a list")

    indexed: dict[str, Any] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError(f"each {collection} entry must be a mapping")
        missing = [field for field in required_fields if field not in row or row[field] in (None, "", [])]
        if missing:
            raise ValueError(f"{collection} entry missing required fields: {missing}")
        row_id = row["id"]
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
