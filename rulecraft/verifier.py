"""Simple deterministic verifier implementation."""

from __future__ import annotations

import json
from dataclasses import dataclass

from rulecraft.schemas import VerifierResult


@dataclass
class BasicVerifier:
    verifier_id: str = "basic_l1"
    schema_version: str = "0.5.15"

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
        constraints = constraints or {}
        reason_codes: list[str] = []
        violated: list[str] = []
        verdict = "PASS"
        outcome = "UNKNOWN"

        content = candidate if isinstance(candidate, str) else json.dumps(candidate)

        if constraints.get("must_be_json"):
            try:
                json.loads(content)
            except json.JSONDecodeError:
                verdict = "FAIL"
                violated.append("FORMAT:JSON_ONLY")
                reason_codes.append("schema_violation")

        required_substrings = constraints.get("required_substrings", [])
        for required in required_substrings:
            if required not in content:
                verdict = "FAIL"
                violated.append(f"CONSTRAINT:REQUIRED:{required}")
                reason_codes.append("constraint_violation")

        forbidden_substrings = constraints.get("forbidden_substrings", [])
        for forbidden in forbidden_substrings:
            if forbidden in content:
                verdict = "FAIL"
                violated.append(f"CONSTRAINT:FORBIDDEN:{forbidden}")
                reason_codes.append("constraint_violation")

        return VerifierResult(
            schema_version=self.schema_version,
            verifier_id=self.verifier_id,
            verdict=verdict,
            outcome=outcome,
            score=None,
            reason_codes=reason_codes,
            violated_constraints=violated,
        ).__dict__
