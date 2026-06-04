"""The fixed tool set the bounded loop is allowed to call.

Three tools, no more. Keeping the set small and fixed is part of what bounds the
agent's behaviour and keeps traces comparable across runs.
"""

from __future__ import annotations

import re
from typing import Any

_STOPWORDS = {
    "a",
    "absent",
    "account",
    "and",
    "are",
    "as",
    "be",
    "by",
    "for",
    "from",
    "in",
    "including",
    "into",
    "is",
    "it",
    "not",
    "of",
    "on",
    "or",
    "should",
    "that",
    "the",
    "their",
    "time",
    "to",
    "units",
    "with",
    "would",
}


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


def _iter_blocks(paper: dict[str, Any]) -> list[dict[str, str]]:
    """Return searchable text blocks from common parsed-paper shapes."""
    blocks: list[dict[str, str]] = []

    for key in ("title", "abstract", "introduction", "methods", "results", "discussion", "body", "appendix"):
        value = paper.get(key)
        if value:
            blocks.append({"source": key, "text": _text(value)})

    sections = paper.get("sections")
    if isinstance(sections, dict):
        for title, value in sections.items():
            blocks.append({"source": f"section:{title}", "text": _text(value)})
    elif isinstance(sections, list):
        for i, section in enumerate(sections):
            if isinstance(section, dict):
                title = section.get("title") or section.get("name") or str(i)
                text = section.get("text") or section.get("content") or section.get("body")
                blocks.append({"source": f"section:{title}", "text": _text(text)})
            else:
                blocks.append({"source": f"section:{i}", "text": _text(section)})

    for key in ("figures", "tables"):
        items = paper.get(key)
        if isinstance(items, dict):
            iterable = items.items()
        elif isinstance(items, list):
            iterable = enumerate(items)
        else:
            iterable = []

        for ref, item in iterable:
            if isinstance(item, dict):
                label = item.get("id") or item.get("label") or item.get("title") or str(ref)
                parts = [
                    item.get("title"),
                    item.get("caption"),
                    item.get("notes"),
                    item.get("text"),
                    item.get("content"),
                ]
                text = " ".join(_text(part) for part in parts if part)
            else:
                label = str(ref)
                text = _text(item)
            blocks.append({"source": f"{key}:{label}", "text": text})

    return [b for b in blocks if b["text"].strip()]


def _chunks(block: dict[str, str], *, max_chars: int = 900) -> list[dict[str, str]]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", block["text"]) if p.strip()]
    if not paragraphs:
        paragraphs = [block["text"].strip()]

    out: list[dict[str, str]] = []
    for paragraph in paragraphs:
        if len(paragraph) <= max_chars:
            out.append({"source": block["source"], "text": paragraph})
            continue

        sentences = re.split(r"(?<=[.!?])\s+", paragraph)
        current: list[str] = []
        current_len = 0
        for sentence in sentences:
            if current and current_len + len(sentence) > max_chars:
                out.append({"source": block["source"], "text": " ".join(current)})
                current = []
                current_len = 0
            current.append(sentence)
            current_len += len(sentence) + 1
        if current:
            out.append({"source": block["source"], "text": " ".join(current)})
    return out


def _query_tokens(query: str) -> list[str]:
    tokens = []
    for token in re.findall(r"[a-zA-Z][a-zA-Z\-]{2,}", query.lower()):
        token = token.strip("-")
        if token and token not in _STOPWORDS:
            tokens.append(token)
    return sorted(set(tokens))


def evidence_search(paper: dict[str, Any], query: str, *, k: int = 5) -> list[dict[str, Any]]:
    """Retrieve up to k passages from the paper relevant to `query`."""
    tokens = _query_tokens(query)
    if not tokens:
        return []

    matches: list[dict[str, Any]] = []
    for block in _iter_blocks(paper):
        for chunk in _chunks(block):
            text = chunk["text"]
            text_lower = text.lower()
            matched = [token for token in tokens if token in text_lower]
            if not matched:
                continue
            score = sum(text_lower.count(token) for token in matched)
            matches.append(
                {
                    "source": chunk["source"],
                    "text": text,
                    "score": score,
                    "matched_terms": matched[:12],
                }
            )

    matches.sort(key=lambda item: (item["score"], len(item["matched_terms"])), reverse=True)
    return matches[:k]


def figure_parse(paper: dict[str, Any], figure_ref: str) -> dict[str, Any]:
    """Extract structured content from a figure/table (e.g. event-study plot)."""
    ref = figure_ref.lower()
    for collection_name in ("figures", "tables"):
        collection = paper.get(collection_name)
        if isinstance(collection, dict):
            items = collection.items()
        elif isinstance(collection, list):
            items = enumerate(collection)
        else:
            continue

        for key, item in items:
            if isinstance(item, dict):
                label = _text(item.get("id") or item.get("label") or item.get("title") or key)
                haystack = " ".join(
                    _text(item.get(name))
                    for name in ("id", "label", "title", "caption", "notes", "text", "content")
                ).lower()
                if ref in label.lower() or ref in haystack:
                    return {"found": True, "type": collection_name[:-1], "ref": label, **item}
            elif ref in _text(key).lower() or ref in _text(item).lower():
                return {"found": True, "type": collection_name[:-1], "ref": _text(key), "text": _text(item)}
    return {"found": False, "ref": figure_ref}


def policy_lookup(policy_name: str) -> dict[str, Any]:
    """Look up policy metadata (announcement vs. implementation dates, scope)."""
    key = policy_name.lower()
    if "carbon" in key and ("trading" in key or "emission" in key or "ets" in key):
        return {
            "policy_name": policy_name,
            "scope": "China carbon emissions trading pilot provinces/cities",
            "announcement_year": 2011,
            "implementation_years": [2013, 2014],
            "source": "static ARGUS baseline metadata",
        }
    return {
        "policy_name": policy_name,
        "scope": "unknown",
        "source": "static ARGUS baseline metadata",
    }


DEFAULT_TOOLS = {
    "evidence_search": evidence_search,
    "figure_parse": figure_parse,
    "policy_lookup": policy_lookup,
}
