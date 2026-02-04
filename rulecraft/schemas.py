"""Core schemas and derived semantics for Rulecraft."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

SchemaVersion = Literal["0.5.15"]
Verdict = Literal["PASS", "FAIL", "PARTIAL"]
Outcome = Literal["OK", "FAIL", "UNKNOWN"]


@dataclass
class FGFCItem:
    claim: str
    evidence: list[str]
    error_type: str | None = None
    correction: str | None = None


@dataclass
class FGFCReport:
    items: list[FGFCItem] = field(default_factory=list)


@dataclass
class VerifierResult:
    schema_version: SchemaVersion
    verifier_id: str
    verdict: Verdict
    outcome: Outcome
    score: float | None = None
    reason_codes: list[str] = field(default_factory=list)
    violated_constraints: list[str] = field(default_factory=list)
    fgfc: FGFCReport | None = None
    failure_cluster_id: str | None = None


def pass_definition(verifier: VerifierResult) -> bool:
    """PASS iff verdict == PASS and outcome != FAIL."""
    return verifier.verdict == "PASS" and verifier.outcome != "FAIL"


@dataclass
class SelectedRule:
    rule_id: str
    version: str
    type: str


@dataclass
class EventLog:
    schema_version: SchemaVersion
    trace_id: str
    bucket_key: str
    intent_key: str | None
    state_key: str | None
    x_ref: str
    run_mode: str
    selected_rules: list[SelectedRule] = field(default_factory=list)
    pass_value: int = 0
    verifier_id: str = ""
    verifier_verdict: Verdict = "PASS"
    verifier_outcome: Outcome = "UNKNOWN"
    verifier_reason_codes: list[str] = field(default_factory=list)
    verifier_violated_constraints: list[str] = field(default_factory=list)
    memory_recall_used_ids: list[str] = field(default_factory=list)
    cost_profile: dict | None = None
