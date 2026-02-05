import json
from pathlib import Path

import jsonschema

from rulecraft.adapters import EchoLLMAdapter
from rulecraft.runner import RulecraftRunner
from rulecraft.verifier import BasicVerifier


def test_runner_emits_valid_eventlog(tmp_path: Path) -> None:
    output_path = tmp_path / "eventlog.jsonl"
    runner = RulecraftRunner(
        llm_adapter=EchoLLMAdapter(),
        verifier=BasicVerifier(),
        eventlog_path=output_path,
    )
    runner.run(prompt="hello", context={"bucket_key": "I1|general|clarity_high"})

    assert output_path.exists()
    line = output_path.read_text(encoding="utf-8").strip().splitlines()[0]
    payload = json.loads(line)
    schema = json.loads(Path("contracts/eventlog.schema.json").read_text(encoding="utf-8"))

    try:
        jsonschema.validate(payload, schema)
    except jsonschema.ValidationError as exc:
        raise AssertionError(f"eventlog schema validation failed: {exc}") from exc
