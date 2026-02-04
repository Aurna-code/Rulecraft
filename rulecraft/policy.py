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
    def _extract_impact_level(impact_level: str | None, bucket_key: str | None) -> str | None:
        if impact_level:
            return impact_level
        if bucket_key:
            return bucket_key.split("|")[0]
        return None

    def should_scale(
        self,
        verifier: VerifierResult,
        *,
        impact_level: str | None = None,
        bucket_key: str | None = None,
    ) -> bool:
        impact_level = self._extract_impact_level(impact_level, bucket_key)

        if verifier.outcome == "FAIL":
            return True
        if verifier.outcome == "UNKNOWN":
            if impact_level == "I3":
                return True
            if "insufficient_evidence" in verifier.reason_codes:
                return True
        if "schema_violation" in verifier.reason_codes:
            return False
        return verifier.verdict != "PASS"
