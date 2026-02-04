import json
import re
from pathlib import Path

from rulecraft.adapters import EchoLLMAdapter
from rulecraft.policy import BudgetRouter
from rulecraft.runner import RulecraftRunner
from rulecraft.schemas import VerifierResult, pass_definition
from rulecraft.verifier import BasicVerifier

STABLE_KEY_PATTERN = re.compile(r"^[A-Z0-9_]+:[A-Z0-9_]+(:[A-Z0-9_]+)?$")


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
    if payload.get("verifier_outcome") == "UNKNOWN":
        assert payload.get("verifier_reason_codes")
    assert {
        "schema_version",
        "trace_id",
        "x_ref",
        "selected_rules",
        "run.mode",
        "verifier_id",
        "verifier_verdict",
        "verifier_outcome",
    }.issubset(payload.keys())


def test_t07_should_scale_defaults() -> None:
    router = BudgetRouter()
    fail_verifier = VerifierResult(
        schema_version="0.5.15",
        verifier_id="test",
        verdict="FAIL",
        outcome="FAIL",
    )
    assert router.decide_next_mode(fail_verifier, "main", 0) == "probe"

    unknown_i3 = VerifierResult(
        schema_version="0.5.15",
        verifier_id="test",
        verdict="PASS",
        outcome="UNKNOWN",
        reason_codes=["insufficient_evidence"],
    )
    assert router.decide_next_mode(unknown_i3, "main", 0) == "probe"


def test_t08_escalates_on_insufficient_evidence() -> None:
    path = Path("data") / "eventlog.jsonl"
    if path.exists():
        path.unlink()

    runner = RulecraftRunner(
        llm_adapter=EchoLLMAdapter(),
        verifier=BasicVerifier(),
        eventlog_path=path,
        max_attempts=2,
    )
    runner.run(
        prompt="check",
        context={"bucket_key": "I2|general|clarity_med"},
        constraints={"requires_external_check": True},
    )

    payload = json.loads(path.read_text(encoding="utf-8").strip().splitlines()[-1])
    assert payload["run.mode"] in {"probe", "tree", "full"}


def test_t09_no_escalation_on_schema_violation() -> None:
    path = Path("data") / "eventlog.jsonl"
    if path.exists():
        path.unlink()

    runner = RulecraftRunner(
        llm_adapter=EchoLLMAdapter(),
        verifier=BasicVerifier(),
        eventlog_path=path,
        max_attempts=2,
    )
    runner.run(
        prompt="bad json",
        context={"bucket_key": "I1|general|clarity_high"},
        constraints={"must_be_json": True},
    )

    payload = json.loads(path.read_text(encoding="utf-8").strip().splitlines()[-1])
    assert payload["run.mode"] == "main"
