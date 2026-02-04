"""Rule definitions and storage."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path


@dataclass
class Rule:
    rule_id: str
    version: str
    type: str
    text: str
    tags: list[str] = field(default_factory=list)
    bucket_scope: list[str] = field(default_factory=list)


class RuleStore:
    def __init__(self, rules: list[Rule] | None = None, *, path: Path | None = None) -> None:
        self.rules = rules or self._load_default(path)

    def _load_default(self, path: Path | None) -> list[Rule]:
        if path:
            payload = json.loads(path.read_text(encoding="utf-8"))
            return [Rule(**item) for item in payload.get("rules", [])]
        return [
            Rule(
                rule_id="default_general",
                version="0.1",
                type="policy",
                text="Answer clearly and concisely.",
                tags=["general"],
                bucket_scope=["I1", "I2", "I3"],
            ),
            Rule(
                rule_id="default_coding",
                version="0.1",
                type="policy",
                text="Provide runnable code with brief explanation.",
                tags=["coding"],
                bucket_scope=["I2", "I3"],
            ),
            Rule(
                rule_id="default_math",
                version="0.1",
                type="policy",
                text="Show key steps for math tasks.",
                tags=["math"],
                bucket_scope=["I2", "I3"],
            ),
        ]
