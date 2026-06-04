"""Parsed-paper schema validation and JSON loading.

ARGUS intentionally starts from a parsed-paper dictionary rather than a raw PDF.
This module defines the minimum contract that downstream audit stages can rely
on while leaving room for richer parsers later.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Union


PaperPath = Union[str, Path]


def load_paper(path: PaperPath) -> dict[str, Any]:
    """Load and validate a parsed-paper JSON file."""
    source = Path(path)
    with source.open(encoding="utf-8") as fh:
        paper = json.load(fh)
    return validate_paper(paper, source=str(source))


def validate_paper(paper: Any, *, source: str = "paper") -> dict[str, Any]:
    """Validate the parsed-paper contract and return the paper unchanged."""
    if not isinstance(paper, dict):
        raise ValueError(f"{source} must be a JSON object / mapping")

    _require_text(paper, "id", source)
    _require_text(paper, "title", source)
    _validate_sections(paper.get("sections"), source)

    for field in ("abstract", "introduction", "methods", "results", "discussion", "body", "appendix"):
        if field in paper and paper[field] is not None and not isinstance(paper[field], str):
            raise ValueError(f"{source}.{field} must be a string when provided")

    for field in ("figures", "tables"):
        if field in paper:
            _validate_items(paper[field], source, field)

    metadata = paper.get("metadata")
    if metadata is not None and not isinstance(metadata, dict):
        raise ValueError(f"{source}.metadata must be an object when provided")

    return paper


def _require_text(paper: dict[str, Any], field: str, source: str) -> None:
    value = paper.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{source}.{field} must be a non-empty string")


def _validate_sections(sections: Any, source: str) -> None:
    if isinstance(sections, dict):
        if not sections:
            raise ValueError(f"{source}.sections must not be empty")
        for title, text in sections.items():
            if not isinstance(title, str) or not title.strip():
                raise ValueError(f"{source}.sections keys must be non-empty strings")
            if not isinstance(text, str) or not text.strip():
                raise ValueError(f"{source}.sections[{title!r}] must be a non-empty string")
        return

    if isinstance(sections, list):
        if not sections:
            raise ValueError(f"{source}.sections must not be empty")
        for i, section in enumerate(sections):
            if not isinstance(section, dict):
                raise ValueError(f"{source}.sections[{i}] must be an object")
            title = section.get("title") or section.get("name")
            text = section.get("text") or section.get("content") or section.get("body")
            if not isinstance(title, str) or not title.strip():
                raise ValueError(f"{source}.sections[{i}].title must be a non-empty string")
            if not isinstance(text, str) or not text.strip():
                raise ValueError(f"{source}.sections[{i}].text must be a non-empty string")
        return

    raise ValueError(f"{source}.sections must be a non-empty object or list")


def _validate_items(value: Any, source: str, field: str) -> None:
    if isinstance(value, dict):
        iterable = value.items()
    elif isinstance(value, list):
        iterable = enumerate(value)
    else:
        raise ValueError(f"{source}.{field} must be an object or list when provided")

    for key, item in iterable:
        if isinstance(item, str):
            if not item.strip():
                raise ValueError(f"{source}.{field}[{key!r}] must not be empty")
            continue
        if not isinstance(item, dict):
            raise ValueError(f"{source}.{field}[{key!r}] must be a string or object")
        if not any(_has_text(item, name) for name in ("id", "label", "title", "caption", "notes", "text", "content")):
            raise ValueError(
                f"{source}.{field}[{key!r}] must include at least one searchable text field"
            )


def _has_text(item: dict[str, Any], field: str) -> bool:
    return isinstance(item.get(field), str) and bool(item[field].strip())
