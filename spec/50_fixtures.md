# Fixtures (SSOT v0.5.15, Flat EventLog)

fixtures/는 contracts 기준으로 고정된 **플랫 EventLog** 예시를 제공한다.

## EventLog 예시 (Flat)

```json
{
  "schema_version": "0.5.15",
  "trace_id": "trace_minimal_pass",
  "bucket_key": "I1|general|clarity_high",
  "x_ref": "hello",
  "run": {"mode": "main"},
  "selected_rules": [
    {"rule_id": "default_general", "version": "0.1", "type": "policy"}
  ],
  "pass_value": 1,
  "verifier_id": "basic_l1",
  "verifier_verdict": "PASS",
  "verifier_outcome": "OK",
  "verifier_reason_codes": []
}
```

## VerifierResult 예시

```json
{
  "schema_version": "0.5.15",
  "verifier_id": "basic_l1",
  "verdict": "FAIL",
  "outcome": "FAIL",
  "reason_codes": ["schema_violation"],
  "violated_constraints": ["FORMAT:JSON_ONLY"]
}
```

## Run Mode 정책
- 저장 형식(JSONL)은 `run.mode` 같은 dotted key를 사용하지 않는다.
- 내부 파이썬 표현은 `run_mode`를 사용하며, 직렬화 레이어에서만 `run: {mode}`로 변환한다.
