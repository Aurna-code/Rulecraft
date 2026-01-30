# Rulecraft Verifier 제작 사양 — r06

버전: r06  
작성일: 2026-01-26 (Asia/Seoul)
수정일: 2026-01-29 (Asia/Seoul)
패치: TongGeometry(GTS) — LLM 가이드 트리 서치(형식-검증 도메인) 이식
패치: NN-FT(2601.14453) — FlowMap 신호를 ‘추정기’로 확장하는 근거(옵션)

패치: Phase 2 — Folding + Memory Actions 신호/정합성 규율 추가
패치: Phase 3 — PRAXIS(조건부 전술) 신호 규율 추가
패치: hotfix09(원천) — InFi-Check FGFC(근거/오류타입/교정) 확장(`VerifierResult.fgfc`) 규격 추가
패치: hotfix12 — Patterning(데이터 개입) 입력 신호로서 reason_codes 안정성 규범 추가
패치: hotfix12p1 — Verifier/Router 무(無)모델 기본값 + 에스컬레이션 지표/트리거(관측 가능성) 추가

> 목적: Rulecraft의 `VerifierAdapter`를 “추정”이 아니라 **프로그래밍적 실체**로 만들기 위한 구현 스펙을 고정한다.  
> 반환 계약(SSOT): `Rulecraft_SSOT_0.5.15_ssot07_memory_phase3_hotfix12p1.md` 의 `VerifierResult`

---

## 0) TL;DR

- Verifier는 단일 모델 프롬프트가 아니라 **3층 합성(Compose)** 이 기본이다.
  - **L1 정적(필수)**: 스키마/형식/제약/툴콜 규칙 검증 (결정적)
  - **L2 의미(선택)**: 저비용 grader로 타당성/정합성 스코어링 (확률적)
  - **L3 실행(옵션, 강추)**: Sandbox/하네스로 실행·채점해서 outcome을 확정 (결정적)
- 약한 모델일수록 L2를 “믿음”으로 쓰지 말고, **L1+L3로 정답을 환경에서 뽑게** 만드는 편이 가성비가 좋다.

---

## 0.1) 모델 없는 기본값(권장) — “가벼운 미들웨어” 운영 규율

Rulecraft의 기본 목표는 **Verifier/Router를 별도 AI 모델 없이** 굴리는 것이다.  
즉, “판단”을 모델에게 떠넘기기보다 **결정적 신호(L1/L3) + 관측 가능 로그**로 운영을 안정화한다.

### 기본 프로파일(권장)
- **VerifierProfile: `v_l1_only`** (기본)
  - L1 정적 검증만 수행(스키마/제약/툴콜/금지 패턴)
  - `outcome=UNKNOWN`은 정상(=검증 불가)이며, PASS 정의(SSOT §5.1)로 운영한다
- **VerifierProfile: `v_l1+l3_exec`** (가능한 도메인)
  - L1 + L3 실행 검증(테스트/프로버/샌드박스)로 `outcome ∈ {OK, FAIL}`을 가능한 한 확정
- **L2 의미 검증은 기본 OFF**
  - 붙이더라도 “최종 판결”이 아니라 **선별/스케일링 트리거(should_scale)** 신호로만 쓴다
  - 초경량 1순위는 `score_method="rule_check"`(정규식/간단 함수/키 검사)이다

### Router/Policy도 “무(無)모델” 우선
- Router/BudgetRouter/should_scale은 기본적으로 **규칙 기반(결정적)** 으로 만든다.
- 입력 신호는 `EventLog + VerifierResult(reason_codes/violated_constraints/outcome) + cost`로 충분하다.

### “불가피해지면 가볍게 다는” 기준(에스컬레이션 지표)
아래 지표가 일정 기간(윈도우)에서 반복될 때만 L2(또는 더 강한 검증)를 고려한다.

- **UNKNOWN 과다**: `unknown_rate`가 높고, 그 원인이 `exec_unavailable_rate`/`sandbox_denied`가 아니라 “의미 검증 부재”로 보일 때
- **반복 FAIL 클러스터**: 동일 `failure_cluster_id`가 높은 빈도로 재발(=룰/포맷/툴 정책 개선이 더 급함)
- **근거 빈약 반복**: `insufficient_evidence_rate`가 높고, “L3로 확정할 수 없는 텍스트 태스크”가 병목일 때
- **컨텍스트 오염**: `memory_overinject` / `praxis_tactic_overinject` 같은 신호가 반복(=Router/주입 정책이 문제)
- **도메인 특화 판정 필요**: 예컨대 자연어 요약 품질 같은 “실행으로 확정 어려운” 영역에서만 제한적으로 L2를 붙인다

> 핵심: L2를 붙이기 전에, 먼저 L1(계약/형식/툴)과 L3(하네스/테스트)로 “확정 가능한 것”부터 확정한다.

## 1) 범위와 비범위

### 1.1 범위
- Runner가 호출 가능한 `VerifierAdapter.verify(...)`의 인터페이스/합성 규칙 정의
- L1/L2/L3의 역할 분해, verdict/outcome/score 산출 규칙 정의
- reason_codes/violated_constraints 최소 taxonomy 정의
- Sandbox(LLM-in-Sandbox) 연동 시 Verifier가 무엇을 확정해야 하는지 정의

### 1.2 비범위
- 특정 모델(예: GPT-계열/Claude/로컬)의 “최적 프롬프트”는 SSOT에 포함하지 않는다(프로파일 파일로 분리 권장).
- 도메인별 전문 평가(human eval)는 Rulecraft의 기본 Verifier 범위를 벗어난다(추가 Verifier로 붙일 수는 있음).

---

## 2) VerifierAdapter 인터페이스 (권장)

### 2.1 입력(권장 시그니처)
```python
class VerifierAdapter:
    def verify(
        self,
        *,
        trace_id: str,
        x_ref: str,
        candidate: object,              # y0 / synth 결과(텍스트 또는 tool-call 결과)
        context: dict,                  # impact_level/domain_tag/user_clarity 등
        constraints: dict | None = None,# 길이/포맷/툴 정책/금지사항 등
        artifacts: dict | None = None,  # sandbox 결과 파일/테스트 로그/요약 등
        meta: dict | None = None,       # model/meta/cost/rollout_select 등
    ) -> dict:  # VerifierResult
        ...
```

### 2.2 출력(반드시 지켜야 할 것)
- 반환은 **반드시** `Rulecraft_SSOT_0.5.15_ssot07_memory_phase3_hotfix12p1.md` 의 `VerifierResult` 형태여야 한다.
- 특히 아래 필드는 **MUST**:
  - `verifier_id`
  - `verdict ∈ {PASS, FAIL, PARTIAL}`
  - `outcome ∈ {OK, FAIL, UNKNOWN}`
- (옵션) 도큐먼트 기반/팩트 기반 검증에서는 `VerifierResult.fgfc`(SSOT의 FGFCReport)를 채워 **근거+오류타입+교정안**을 구조화해 남길 수 있다.

---

## 3) 1/2/3층 상세

## 3.1 L1: 정적 검증 (필수)

### 3.1.1 역할
- “모델이 아무리 말을 잘해도” 어길 수 있는 것들을 **결정적으로** 잡는다.
- 대표:
  - 구조화 출력 스키마 검증(JSON/YAML)
  - 길이/필드 누락/필수 키 누락
  - 금지 패턴(키/비밀/로그 유출, 룰 우회 지시, tool 권한 상승 등)
  - 툴콜 args 스키마(필수 인자 누락/타입 불일치)
  - 명시 제약(예: “숫자 근거 3개”, “출력은 표 금지”, “파일명 규칙”, “no web”) 위반

### 3.1.2 산출
- 위반이 있으면:
  - `violated_constraints`에 제약 id/태그를 넣는다.
  - `reason_codes`에 `format_leak`, `tool_misroute`, `constraint_violation` 같은 원인을 넣는다.
  - verdict는 원칙적으로 `FAIL` 또는 `PARTIAL` (운영 정책에 따라 다름)

---

## 3.2 L2: 의미 검증 (선택)

### 3.2.1 역할
- 텍스트 결과의 “타당성/정합성/근거 빈약/자기모순”을 확률적으로 잡는다.
- 약한 모델 환경에서는 L2를 “최종 판결”로 쓰지 말고, **승격 트리거**(should_scale)로 쓰는 게 안전하다.

### 3.2.2 구현 옵션(가벼운 순)
- **rule_check**: 규칙 기반(키워드/정규식/간단 함수)으로 신호만 만들기
- **yes_logit**: (가능하면) 짧은 질문에 대한 yes/no 확률을 score로 사용
- **pairwise_rank**: 여러 후보(rollouts/top-m)를 비교해 순위/선호도 산출
- **hybrid**: 위 신호들을 결합해서 score(0~1)로 맵핑

---

## 3.3 L3: 실행 검증 (옵션, 강력 추천)

### 3.3.1 역할
- “말로 검증이 안 되는 것”을 **실행/채점**으로 확정한다.
- 대표:
  - (형식-검증 가능한 도메인) **심볼릭 프로버/정리증명기 연동**: 증명 가능/불가능/미결을 outcome(OK/FAIL/UNKNOWN)으로 매핑
  - 코드/수식/데이터 처리: 테스트 하네스 실행, 정답 파일 생성/비교
  - 툴체인 작업: 파일 생성 여부, 명령 성공 여부, 메트릭 계산
  - 장문 컨텍스트 처리: sandbox에서 파일로 분리/요약/검증 후 결과만 반영

### 3.3.2 산출 규칙(중요)
- 실행 하네스가 PASS/FAIL을 명확히 주면:
  - `outcome`은 **OK/FAIL로 확정**한다(UNKNOWN 금지).
  - verdict는 보통 outcome을 따른다(단, L1에서 치명 위반이면 FAIL 유지).
- 실행이 불가능(타임아웃/권한/환경 미지원)이면:
  - `outcome=UNKNOWN` + `reason_codes`에 `sandbox_timeout|sandbox_denied|exec_unavailable` 중 하나를 남긴다.

---

## 4) 합성 규칙 (L1/L2/L3 → VerifierResult)

### 4.1 우선순위(권장)
1) **L1 치명 위반**(보안/권한/포맷 필수) → verdict=FAIL (outcome은 L3가 확정했더라도 FAIL 유지 가능)
2) L3 실행 결과가 있으면 → outcome 확정(OK/FAIL)
3) L2는 (a) score 산출, (b) PARTIAL/UNKNOWN 트리거, (c) 후보 선별(top-m) 신호로 사용

### 4.2 verdict/outcome 기본 매핑(권장)
- **PASS**: (L1 pass) AND (L3 없거나 OK) AND (L2가 큰 경고를 내지 않음)
- **FAIL**: (L1 치명 위반) OR (L3 outcome=FAIL) OR (L2가 강한 FAIL 신호)
- **PARTIAL**: L1은 통과했지만, L2/L3가 애매하거나 일부 제약만 위반한 경우

- **outcome=OK**: 실행/근거가 충분해 “맞음”을 확인했거나, 검증이 명확한 경우
- **outcome=FAIL**: 실행/근거로 “틀림”이 확인된 경우
- **outcome=UNKNOWN**: 검증 불가(정보 부족/실행 불가/근거 빈약) 상태

> 주의: `outcome=UNKNOWN`은 “틀림”이 아니라 “확정 불가”다. L1이 통과했고 치명 경고가 없으면, **`verdict=PASS + outcome=UNKNOWN`을 허용**해서 Runner가 결과 출력을 막지 않게 한다.
> FAIL은 (a) L1 치명 위반, (b) L3로 오답 확정(outcome=FAIL), (c) L2가 강한 FAIL 신호를 낸 경우로 좁게 유지하는 게 운영 안정성이 좋다.

> 시스템 PASS 정의는 `PASS iff (verdict==PASS) AND (outcome!=FAIL)` 를 사용한다(Playbook/Addendum의 정의 유지).

### 4.3 score(0~1) 권장 규칙
- score는 “최종 신뢰도”가 아니라 **선별/스케일링/정책 입력**이다.
- 권장:
  - L3가 명확 PASS면 score=1에 가깝게 캡(예: 0.95~1.0)
  - L3 FAIL이면 score=0에 가깝게 캡
  - L3 없으면 L2 score를 사용하되, L1 경미 위반이 있으면 penalty 적용



### 4.4 노이즈/비결정성 처리 규율(권장)

LongCat-Flash-Thinking-2601의 “노이즈 분해” 관점(환경/툴이 완전하지 않다는 전제)을 Rulecraft에 가져오면, Verifier는 아래를 **일관되게** 처리해야 한다.

- **툴 실패/부분 성공**
  - 툴 실행 실패/타임아웃이면: `reason_codes += tool_failure|tool_timeout`, 필요 시 `violated_constraints += TOOL:EXEC_FAILED|TOOL:EXEC_TIMEOUT`
  - 부분 성공이면: `reason_codes += partial_success`, 결과는 “가능한 범위”로만 반영(과신 금지)
- **툴 출력 불량**
  - 출력 스키마 위반이면: `reason_codes += tool_output_invalid`, `violated_constraints += TOOL:OUTPUT_INVALID`
  - 동일 조건 재실행 상충이면: `reason_codes += tool_output_inconsistent`
- **환경(샌드박스/테스트) 플래키**
  - 동일 입력/시드에서 결과가 흔들리면: `reason_codes += env_nondeterminism`, `outcome=UNKNOWN`을 기본으로 두고
    Runner에 “재현성 확보(시드 고정/반복 실행/환경 핀)” 또는 “상위 검증 경로”로 승격 신호를 준다.
- **재시도 복구**
  - 1회 재시도로 정상화되면: `reason_codes += retry_recovered`
  - 단, high impact에서는 `PASS/OK`로 끝내지 말고(정책에 따라) 추가 검증/재현성 체크를 권장한다.

> 원칙: “노이즈를 숨기지 않는다.”  
> Verifier는 불확실을 `UNKNOWN`으로 남기고, Runner가 `should_scale/EnvSuite/회귀`로 해결하게 만드는 쪽이 운영 안정성이 높다.


---

## 5) reason_codes & violated_constraints (최소 taxonomy)

### 5.1 reason_codes(권장 최소)
- `format_leak` (포맷 밖 텍스트/구조 누수)
- `constraint_violation` (명시 제약 위반)
- `insufficient_evidence` (근거 부족)
- `instruction_conflict` (지시 상충)
- `tool_misroute` (툴 종류/시점/순서/args 오류)
- `tool_failure` (툴 실행 실패: 권한/리밋/서버 오류 등)
- `tool_timeout` (툴 타임아웃/장시간 지연)
- `tool_output_invalid` (툴 출력이 스키마/형식 위반)
- `tool_output_inconsistent` (동일 조건 재실행 시 출력 상충)
- `partial_success` (일부 단계 성공, 일부 실패)
- `truncation_or_cutoff` (출력 잘림/중단 의심)
- `numeric_error` (계산/수치 오류 의심)
- `self_inconsistency` (자기모순/상충 진술)

- (옵션, FGFC) `fact_predicate_mismatch` / `fact_entity_mismatch` / `fact_circumstance_mismatch`
- (옵션, FGFC) `fact_coreference_mismatch` / `fact_discourse_link_mismatch` / `fact_extrinsic_claim`
- (옵션, FGFC) `fact_refuted` / `fact_supported` / `fact_not_enough_info`  (unit 단위 verdict 집계용)

- `env_nondeterminism` (실행/채점이 비결정적·플래키)
- `search_budget_exhausted` (트리/탐색 예산 소진으로 결론 미확정)
- `prover_incomplete` (프로버/하네스가 불완전: UNKNOWN 유지)
- `proof_not_found` (증명/해결 실패: outcome=FAIL로 확정한 경우)
- `retry_recovered` (재시도로 복구 성공: 신뢰도 penalty 신호)
- `sandbox_timeout` / `sandbox_denied` / `exec_unavailable` (실행 검증 실패 원인)
- `test_fail` (하네스/테스트 실패로 명확한 오답)
- (옵션, Phase 2/3) `memory_recall_miss` / `memory_overinject` / `memory_conflict` / `memory_stale` / `memory_poison_risk` (메모리 주입/리콜/PRAXIS 조건부 전술 관련 신호)
- (옵션, Phase 3) `praxis_tactic_mismatch` / `praxis_tactic_overinject` / `praxis_tactic_conflict` (조건부 전술 특화 신호; 위 memory_*로도 충분하면 생략 가능)

### 5.2 violated_constraints(권장 형태)
- 문자열 id로 기록(예: `SCHEMA:VerifierResult`, `POLICY:NO_NETWORK`, `FORMAT:JSON_ONLY`, `TOOL:CALL_REQUIRED:web.search_query`)
- 운영에서 중요한 건 “사유의 텍스트”보다 **집계 가능한 키**다(FlowMap/Regression에 사용).

#### 5.2.1 안정성 규율(권장)
- `violated_constraints`에 들어가는 키는 **taxonomy.py에 등록된 집합**(또는 동일한 하드코딩 목록)에서만 선택한다.
- 자유 서술 텍스트를 넣지 않는다(집계 불가 + 회귀 불가).
- 키 체계 변경이 필요하면: (1) taxonomy 버전 업, (2) 집계/회귀 코드 동시 업데이트, (3) `failure_cluster_id` 리매핑을 같이 수행한다.
- `failure_cluster_id`는 아래 규칙으로 **결정적으로(deterministic)** 생성하는 것을 권장한다.
  - 입력: `sorted(reason_codes)`, `sorted(violated_constraints)`, `stage_tag`(예: `main|verify`, `synth|verify`, `tree|verify`)
  - 생성: `sha1("rc=" + ",".join(rc) + "|vc=" + ",".join(vc) + "|st=" + stage_tag)`의 hex digest
  - 목적: 로그 집계/회귀팩/우선순위 자동화를 위해 “같은 실패는 같은 키”로 묶는다.


---



### 5.2.2 FGFC error_type taxonomy (InFi-Check 호환, 권장)

FGFC 모드에서는 `fgfc.units[*].error_type`을 아래 값 중 하나로 기록한다.

- `PredE`: predicate/관계 오류
- `EntE`: entity 오류
- `CircE`: 시간/장소/수치 등 circumstance 오류
- `CorefE`: 지시/대명사 등 co-reference 오류
- `LinkE`: 인과/시간/담화(disourse) 링크 오류
- `OutE`: 문서 밖(extrinsic) 정보 주입

권장 매핑(집계/루프용):
- PredE → `fact_predicate_mismatch`
- EntE  → `fact_entity_mismatch`
- CircE → `fact_circumstance_mismatch`
- CorefE→ `fact_coreference_mismatch`
- LinkE → `fact_discourse_link_mismatch`
- OutE  → `fact_extrinsic_claim`

주의:
- `violated_constraints`는 “정적 규칙 위반”이고, FGFC는 “의미/사실 오류”에 가깝다. 섞지 말고 각각의 채널로 남겨라.


## 5.3 Memory RECALL(Phase 1)용 상태 신호 규율

Rulecraft Phase 1에서는 RECALL의 `state_key`/호환성 판단에 Verifier 신호를 쓴다(SSOT §4.3~§4.4).  
그래서 Verifier는 “그때그때 기분”으로 reason_codes를 바꾸면 안 된다.

권장 규칙:

- **reason_codes는 “작고 안정적인 카테고리”로 유지**(세부는 notes로)
- 최소한 아래 축은 지속적으로 분리되게 유지:
  - `format/*` (스키마/형식/출력 요구 위반)
  - `constraint/*` (명시 제약 위반)
  - `tool/*` (툴 사용 규칙/순서/권한 위반)
  - `evidence/*` (근거/인용/출처 부족)
  - `logic/*` (모순/연역 오류/수학 오류 등)
  - `execution/*` (샌드박스/하네스 실행 실패/불일치)
  - `uncertainty/*` (검증불가/불충분)

RECALL 쪽에서의 사용 예:
- 최근 런이 `tool/*`로 자주 실패하면 “tool-heavy 전술”을 우선 리콜하거나, 반대로 같은 전술


## 5.4 Folding + Memory Actions(Phase 2)용 신호 규율 (권장)

Phase 2는 Verifier를 “채점기”로만 쓰지 않고, **메모리 운영 자동화의 센서**로도 사용한다.
따라서 아래 신호는 가능한 한 **작고 안정적인 키**로 reason_codes/violated_constraints에 남긴다.

권장 reason_codes(옵션):
- `memory_recall_miss`: RECALL로 가져온 힌트/전술이 실제로 도움이 안 됨(또는 부적합)
- `memory_overinject`: 힌트 과다로 컨텍스트 오염/길이 압박/혼란 유발
- `memory_conflict`: 복수 힌트/전술이 상충
- `memory_stale`: 오래된 전술/룰이 현재 state_key와 부적합
- `memory_poison_risk`: 반복 실패/위반을 유발하는 후보(RETIRE/PRUNE 후보)

권장 violated_constraints 키(예시):
- `MEMORY:RECALL_MISS`
- `MEMORY:OVERINJECT`
- `MEMORY:CONFLICT`
- `MEMORY:STALE`
- `MEMORY:POISON_RISK`

사용 방식(권장):
- Folding 트리거 중 `fail_cluster`는 위 키들의 반복을 집계해 발동할 수 있다.
- MemoryActionPlanner는 위 신호를 이용해 `RETIRE`/`PIN`/`MERGE`/`PRUNE`의 우선순위를 조정한다.
- 키는 §5.2.1 안정성 규율을 따른다(새 키 추가는 “천천히”, 기존 키 의미 변경 금지).

을 페널티 처리
- `format/*`이 반복되면 출력 스키마 관련 룰/에피소드(템플릿)를 우선 리콜

즉, Verifier taxonomy는 이제 **관측 가능성 + 메모리 라우팅 신호**다. 잘 정의해두면 시스템이 알아서 개선 루프를 돈다.



## 5.5 Patterning(데이터 개입) 지원 규범(옵션)

Patterning(arXiv:2601.13548)은 “원하는 행동/일반화”를 만들기 위해 **어떤 데이터 슬라이스를 얼마나 섞을지**를 역으로 푸는 접근이다.
Rulecraft에선 이를 **Distiller/CounterexampleGenerator의 데이터 믹싱**에 적용할 수 있고, 이때 `reason_codes`는 관측치(Observable)의 핵심 입력이 된다.

따라서 Verifier는 아래 규범을 **SHOULD** 지킨다.

- `reason_codes` taxonomy는 **자주 바꾸지 않는다.** (시간축 비교가 깨지면 χ 추정이 무의미해진다.)
- `reason_codes`는 “현상”이 아니라 **원인/개입 레버** 중심으로 정의한다.  
  예: `format_leak`, `tool_misroute`, `missing_constraint`, `hallucinated_fact` 처럼 *데이터/룰/라우팅으로 고칠 수 있는 단위*.
- Verifier는 reason_code를 과잉 생성하지 말고 **지배적인 1~3개**만 반환한다.
- 새로운 code를 추가할 때는 기존 code와 **상호배타성/우선순위**를 명시한다(다중 라벨이면 최소한 순서를 고정).
- `violated_constraints`는 “어떤 계약이 깨졌는지”를 가리키는 **결정적 키**로 유지한다(자동 회귀/게이트 입력).

---


## 6) 제작 사양(코드 구조 권장)

### 6.1 모듈 구조(권장)
```
src/rulecraft/verifier/
  base.py              # VerifierAdapter 인터페이스
  l1_static.py         # schema/constraints/tool-policy validators
  l2_grader.py         # LLM grader / hybrid scoring
  l3_exec.py           # sandbox harness integration
  compose.py           # 합성(aggregation) 로직
  taxonomy.py          # reason_codes / constraint ids
```

### 6.2 최소 의존성(예시)
- L1: `jsonschema`, `pydantic`(또는 자체 validator), `re`
- L3: sandbox runner(Docker/프로세스), timeout/cgroup(가능하면), 파일 경로 정책

### 6.3 캐시/재현성(권장)
- 같은 입력(x_ref) + 같은 후보(y_ref/hash)에 대해 verifier 결과를 캐시할 수 있다(비용 절감).
- 캐시 키에는 `verifier_id`와 `schema_version`을 포함해야 한다(SSOT 변경 시 무효화).

---

## 7) MVP 제작 체크리스트(현실 버전)

- [ ] L1: 출력 포맷(JSON/YAML) + 필수 키 + 금지 패턴 + 길이 제한 검증
- [ ] L1: `violated_constraints`/`reason_codes`를 키 기반으로 남김
- [ ] L2: (선택) cheap grader 1개(로컬 or API 보험)만 붙여 score 산출
- [ ] L3: (선택) 최소 하네스 1개(예: 파이썬 테스트 실행)로 outcome 확정
- [ ] 합성: L1/L2/L3 우선순위 규칙을 compose.py에 고정
- [ ] 로그: EventLog에 verifier verdict/outcome/score를 미러링(FlowMap용)