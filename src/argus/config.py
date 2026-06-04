"""Loaders for the identification rubric and flaw taxonomy.

These two YAML files in `config/` are the contract the whole system runs on, so
they are loaded and lightly validated here rather than parsed ad hoc elsewhere.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"


def _load(name: str) -> dict[str, Any]:
    with open(CONFIG_DIR / name, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load_dimensions() -> dict[str, Any]:
    """Identification dimensions keyed by id."""
    raw = _load("identification_dimensions.yaml")
    return {d["id"]: d for d in raw["dimensions"]}


def load_flaws() -> dict[str, Any]:
    """Flaw taxonomy keyed by id."""
    raw = _load("flaw_taxonomy.yaml")
    return {f["id"]: f for f in raw["flaws"]}
