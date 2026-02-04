"""Adapters for LLM and verifier backends."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class LLMAdapter(Protocol):
    """Common LLM interface."""

    def generate(
        self,
        messages: list[dict],
        *,
        temperature: float = 0.2,
        max_tokens: int | None = None,
        tools: list[dict] | None = None,
        response_format: dict | None = None,
        seed: int | None = None,
    ) -> tuple[str | dict, dict]:
        """Return (text_or_toolcall, meta)."""


class VerifierAdapter(Protocol):
    """Verifier adapter interface."""

    def verify(
        self,
        *,
        trace_id: str,
        x_ref: str,
        candidate: object,
        context: dict,
        constraints: dict | None = None,
        artifacts: dict | None = None,
        meta: dict | None = None,
    ) -> dict:
        """Return a VerifierResult-compatible dict."""


@dataclass
class EchoLLMAdapter:
    """Minimal adapter for local testing."""

    model: str = "echo"

    def generate(
        self,
        messages: list[dict],
        *,
        temperature: float = 0.2,
        max_tokens: int | None = None,
        tools: list[dict] | None = None,
        response_format: dict | None = None,
        seed: int | None = None,
    ) -> tuple[str, dict]:
        content = messages[-1]["content"] if messages else ""
        meta = {
            "model": self.model,
            "backend": "local",
            "latency_ms": 0,
            "tokens_in": len(content.split()),
            "tokens_out": len(content.split()),
        }
        return content, meta
