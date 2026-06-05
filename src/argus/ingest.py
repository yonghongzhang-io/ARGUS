"""Ingest a real paper into the parsed-paper dict ARGUS audits.

Real econ-paper PDF parsing (tables, event-study figures) is a known hard
problem and deliberate future work. For the Week-0 reality check we only need
section text plus figure/table captions, so this module ingests a tiny,
dependency-free Markdown convention you can paste a paper into:

    # Title of the paper
    One or more paragraphs here become the abstract (everything before the
    first "## " heading).

    ## parallel trends
    The event-study shows ... (section body)

    ## sutva
    Spillovers are discussed ...

    @figure fig_event_study | Event-study plot with pre-treatment leads.
    @table table_balance | Balance table for treated vs control.

`@figure`/`@table` lines may appear anywhere; everything else under a `## `
heading is that section's text. Section names should match the rubric topics
(parallel trends, no anticipation, treatment timing, sutva, control group,
specification, inference, sample period, concurrent policies, robustness
placebo, data measurement) so retrieval lines up — but free text works too,
since extraction searches all blocks.

Optional PDF path: if `pdfplumber` is installed, `ingest_pdf` pulls raw text;
you then still split it into the Markdown convention above (no automatic
section/figure structure is inferred — that is the hard part left for later).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Optional

_REF_RE = re.compile(r"^@(figure|table)\s+(\S+)\s*\|\s*(.*)$", re.IGNORECASE)


def ingest_markdown(text: str, *, paper_id: Optional[str] = None) -> dict[str, Any]:
    """Parse the ARGUS Markdown convention into a parsed-paper dict."""
    title = ""
    abstract_lines: list[str] = []
    sections: dict[str, str] = {}
    figures: list[dict[str, str]] = []
    tables: list[dict[str, str]] = []

    current: Optional[str] = None  # current section name, or None = pre-section
    buf: list[str] = []

    def flush() -> None:
        # Drop empty sections — real PDFs produce bare headers (e.g. "## a r t
        # i c l e i n f o") with the body under the next heading.
        if current is not None:
            body = "\n".join(buf).strip()
            if body:
                sections[current] = body

    for raw in text.splitlines():
        line = raw.rstrip()

        ref = _REF_RE.match(line.strip())
        if ref:
            kind, ref_id, caption = ref.group(1).lower(), ref.group(2), ref.group(3).strip()
            (figures if kind == "figure" else tables).append({"id": ref_id, "caption": caption})
            continue

        if line.startswith("# ") and not title:
            title = line[2:].strip()
            continue

        if line.startswith("## "):
            flush()
            current = line[3:].strip()
            buf = []
            continue

        if current is None:
            abstract_lines.append(line)
        else:
            buf.append(line)

    flush()

    pid = paper_id or _slug(title) or "untitled"
    paper: dict[str, Any] = {"id": pid, "title": title or pid, "sections": sections}
    abstract = "\n".join(abstract_lines).strip()
    if abstract:
        paper["abstract"] = abstract
    if figures:
        paper["figures"] = figures
    if tables:
        paper["tables"] = tables
    return paper


def ingest_file(path: str | Path, *, paper_id: Optional[str] = None) -> dict[str, Any]:
    """Ingest a .md/.txt file (Markdown convention) or a .pdf (raw text only)."""
    path = Path(path)
    if path.suffix.lower() == ".pdf":
        return ingest_markdown(ingest_pdf(path), paper_id=paper_id or _slug(path.stem))
    return ingest_markdown(path.read_text(encoding="utf-8"), paper_id=paper_id or _slug(path.stem))


def ingest_pdf(path: str | Path) -> str:
    """Best-effort raw text from a PDF (requires `pip install pdfplumber`).

    No section/figure structure is inferred — paste the result into the
    Markdown convention by hand. This is intentionally minimal; real structured
    PDF parsing is future work.
    """
    try:
        import pdfplumber  # type: ignore
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise RuntimeError(
            "PDF ingest needs pdfplumber (`pip install pdfplumber`). For now, paste "
            "the paper text into the Markdown convention instead — see ingest.py."
        ) from exc

    with pdfplumber.open(str(path)) as pdf:  # pragma: no cover - needs a real PDF
        return "\n\n".join((page.extract_text() or "") for page in pdf.pages)


def _slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "_", (value or "").lower()).strip("_")
    return slug[:60]
