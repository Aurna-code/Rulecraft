import json
from pathlib import Path

from rulecraft.schemas import VerifierResult, pass_definition

ROOT = Path(__file__).resolve().parents[2]
FIXTURES_DIR = ROOT / "fixtures"


def assert_type(value, expected_types) -> None:
    if not isinstance(value, expected_types):
        raise AssertionError(f"Expected {expected_types}, got {type(value)}")


def validate_fgfc_report(payload: dict) -> None:
    assert "items" in payload
    assert_type(payload["items"], list)
    for item in payload["items"]:
        assert_type(item, dict)
        assert "claim" in item
        assert "evidence" in item
        assert item["claim"]
        assert_type(item["evidence"], list)
        for evidence in item["evidence"]:
            assert evidence
        if "error_type" in item and item["error_type"] is not None:
            assert item["error_type"]
        if "correction" in item and item["correction"] is not None:
            assert item["correction"]


def validate_verifier_result(payload: dict) -> None:
    required = ["schema_version", "verifier_id", "verdict", "outcome"]
    for key in required:
        assert key in payload

    assert payload["schema_version"] == "0.5.15"
    assert payload["verifier_id"].strip()
    assert payload["verdict"] in {"PASS", "FAIL", "PARTIAL"}
    assert payload["outcome"] in {"OK", "FAIL", "UNKNOWN"}

    if "score" in payload and payload["score"] is not None:
        assert 0 <= payload["score"] <= 1
    if "reason_codes" in payload:
        assert_type(payload["reason_codes"], list)
    if "violated_constraints" in payload:
        assert_type(payload["violated_constraints"], list)
    if "fgfc" in payload and payload["fgfc"] is not None:
        validate_fgfc_report(payload["fgfc"])
    if "failure_cluster_id" in payload and payload["failure_cluster_id"] is not None:
        assert payload["failure_cluster_id"].strip()


def validate_eventlog(payload: dict) -> None:
    required = [
        "schema_version",
        "trace_id",
        "bucket_key",
        "verifier",
        "x_ref",
        "run.mode",
        "selected_rules",
        "pass_value",
    ]
    for key in required:
        assert key in payload

    assert payload["schema_version"] == "0.5.15"
    assert payload["trace_id"].strip()
    assert payload["bucket_key"].strip()
    assert payload["x_ref"].strip()
    assert payload["run.mode"] in {"main", "tree", "probe", "full"}
    assert payload["pass_value"] in {0, 1}

    if "intent_key" in payload and payload["intent_key"] is not None:
        assert payload["intent_key"].strip()
    if "state_key" in payload and payload["state_key"] is not None:
        assert payload["state_key"].strip()
    if "verdict" in payload:
        assert payload["verdict"] in {"PASS", "FAIL", "PARTIAL"}
    if "outcome" in payload:
        assert payload["outcome"] in {"OK", "FAIL", "UNKNOWN"}

    assert_type(payload["selected_rules"], list)
    for rule in payload["selected_rules"]:
        assert rule.strip()

    verifier = payload["verifier"]
    assert_type(verifier, dict)
    assert verifier["verifier_id"].strip()
    assert verifier["verdict"] in {"PASS", "FAIL", "PARTIAL"}
    assert verifier["outcome"] in {"OK", "FAIL", "UNKNOWN"}
    if "reason_codes" in verifier:
        assert_type(verifier["reason_codes"], list)
    if "violated_constraints" in verifier:
        assert_type(verifier["violated_constraints"], list)

    if "memory_recall_used_ids" in payload:
        assert_type(payload["memory_recall_used_ids"], list)
        for item in payload["memory_recall_used_ids"]:
            assert item.strip()


def test_fixtures_validate_against_schemas() -> None:
    for fixture_path in FIXTURES_DIR.glob("eventlog_*.json"):
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        validate_eventlog(payload)

    for fixture_path in FIXTURES_DIR.glob("verifier_result_*.json"):
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        validate_verifier_result(payload)


def test_pass_definition_truth_table() -> None:
    truth_cases = [
        ("PASS", "OK", True),
        ("PASS", "UNKNOWN", True),
        ("PASS", "FAIL", False),
        ("FAIL", "OK", False),
        ("FAIL", "UNKNOWN", False),
        ("FAIL", "FAIL", False),
        ("PARTIAL", "OK", False),
        ("PARTIAL", "UNKNOWN", False),
        ("PARTIAL", "FAIL", False),
    ]
    for verdict, outcome, expected in truth_cases:
        verifier = VerifierResult(
            schema_version="0.5.15",
            verifier_id="test",
            verdict=verdict,
            outcome=outcome,
        )
        assert pass_definition(verifier) is expected


def test_invariant_pass_false_on_fail_outcome() -> None:
    verifier = VerifierResult(
        schema_version="0.5.15",
        verifier_id="test",
        verdict="PASS",
        outcome="FAIL",
    )
    assert pass_definition(verifier) is False


def test_invariant_non_empty_ids() -> None:
    for fixture_path in FIXTURES_DIR.glob("*.json"):
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        if "trace_id" in payload:
            assert payload["trace_id"].strip()
        if "verifier_id" in payload:
            assert payload["verifier_id"].strip()
        if "verifier" in payload:
            assert payload["verifier"]["verifier_id"].strip()

        if fixture_path.name.startswith("eventlog_"):
            validate_eventlog(payload)
        if fixture_path.name.startswith("verifier_result_"):
            validate_verifier_result(payload)
