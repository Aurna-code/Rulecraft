# 20) Global Invariants (Non-negotiable)

## I1. PASS 정의 불변
PASS := (verdict=="PASS") AND (outcome!="FAIL")

## I2. violated_constraints는 안정 키
자유서술 금지. 키 형태 예:
- SCHEMA:VerifierResult
- FORMAT:JSON_ONLY
- TOOL:CALL_REQUIRED:web.search_query
- POLICY:NO_NETWORK
- TOOL:EXEC_TIMEOUT
- TOOL:OUTPUT_INVALID

## I3. UNKNOWN을 숨기지 않는다
- 검증 불가/실행 불가/근거 부족이면 outcome=UNKNOWN을 유지해야 한다.
- reason_codes에 최소 1개를 남긴다:
  - insufficient_evidence | exec_unavailable | sandbox_denied | sandbox_timeout | tool_timeout ...

## I4. Verifier 기본은 무모델 (L1-only)
- L2(의미 grader)는 기본 OFF
- L3(실행 검증)는 가능하면 ON (가능 도메인에 한해)

## I5. Router/BudgetRouter도 무모델
- should_scale은 규칙 기반 계산이어야 한다.
- 입력은 EventLog + VerifierResult + cost면 충분해야 한다.

## I6. Rule vs PRAXIS 분리
- Conditional tactics(ReuseBuffer.tactic_entries)는 Rulebook 룰이 아니다.
- active 승격/강제 적용/룰 lifecycle과 혼동 금지.

## I7. 메모리 주입 예산 강제
- MemoryHint.summary <= 120 tokens (또는 600 chars)
- ConditionalTactic injection <= 160 tokens (또는 800 chars)
- (룰 제외) 총 주입 <= 256 tokens
초과는 잘라서 주입하고, reason_codes에 memory_overinject 또는 praxis_tactic_overinject 기록.

## I8. 재현 가능성
- EventLog는 JSONL append로 남긴다(런마다 1줄).
- trace_id로 TraceCapsule/아티팩트 조인이 가능해야 한다.
