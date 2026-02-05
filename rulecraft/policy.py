"""Policy helpers for Rulecraft scaling and budgets."""

from __future__ import annotations

from dataclasses import dataclass

from rulecraft.schemas import VerifierResult


@dataclass
class BudgetProfile:
    max_k_probe: int = 2
    max_k_full: int = 4
    max_tokens: int | None = None
    rule_top_k: int = 4


class BudgetRouter:
    def __init__(self, profile: BudgetProfile | None = None) -> None:
        self.profile = profile or BudgetProfile()

    @staticmethod
    def decide_next_mode(
        verifier: VerifierResult,
        current_mode: str,
        attempt: int,
    ) -> str | None:
        """Escalate deterministically to tree on FAIL or insufficient evidence."""
        if current_mode == "tree":
            return None
        if "schema_violation" in verifier.reason_codes:
            return None
        if verifier.verdict == "FAIL":
            return "tree"
        if verifier.verdict == "PARTIAL" and "insufficient_evidence" in verifier.reason_codes:
            return "tree"
        return None
