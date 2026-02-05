# 30) Decision Tables

## D1. Verifier 합성 규칙(요약)
- L1 치명 위반 => verdict=FAIL (outcome은 L3가 있어도 FAIL 유지 가능)
- L3가 명확하면 outcome은 OK/FAIL로 확정(UNKNOWN 금지)
- L2는 점수/트리거용(최종 판결용으로 쓰지 않음)

## D2. should_scale 기본 규칙(무모델 Router)
입력: impact_level(I1/I2/I3), verdict/outcome, violated_constraints, reason_codes, cost

권장 결론:
- outcome==FAIL => should_scale = True (단, 포맷/정책 위반은 “수정 재시도”로 라우팅)
- outcome==UNKNOWN => impact가 높을수록 should_scale을 더 쉽게 True로
  - I3: 기본 True (추가 근거/L3/상위루트 권장)
  - I2: reason_codes에 insufficient_evidence/exec_unavailable 있으면 True
  - I1: 기본 False(비용 절약), 단 반복 클러스터면 True
- verdict==FAIL & violated_constraints != empty => should_scale = False가 아니라 “형식 수리 재시도”를 먼저
  (즉, scale은 ‘강한 모델’이 아니라 ‘올바른 루트’로 보내는 것)

## D3. CandidateSelect 최소 정책
- GuardrailRule은 먼저(system_guard/prepend)
- StrategyRule은 그 다음(prepend/inline)
- max_rules 준수
- allow_types 준수
- 탐색(exploration)은 로깅만 하고, MVP에서는 선택 점수에 반영하지 않아도 됨

## D4. Memory RECALL(Phase1) 최소 정책
1) Gather: ReasoningBank, Rulebook, ReuseBuffer(tactics), 최근 TraceCapsule
2) Filter:
   - bucket_key/intent_key 명백 불일치 제거
   - state_key 호환성(툴/모드/정책) 깨지면 제거
3) Rerank:
   S = w_sem*sim + w_int*sim(intent) + w_state*compat(state) + w_qual*quality
4) Return:
   - top-m MemoryHint
   - used_ids를 EventLog에 기록

## D5. Folding/Memory Actions(Phase2) 최소 정책
- end_of_run에서 FoldResult 생성(요약이 아니라 “재사용 단위 생성”)
- Plan -> Apply -> Record 3단계로 남긴다
- Rulebook active 승격은 금지(temporary draft까지만)
- 실패/충돌은 PRUNE보다 RETIRE 우선
