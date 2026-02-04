"""Memory subsystem primitives for Rulecraft."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

RecallSource = Literal["reasoning_bank", "rulebook", "reuse_buffer", "trace_capsule"]


@dataclass
class MemoryHint:
    memory_id: str
    source: RecallSource
    summary: str
    intent_key: str | None
    state_key: str | None
    bucket_key: str | None


@dataclass
class MemoryRecallResponse:
    items: list[MemoryHint] = field(default_factory=list)


@dataclass
class MemoryRecord:
    memory_id: str
    summary: str
    intent_key: str | None
    state_key: str | None
    bucket_key: str | None
    quality: float = 0.0


@dataclass
class MemoryStore:
    reasoning_bank: list[MemoryRecord] = field(default_factory=list)
    rulebook: list[MemoryRecord] = field(default_factory=list)
    reuse_buffer: list[MemoryRecord] = field(default_factory=list)

    def recall(
        self,
        *,
        bucket_key: str,
        intent_key: str | None,
        state_key: str | None,
        top_k: int = 3,
    ) -> MemoryRecallResponse:
        candidates = (
            [("reasoning_bank", item) for item in self.reasoning_bank]
            + [("rulebook", item) for item in self.rulebook]
            + [("reuse_buffer", item) for item in self.reuse_buffer]
        )
        filtered = []
        for source, item in candidates:
            if item.bucket_key and item.bucket_key != bucket_key:
                continue
            if intent_key and item.intent_key and item.intent_key != intent_key:
                continue
            if state_key and item.state_key and item.state_key != state_key:
                continue
            filtered.append((source, item))
        ranked = sorted(filtered, key=lambda entry: entry[1].quality, reverse=True)
        hints = [
            MemoryHint(
                memory_id=item.memory_id,
                source=source,
                summary=item.summary,
                intent_key=item.intent_key,
                state_key=item.state_key,
                bucket_key=item.bucket_key,
            )
            for source, item in ranked[:top_k]
        ]
        return MemoryRecallResponse(items=hints)

    def record_reasoning(self, record: MemoryRecord) -> None:
        self.reasoning_bank.append(record)
