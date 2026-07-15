"""Anthropic backend exposed through an OpenAI-shaped client surface.

The two LLM call sites (`llm_assessor.assess_chain_llm`, `relevance.filter_relevant`)
speak one dialect: ``client.chat.completions.create(model, temperature, messages,
response_format={"type": "json_schema", ...})`` and then read
``resp.choices[0].message.content`` as a JSON string. Rather than branching those
call sites per provider, this module wraps the Anthropic SDK in a client that
mimics exactly that surface:

- the OpenAI ``json_schema`` response_format is translated into a single forced
  tool call (``tool_choice={"type": "tool"}``) whose ``input_schema`` is the same
  JSON schema, which is Anthropic's native mechanism for schema-constrained output;
- the tool-use block's input dict is re-serialized to a JSON string and returned
  in an object shaped like an OpenAI chat completion.

Select it with ``ARGUS_PROVIDER=anthropic`` (see ``llm_assessor.make_client``).
Requires ``ANTHROPIC_API_KEY`` and the ``anthropic`` package.
"""

from __future__ import annotations

import json
import os
from typing import Any, Optional

DEFAULT_MAX_TOKENS = 1024


class _Message:
    def __init__(self, content: str) -> None:
        self.content = content


class _Choice:
    def __init__(self, content: str) -> None:
        self.message = _Message(content)


class _Response:
    def __init__(self, content: str, raw: Any) -> None:
        self.choices = [_Choice(content)]
        self.raw = raw  # the underlying anthropic response, for tracing


class _Completions:
    def __init__(self, anthropic_client: Any) -> None:
        self._client = anthropic_client

    def create(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        temperature: Optional[float] = None,
        response_format: Optional[dict[str, Any]] = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        **_: Any,
    ) -> _Response:
        system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
        user_msgs = [
            {"role": m["role"], "content": m["content"]}
            for m in messages
            if m["role"] != "system"
        ]

        kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": user_msgs,
        }
        # Newer Claude models reject an explicit temperature; only pass it when
        # the caller insists (create_structured retries without it on rejection).
        if temperature is not None:
            kwargs["temperature"] = temperature
        if system:
            kwargs["system"] = system

        schema_spec = (response_format or {}).get("json_schema") or {}
        if schema_spec:
            name = schema_spec.get("name", "structured_output")
            kwargs["tools"] = [{
                "name": name,
                "description": "Return the structured judgement.",
                "input_schema": schema_spec.get("schema", {"type": "object"}),
            }]
            kwargs["tool_choice"] = {"type": "tool", "name": name}

        resp = self._client.messages.create(**kwargs)

        content = "{}"
        for block in getattr(resp, "content", []) or []:
            if getattr(block, "type", None) == "tool_use":
                content = json.dumps(getattr(block, "input", {}) or {})
                break
            if getattr(block, "type", None) == "text" and not schema_spec:
                content = getattr(block, "text", "") or "{}"
        return _Response(content, resp)


class _Chat:
    def __init__(self, anthropic_client: Any) -> None:
        self.completions = _Completions(anthropic_client)


class AnthropicCompatClient:
    """OpenAI-shaped facade over the Anthropic SDK (chat.completions.create only)."""

    def __init__(self, anthropic_client: Optional[Any] = None) -> None:
        if anthropic_client is None:
            if not os.environ.get("ANTHROPIC_API_KEY"):
                raise RuntimeError(
                    "ARGUS_PROVIDER=anthropic but ANTHROPIC_API_KEY is not set "
                    "(export it or add it to the project-root .env)."
                )
            import anthropic

            anthropic_client = anthropic.Anthropic()
        self.chat = _Chat(anthropic_client)


__all__ = ["AnthropicCompatClient"]
