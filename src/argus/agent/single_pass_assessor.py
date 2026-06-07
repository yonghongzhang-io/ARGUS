"""Single-pass LLM assessor (M4 ablation: the architectural opposite of ARGUS).

The WHOLE paper + the 11-dimension rubric go into ONE model call: no retrieval,
no relevance gate, no bounded per-dimension loop, no `unknown`-by-construction.
It judges evidence ADEQUACY with the SAME standard, SAME provider/model, and SAME
canonical rubric as the two-stage assessor (``llm_assessor.py``), so the ONLY
thing that differs is the architecture -- which is what M4 isolates.

Because there is no relevance gate, any extra over-flagging on real papers is
attributable to the missing gate, not to a weaker model or a different rubric:
the two-stage path can answer ``unknown`` when retrieval finds nothing, whereas
single-pass must commit from the whole text.

Returns the same judgement shape as the keyword/llm assessors
(``risk`` / ``evidence_status`` / ``rationale`` / ``cited_evidence``) so the
pipeline's localization, report, and the flaw-injection metrics consume it
unchanged. ``risk`` may be ``unknown`` (the model abstaining), which lets the
real-paper unknown/high-share comparison be apples-to-apples.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Callable, Optional

from .llm_assessor import DEFAULT_MODEL, make_client

RISKS = ("low", "medium", "high", "unknown")

# Same adequacy standard as llm_assessor._SYSTEM_PROMPT, extended to audit ALL
# dimensions in one pass and emit JSON keyed by dimension id.
SYSTEM_PROMPT = (
    "You audit the causal-IDENTIFICATION credibility of a difference-in-differences "
    "(DID) study. You do NOT judge whether the estimated effect is true -- the "
    "counterfactual is never observed. For EACH identification dimension in the "
    "rubric, judge whether the evidence the paper ACTUALLY REPORTS is ADEQUATE to "
    "support that dimension's assumption.\n\n"
    "Crucial distinction: evidence PRESENCE is not evidence ADEQUACY. A section "
    "labelled 'robustness' that only swaps a specification is not a placebo test; "
    "'clustered standard errors' with no level or cluster count is not adequate "
    "inference; an event-study plot with non-null leads does not support parallel "
    "trends. Assess whether the reported evidence establishes the testable "
    "implication, and whether it reveals a flaw.\n\n"
    "For each dimension output one risk level:\n"
    "  low      : adequate, credible evidence is reported.\n"
    "  medium   : evidence is partial, indirect, or weak.\n"
    "  high     : the required evidence is absent, or present but flawed.\n"
    "  unknown  : the text gives no basis to judge either way (use sparingly).\n"
    "Also output evidence_status in {sufficient, partial, missing, flawed} "
    "(roughly sufficient->low, partial->medium, missing/flawed->high). Be "
    "conservative: absent, thin, or flawed evidence is not 'supported'.\n\n"
    "Return STRICT JSON only (no prose, no markdown fences): an object keyed by the "
    "dimension id, each value an object with keys \"risk\", \"evidence_status\", "
    "\"cited_evidence\" (a short verbatim span you relied on, or \"\"), and "
    "\"rationale\" (one sentence)."
)

USER_TEMPLATE = (
    "RUBRIC (dimension id -> assumption / testable implication / expected evidence):\n"
    "{rubric_block}\n\n"
    "PAPER TEXT:\n{paper_text}\n\n"
    "Audit every dimension id listed in the rubric. JSON only."
)


def paper_to_text(paper: dict[str, Any]) -> str:
    """Flatten a parsed-paper dict into the whole-paper text the model sees.

    Includes title, abstract, every section, and figure/table captions -- the
    single-pass assessor has no retrieval, so it is given everything.
    """
    parts: list[str] = []
    if paper.get("title"):
        parts.append(str(paper["title"]))
    if paper.get("abstract"):
        parts.append(str(paper["abstract"]))
    sections = paper.get("sections")
    if isinstance(sections, dict):
        for title, text in sections.items():
            parts.append(f"## {title}\n{text}")
    elif isinstance(sections, list):
        for sec in sections:
            if isinstance(sec, dict):
                parts.append(f"## {sec.get('title', '')}\n{sec.get('text', '')}")
            else:
                parts.append(str(sec))
    for field in ("figures", "tables"):
        for item in paper.get(field, []) or []:
            cap = (item or {}).get("caption", "")
            if cap:
                parts.append(f"[{field[:-1]} {item.get('id', '')}] {cap}")
    return "\n\n".join(p for p in parts if p)


def _rubric_block(dims: dict[str, Any]) -> str:
    """Render the canonical rubric (config.load_dimensions()) into the prompt."""
    lines = []
    for did, d in dims.items():
        evidence = d.get("evidence", []) or d.get("expected_evidence", []) or []
        lines.append(
            f"- {did} ({d.get('name', did)}):\n"
            f"    assumption: {str(d.get('assumption', '')).strip()}\n"
            f"    implication: {str(d.get('implication', '')).strip()}\n"
            f"    expected_evidence: {'; '.join(evidence)}"
        )
    return "\n".join(lines)


def _coerce(raw: Any, dims: dict[str, Any]) -> dict[str, dict]:
    out = {}
    for did in dims:
        cell = raw.get(did, {}) if isinstance(raw, dict) else {}
        risk = str(cell.get("risk", "unknown")).strip().lower()
        if risk not in RISKS:
            risk = "unknown"
        cited = cell.get("cited_evidence", cell.get("evidence", []))
        if isinstance(cited, str):
            cited = [cited] if cited else []
        out[did] = {
            "risk": risk,
            "evidence_status": str(cell.get("evidence_status", "")).strip().lower(),
            "rationale": str(cell.get("rationale", ""))[:500],
            "cited_evidence": [str(c)[:300] for c in (cited or [])][:5],
            "assessor": "single_pass",
        }
    return out


def _default_openai_call(system: str, user: str, model: str,
                         client: Optional[Any] = None) -> str:
    """Same provider/params as the two-stage assessor: OpenAI, temperature 0."""
    client = make_client(client)
    resp = client.chat.completions.create(
        model=model,
        temperature=0,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        response_format={"type": "json_object"},
    )
    return resp.choices[0].message.content or "{}"


def judge_text(
    paper_text: str,
    dims: dict[str, Any],
    *,
    client: Optional[Any] = None,
    model: Optional[str] = None,
    call_fn: Optional[Callable[[str, str, str], str]] = None,
    max_paper_chars: int = 120_000,
) -> dict[str, dict]:
    """One model call over the whole paper text; returns {dim_id: judgement}."""
    model = model or os.environ.get("ARGUS_LLM_MODEL", DEFAULT_MODEL)
    user = USER_TEMPLATE.format(
        rubric_block=_rubric_block(dims),
        paper_text=paper_text[:max_paper_chars],
    )
    if call_fn is not None:
        raw_text = call_fn(SYSTEM_PROMPT, user, model)
    else:
        raw_text = _default_openai_call(SYSTEM_PROMPT, user, model, client)
    raw_text = re.sub(r"^```(?:json)?|```$", "", raw_text.strip()).strip()
    try:
        raw = json.loads(raw_text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw_text, re.S)
        raw = json.loads(m.group(0)) if m else {}
    return _coerce(raw, dims)


def assess_single_pass(
    dims: dict[str, Any],
    paper: dict[str, Any],
    *,
    client: Optional[Any] = None,
    model: Optional[str] = None,
    call_fn: Optional[Callable[[str, str, str], str]] = None,
) -> dict[str, dict]:
    """Pipeline entry: serialize the paper and judge all dimensions in one pass."""
    return judge_text(paper_to_text(paper), dims, client=client, model=model, call_fn=call_fn)


def make_single_pass_assessor(
    model: Optional[str] = None,
    *,
    client: Optional[Any] = None,
    call_fn: Optional[Callable[[str, str, str], str]] = None,
    max_paper_chars: int = 120_000,
) -> Callable[[str, dict], dict]:
    """Factory for the flaw-injection harness: assessor(paper_text, dims)."""
    def assessor(paper_text: str, dims: dict[str, Any]) -> dict:
        return judge_text(paper_text, dims, client=client, model=model,
                          call_fn=call_fn, max_paper_chars=max_paper_chars)
    return assessor
