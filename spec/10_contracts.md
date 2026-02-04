# Contracts (SSOT v0.5.15, Flat EventLog)

이 문서는 contracts/fixtures에서 확정한 **플랫 EventLog 우주**를 SSOT로 고정한다.
MVP 단계에서는 nested verifier 객체나 selected_rules 객체 배열을 **사용하지 않는다**.

## EventLog (Flat, MVP)

### 핵심 원칙
- EventLog는 **플랫 필드**로 저장한다.
- `verifier_*` 필드는 VerifierResult의 핵심 값을 **평탄화(flat)** 한 것이다.
- `selected_rules`는 **rule_id 문자열 배열**로 최소 형태만 사용한다.
- nested verifier 객체 / selected_rules 객체 배열은 **향후 확장 가능**하나, MVP에서는 **flat**을 고정한다.

### 필드 정의 (MUST)
- `schema_version`: 문자열, 반드시 "0.5.15"
- `trace_id`: 문자열 (비어 있으면 안 됨)
- `bucket_key`: 문자열 (비어 있으면 안 됨)
- `x_ref`: 문자열 (원문 prompt)
- `run.mode`: 문자열 enum {"main","tree","probe","full"}
- `selected_rules`: string[] (rule_id 목록, 비어 있어도 됨)
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

## Dotted Key 정책

- JSONL 저장 시에는 dotted key(`run.mode`)를 **허용/사용**한다.
- 파이썬 내부 표현은 `run_mode` 같은 정상 필드명을 사용한다.
- 직렬화/역직렬화 레이어에서만 dotted key로 변환한다.
- contracts가 dotted key를 강제하는 경우, **mapper 함수**로 내부 ↔ 저장 표현을 변환한다.
