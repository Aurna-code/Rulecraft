import json
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_DIR = ROOT / "contracts"
FIXTURES_DIR = ROOT / "fixtures"


def load_schema(name: str) -> dict:
    return json.loads((CONTRACTS_DIR / name).read_text(encoding="utf-8"))


def validate_fixture(path: Path, schema: dict) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    try:
        jsonschema.validate(payload, schema)
    except jsonschema.ValidationError as exc:
        raise AssertionError(f"{path.name}: {exc}") from exc


def test_fixtures_validate_schema() -> None:
    eventlog_schema = load_schema("eventlog.schema.json")
    verifier_schema = load_schema("verifier_result.schema.json")
    fgfc_schema = load_schema("fgfc_report.schema.json")

    for fixture_path in FIXTURES_DIR.glob("eventlog_*.json"):
        validate_fixture(fixture_path, eventlog_schema)

    for fixture_path in FIXTURES_DIR.glob("verifier_result_*.json"):
        validate_fixture(fixture_path, verifier_schema)

    for fixture_path in FIXTURES_DIR.glob("fgfc_report_*.json"):
        validate_fixture(fixture_path, fgfc_schema)
