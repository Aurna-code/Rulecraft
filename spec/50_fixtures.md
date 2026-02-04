# 50) Fixtures (Sample JSON)

## VerifierResult 예시
{
  "schema_version": "0.5.15",
  "verifier_id": "v_l1_only",
  "verdict": "PASS",
  "outcome": "UNKNOWN",
  "score": 0.55,
  "reason_codes": ["insufficient_evidence"],
  "violated_constraints": null
}

## EventLog 최소 예시(JSONL 한 줄)
{
  "schema_version": "0.5.15",
  "trace_id": "t_20260131_000001",
  "x_ref": "user:msg#123",
  "bucket_key": "I2|coding|clarity_med",
  "selected_rules": [{"rule_id":"r1","version":"0.1.0","type":"GuardrailRule"}],
  "run": {"mode": "main", "cfg": {"temperature": 0.2}},
  "verifier": {"verifier_id":"v_l1_only","verdict":"PASS","outcome":"UNKNOWN","reason_codes":["insufficient_evidence"]}
}
