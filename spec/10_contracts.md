# Contracts (SSOT v0.5.15, Flat EventLog)

이 문서는 contracts/fixtures에서 확정한 **플랫 EventLog 우주**를 SSOT로 고정한다.
MVP 단계에서는 nested verifier 객체나 selected_rules 객체 배열을 **사용하지 않는다**.

## EventLog (Flat, MVP)

### 핵심 원칙
- EventLog는 **플랫 필드**로 저장한다.
- `verifier_*` 필드는 VerifierResult의 핵심 값을 **평탄화(flat)** 한 것이다.
- `selected_rules`는 **{rule_id, version, type} 객체 배열**로 최소 형태만 사용한다.
- nested verifier 객체 / selected_rules 객체 배열은 **향후 확장 가능**하나, MVP에서는 **flat**을 고정한다.

### 필드 정의 (MUST)
- `schema_version`: 문자열, 반드시 "0.5.15"
- `trace_id`: 문자열 (비어 있으면 안 됨)
- `bucket_key`: 문자열 (비어 있으면 안 됨)
- `x_ref`: 문자열 (원문 prompt)
- `run`: 객체 { mode }
- `selected_rules`: {rule_id, version, type} 객체 배열 (비어 있어도 됨)
- `pass_value`: 0 또는 1
- `verifier_id`: 문자열 (비어 있으면 안 됨)
- `verifier_verdict`: 문자열 enum {"PASS","FAIL","PARTIAL"}
- `verifier_outcome`: 문자열 enum {"OK","FAIL","UNKNOWN"}

### 필드 정의 (SHOULD/MAY)
- `verifier_reason_codes`: string[] (SHOULD)
- `verifier_violated_constraints`: string[] (SHOULD)
- `intent_key`: string | null (SHOULD)
- `state_key`: string | null (SHOULD)
- `memory_recall_used_ids`: string[] (MAY)
- `cost_profile`: object | null (MAY)

## VerifierResult

- VerifierResult는 contracts/verifier_result.schema.json에 정의한다.
- EventLog는 VerifierResult의 핵심 값을 `verifier_*`로 **평탄화**하여 기록한다.

## Run Mode 정책

- 저장 형식(JSONL)은 `run.mode` 같은 dotted key를 사용하지 않는다.
- 내부 표현은 `run_mode`를 사용하고, 직렬화 레이어에서만 `run: {mode}`로 변환한다.
