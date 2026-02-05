# 40) Acceptance Tests (MVP Gate)

테스트는 “기능”이 아니라 “규율”을 고정한다.
아래를 pytest로 구현하고, CI에서 반드시 돌린다.

## T01 PASS 정의 고정
- 입력: (verdict=PASS,outcome=OK) => PASS True
- 입력: (verdict=PASS,outcome=UNKNOWN) => PASS True
- 입력: (verdict=PASS,outcome=FAIL) => PASS False
- 입력: (verdict=FAIL,outcome=OK) => PASS False

## T02 violated_constraints 안정 키 검사
- violated_constraints 항목은 공백/장문/문장형이면 FAIL
- 패턴 예: ^[A-Z0-9_]+:[A-Z0-9_]+(:[A-Z0-9_]+)?$

## T03 UNKNOWN은 reason_codes 없이 나오면 FAIL
- outcome=UNKNOWN이면 reason_codes는 최소 1개 있어야 함

## T04 EventLog JSONL append
- run 1회 실행 시 eventlog.jsonl에 1줄 append
- 필수 키: schema_version, trace_id, x_ref, selected_rules, run.mode, verifier.verdict/outcome

## T05 CandidateSelect 정책
- max_rules 준수
- allow_types 준수
- GuardrailRule이 있으면 selected_rules의 앞쪽에 온다(정책 옵션으로 완화 가능하나 기본은 고정)

## T06 Memory 주입 예산
- (룰 제외) 주입 총합이 상한을 넘으면 잘라서 주입해야 함
- 잘린 경우 reason_codes에 memory_overinject 또는 praxis_tactic_overinject 기록

## T07 should_scale 규칙(기본 Router)
- I3 + outcome UNKNOWN => should_scale True
- I1 + outcome UNKNOWN + 이유 없음 => should_scale False
- outcome FAIL => should_scale True (단, format/policy 위반은 'repair route'로 우선 라우팅)
