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
        if "schema_violation" in verifier.reason_codes:
            return None
        if verifier.outcome == "FAIL" or "insufficient_evidence" in verifier.reason_codes:
            return _next_mode(current_mode)
        return None


def _next_mode(current_mode: str) -> str | None:
    order = ["main", "probe", "tree", "full"]
    if current_mode not in order:
        return "main"
    idx = order.index(current_mode)
    if idx + 1 < len(order):
        return order[idx + 1]
    return None
