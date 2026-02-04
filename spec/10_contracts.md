# 10) Contracts (Schemas)

## 공통 규칙
- 모든 레코드는 schema_version MUST 포함 (값은 "0.5.15")
- *_id는 전역 유일 MUST
- EventLog는 trace_id를 중심으로 TraceCapsule/기타 저장소와 조인 가능해야 함

---

## 1) RuleRecord (Rulebook 저장 단위)
필수 필드:
- rule_id: string
- version: string
- type: "StrategyRule" | "GuardrailRule"
- status: "temporary" | "active" | "retired"
- body: string
- applicability: {domain_tag?, task_family?, predicates?, bucket_keys?}
- priority: {guardrail_first: bool, rank?}
- evidence: {trace_ids?, verifier_ids?, regression_ids?}
- tests: {regression_tests: [string], counterexample_tests: [string]}
- metrics: {utility_q_ema?, pass_p_hat?, pass_p_lb95?, pass_p_K?, pass_p_bucket?, pass_p_bucket_delta?}
- lifecycle?: {created_at?, updated_at?, last_used_at?, retire_candidate?}

규율:
- GuardrailRule은 guardrail_first=true 권장
- active 승격은 tests 게이트 통과 전엔 금지(temporary 유지)

---

## 2) CandidateSelectRequest / Response
CandidateSelectRequest:
- request_id, x_ref MUST
- constraints: {max_rules:int, allow_types:[...]} MUST
- bucket_key/context는 SHOULD

CandidateSelectResponse:
- selected_rules[] MUST
  - rule_id, version, type, injection_mode MUST
  - injection_mode: "prepend"|"inline"|"system_guard"
  - score/reasons는 optional

규율:
- max_rules 초과 금지
- allow_types 밖의 type 선택 금지
- GuardrailRule은 system_guard 또는 prepend 우선(정책으로 고정 가능)

---

## 3) VerifierResult (반드시 이 형태로 반환)
필수:
- verifier_id: string
- verdict: "PASS"|"FAIL"|"PARTIAL"
- outcome: "OK"|"FAIL"|"UNKNOWN"

권장/옵션:
- score: 0..1 (스케일링/선별 신호)
- reason_codes: [string] (FAIL/PARTIAL이면 최소 1개 권장)
- violated_constraints: [string] (자유서술 금지, 안정 키)
- failure_cluster_id?: string
- fgfc?: object (optional extension)

---

## 4) PASS (derived semantic)
PASS := (verdict=="PASS") AND (outcome!="FAIL")

주의:
- verdict PASS여도 outcome FAIL이면 pass=0

---

## 5) EventLog (JSONL로 append 저장)
필수:
- trace_id: string
- x_ref: string
- selected_rules[] (CandidateSelectResponse의 일부 미러)
- run.mode: "main"|"sot"|"matts"|"kroll"|"synth"|"tree"
- verifier: VerifierResult (최소한 미러 필드 저장)

권장:
- bucket_key: "I{1|2|3}|{domain}|clarity_{low|med|high}" 형태
- memory_recall / memory_fold / memory_actions / praxis 등 확장 필드는 optional로 유지

규율:
- EventLog는 집계 가능한 필드만 넣고, 상세는 TraceCapsule에 넣는 구조를 유지
