import json
import re
from pathlib import Path

from rulecraft.adapters import EchoLLMAdapter
from rulecraft.policy import BudgetRouter
from rulecraft.runner import RulecraftRunner
from rulecraft.schemas import VerifierResult, pass_definition
from rulecraft.verifier import BasicVerifier

STABLE_KEY_PATTERN = re.compile(r"^[A-Z]+:[A-Z0-9_]+(?:[:A-Z0-9_]+)?$")


def test_t01_pass_definition_fixed() -> None:
    verifier = VerifierResult(
        schema_version="0.5.15",
        verifier_id="test",
        verdict="PASS",
        outcome="OK",
    )
    assert pass_definition(verifier) is True


def test_t02_violated_constraints_stable_keys() -> None:
    verifier = BasicVerifier()
    result = verifier.verify(
        trace_id="t",
        x_ref="x",
        candidate="not json",
        context={},
        constraints={"must_be_json": True},
    )
    violated = result["violated_constraints"]
    assert violated
    for item in violated:
        assert STABLE_KEY_PATTERN.match(item)


def test_t03_unknown_requires_reason_codes() -> None:
    verifier = BasicVerifier()
    result = verifier.verify(
        trace_id="t",
        x_ref="x",
        candidate="ok",
        context={},
        constraints=None,
    )
    assert result["outcome"] == "UNKNOWN"
    assert result["reason_codes"]


def test_t04_eventlog_jsonl_append() -> None:
    path = Path("data") / "eventlog.jsonl"
    if path.exists():
        path.unlink()

    runner = RulecraftRunner(
        llm_adapter=EchoLLMAdapter(),
        verifier=BasicVerifier(),
        eventlog_path=path,
    )
    runner.run(prompt="hello", context={"bucket_key": "I1|general|clarity_high"})

    assert path.exists()
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert {
        "schema_version",
        "trace_id",
        "x_ref",
        "selected_rules",
        "run.mode",
        "verifier",
    }.issubset(payload.keys())
    assert {"verdict", "outcome", "reason_codes"}.issubset(payload["verifier"].keys())


def test_t07_should_scale_defaults() -> None:
    router = BudgetRouter()
    fail_verifier = VerifierResult(
        schema_version="0.5.15",
        verifier_id="test",
        verdict="FAIL",
        outcome="FAIL",
    )
    assert router.should_scale(fail_verifier, impact_level="I1") is True

    unknown_i3 = VerifierResult(
        schema_version="0.5.15",
        verifier_id="test",
        verdict="PASS",
        outcome="UNKNOWN",
        reason_codes=["insufficient_evidence"],
    )
    assert router.should_scale(unknown_i3, impact_level="I3") is True

    unknown_reason = VerifierResult(
        schema_version="0.5.15",
        verifier_id="test",
        verdict="PASS",
        outcome="UNKNOWN",
        reason_codes=["insufficient_evidence"],
    )
    assert router.should_scale(unknown_reason, impact_level="I1") is True
