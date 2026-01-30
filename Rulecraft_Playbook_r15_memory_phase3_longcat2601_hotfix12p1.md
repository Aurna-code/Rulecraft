# Rulecraft LLM Binding Playbook (Consolidated Session Notes) — r15

버전: r15  
작성일: 2026-01-23 (Asia/Seoul)


수정일: 2026-01-29 (Asia/Seoul)
패치: TongGeometry(GTS) — LLM 가이드 트리 서치(형식-검증 도메인) 이식
패치: NN-FT(2601.14453) — FlowMap Neural Field Estimator(옵션)

패치: Phase 1 — intent/state 기반 Memory RECALL(필터→리랭크) 실행 흐름 반영
패치: Phase 2 — Folding + Memory Actions(Plan→Apply→Record) 실행 흐름 반영
패치: Phase 3 — PRAXIS: ReuseBuffer 조건부 전술(conditional tactics) 운용 반영
패치: LongCat-Flash-Thinking-2601 이식(HeavyThinking + 노이즈/환경 스케일링) 
패치: hotfix09(원천) — InFi-Check FGFC(근거/오류타입/교정) 적용 지침 추가 + 참조 갱신
패치: hotfix12 — Patterning(dual of interpretability) 기반 데이터 개입(증류/회귀 데이터 믹싱)
패치: hotfix12p1 — Verifier/Router 무(無)모델 기본값 + 에스컬레이션 지표/트리거(관측 가능성) 추가
> 목적: Rulecraft를 로컬 LLM 또는 API LLM 호출 경로에 “붙여” 운영할 때 필요한 최소 구조, 안전한 확장, 오픈소스 공개 기준까지 한 파일로 정리한다.


> 관련 문서(선택):
> - Augnes Local 부록(루프 규율/근거): `Rulecraft_Addendum_0.5.15_rev15_memory_phase3_longcat2601_hotfix12p1.md`
> - Contracts/Schema SSOT(정본): `Rulecraft_SSOT_0.5.15_ssot07_memory_phase3_hotfix12p1.md`
> - Verifier 제작 사양(구현 스펙): `Rulecraft_Verifier_Spec_r06_memory_phase3_longcat2601_hotfix12p1.md`

---

## 1) 핵심 결론 (초단기 기억용)

- Rulecraft는 **모델 내부 플러그인**이 아니라 **LLM 호출을 감싸는 컨트롤 레이어(미들웨어/오케스트레이터)** 다.
- “전반 성능 향상”은 모델 크기보다 **루프 설계(룰 선택→실행→검증→스케일링→합성→증류/회귀)**에서 나온다.
- 그래서 `EventLog/VerifierResult/cost_profile`을 오프라인으로 집계해 **FlowMap(RiskMap/OpportunityMap)**을 만들고, `CandidateSelect/should_scale/BudgetRouter/Distiller`의 입력 신호로 써서 **될 구간에만 계산과 룰을 집중**한다.

- 그래서 **로컬 LLM**(Ollama/llama.cpp/vLLM 등)에도, **API LLM**(OpenAI/Anthropic/Gemini 등)에도 동일한 형태로 적용 가능하다.
- 필요한 최소 세트는 **Runner(오케스트레이터)** + **LLMAdapter(generate)** + **Verifier** + **Logger/Trace**.
- 계산 확대(K-rollout, synth)는 상시가 아니라 **should_scale 트리거 기반**으로만 한다.
- “룰 저장소”는 **Rulebook**으로 명명하고, 운영 관점에서 레이어/권한/승격/회귀가 핵심이다.

---

## 1.1) 실용 응용 이식안 (운영 우선순위 요약)

> “당장 구현 순서”만 남긴다. 계약/스키마(SSOT)는 `Rulecraft_SSOT_0.5.15_ssot07_memory_phase3_hotfix12p1.md`를 따른다.

- **MVP**: `Runner + LLMAdapter + VerifierAdapter + Logger(EventLog/Trace)`  
  ↳ Playbook §2~§4, Addendum §3.3~§3.4
- **자동 수습 루프**: `1-pass → verify → should_scale → (SoT-1pass | K_probe→K_full+synth) → verify → log`  
  ↳ Playbook §2.2/§6, Addendum §5.4/§7.3
- **형식/툴콜 안정화**: `schema validate → (auto repair 1회) → downgrade/fallback`  
  ↳ Playbook §10, Addendum §3.6(Assertion)/§3.3(violated_constraints)
- **비용 제어**: `bucket×impact cost_profile` 기반 `BudgetRouter`로 `K/synth/max_tokens/rule_top_k` 상한 제어  
  ↳ Playbook §6.4~§6.5, Addendum §5.4.4
- **노이즈/툴 상호작용 견고화**: `Noise taxonomy + ToolFuzz(회귀팩) + EnvSuite(L3)`로 tool 실패/부분 성공/비결정성을 `Verifier.reason_codes`로 구조화해서 hardcase 라우팅과 회귀 우선순위를 자동화  
  ↳ Playbook §6/§15, VerifierSpec §5.1~§5.2
- **FGFC 모드(세부 팩트체크)**: 도큐먼트 기반 답변에서 L2가 `VerifierResult.fgfc`(근거+오류타입+교정)을 채워 디버깅/자동 교정/반례 생성에 직접 연결
  ↳ Playbook §2.2/§3.1.1, VerifierSpec §5.2.2, SSOT의 FGFCReport
- **HeavyThinking 모드(테스트타임 스케일링)**: low-K 병렬 브랜치(폭) + 제한된 심화(깊이) + 요약/합성으로 “K_full 전에” 값이 있는지 체크  
  ↳ Playbook §6.2.1, Addendum §5.4.2.2
- **룰 누적(자기개선)**: 로그가 쌓인 뒤 `Distiller → Consolidator → Rulebook 승격(temporary→active) → Regression`  
  ↳ Playbook §15, Addendum §6
- **PASS 정의(정합성)**: `PASS iff (verdict == PASS) AND (outcome != FAIL)`  
  ↳ Addendum §5.1 (이 Playbook도 동일 정의를 따른다)



## 1.2) 통합 순서(재검토 반영, 구현 체크포인트)

> Rulecraft는 “기능 추가”보다 **루프가 안정적으로 도는 순서**가 더 중요하다.
> 아래 순서를 뒤집으면, 대부분 비용 누수 또는 품질 붕괴로 끝난다.

0) **SSOT(계약) 잠금**  
   - `schema_version`, id 유일성, PASS 정의(SSOT §5.1) 고정  
1) **MVP 루프 고정**  
   - `Runner + LLMAdapter + VerifierAdapter + Logger(EventLog/Trace)`가 항상 끝까지 돈다  
2) **Verifier 실체화**  
   - L1(정적) 필수, 가능하면 L3(실행)로 `outcome`을 OK/FAIL로 확정  
3) **should_scale = 계산 상한 장치**  
   - K-rollout/synth는 상시 금지, 트리거 기반 `probe→full` 단계형만  
4) **PaCoRe-lite(병렬-압축-합성)**  
   - rollout→summary→top-m→synth(2-pass) + 재검증 + best-rollout fallback  
5) **BudgetRouter(비용 제어)**  
   - bucket×impact 비용 프로파일로 `K/synth/max_tokens/rule_top_k` 상한 제어  
6) **Rulebook 승격 게이트(자기개선 통제)**  
   - tests/counterexample 없는 룰은 `temporary` 유지, 자동 승격 금지  
7) **FlowMap/PolicySearch(오프라인 인텔리전스)**  
   - 로그가 쌓인 뒤에만 활성화. 반영은 항상 `Replay→Canary→Rollback`.

---

## 2) 아키텍처: Runner + Adapters

### 2.1 Control Plane vs Data Plane

- **Control Plane (Rulecraft 영역)**  
  룰 선택/주입, 검증, 스케일링 판단, 로그/회귀/룰 적재를 담당.
- **Data Plane (LLM 백엔드 영역)**  
  로컬 엔진 또는 API 호출을 수행하고, 텍스트/툴콜 결과와 메타데이터를 반환.

### 2.2 표준 실행 흐름 (권장)

1. 입력 `x` 수신
2. (Phase 1) `intent_key/state_key`를 만들고 메모리를 **RECALL**(필터→리랭크)해 힌트를 확보
3. Rulecraft가 top-k 룰/메모리 힌트를 반영해 **주입 계획(injection plan)** 생성
4. LLM 1-pass 실행 → 후보 결과 `y0`
5. Verifier로 검증 → `VerifierResult` (옵션: `fgfc`로 문장/claim 단위 근거+오류타입+교정 기록)
6. `should_scale`면: 아래 중 하나(또는 조합)로 “보험 계산”을 수행
   - (A) **SoT-1pass**
   - (B) **K-rollout(+Top-m)** → synth(2-pass)
   - (C) **ReuseSeed(옵션)**: ReuseBuffer seed 선택(PUCT)로 롤아웃/탐색 재시드
   - (D) **SandboxProbe(옵션)**: LLM-in-Sandbox로 계산/근거/형식 처리
   - (E) **GuidedTreeSearch(옵션)**: 상태-행동 트리 서치(PUCT/beam) + Verifier(L1/L3)로 가지치기, LLM은 제안자/휴리스틱 역할

7. 최종 결과 출력
8. (Phase 2) **Folding + Memory Actions**: WorkingSet/Trace를 접고, `MemoryActionPlan`을 생성한 뒤 적용(`MemoryActionRecord`)하고 EventLog에 연결
9. (Phase 3) **PRAXIS(조건부 전술)**: fold 결과를 바탕으로 `ReuseBuffer.tactic_entries`를 WRITE/MERGE/RETIRE로 갱신하고, 다음 런의 RECALL 소스에 반영
10. 로그 기록, 룰 증류/적재(옵션), 회귀 테스트 등록(옵션)

---

## 3) 최소 요구 컴포넌트

### 3.1 필수

- **RulecraftRunner**: 전체 오케스트레이션
- **LLMAdapter**: 로컬/API 호출을 동일 인터페이스로 래핑
- **VerifierAdapter**: 검증기(로컬/API/규칙기반 가능)
- **Logger/Trace Store**: 실행 로그, 비용, 룰 적용 정보, verdict/outcome 기록


### 3.1.1 Verifier는 “1/2/3층”으로 만든다 (권장)

- **L1 정적 검증(필수)**: 스키마/형식/제약/툴콜 규칙 검사 → `violated_constraints` 중심
- **L2 의미 검증(선택)**: 저비용 grader(로컬 LLM/간단 룰/하이브리드)로 `score/reason_codes` 산출
  - (옵션, FGFC) 도큐먼트 기반 답변이면 `VerifierResult.fgfc`를 채워 **문장/claim 단위 verdict + 근거 + 오류타입 + 교정안**을 남긴다
- **L3 실행 검증(옵션, 강력 추천)**: Sandbox/하네스에서 실행·채점 → `outcome`을 **OK/FAIL**로 고정(텍스트만으로 애매한 문제에 특히 강함)

- Verifier의 반환 계약은 `Rulecraft_SSOT_0.5.15_ssot07_memory_phase3_hotfix12p1.md`의 `VerifierResult`를 **MUST** 따른다.
- 제작 사양(인터페이스/합성 규칙/기본 reason_codes taxonomy)은 `Rulecraft_Verifier_Spec_r06_memory_phase3_longcat2601_hotfix12p1.md`를 정본으로 한다.
- 약한 모델일수록 L2를 과신하지 말고, **L1+L3로 “정답을 환경에서 뽑게”** 하는 쪽이 가성비가 좋다.

#### (추가) “무(無)모델 Verifier/Router” 기본값 + 에스컬레이션 규율

- Rulecraft의 기본 목표는 **Verifier/Router/BudgetRouter를 별도 AI 모델 없이** 먼저 완성하는 것이다.
  - Verifier: L1 정적 검증(필수) + 가능하면 L3 실행 검증(테스트/샌드박스)로 `outcome`을 확정
  - Router/BudgetRouter: EventLog/VerifierResult/cost 집계(FlowMap) 기반 **결정적 라우팅**
- L2(의미 검증)는 기본 OFF로 두고, 붙이더라도 “판결”이 아니라 **should_scale/선별 신호**로 제한한다.
- 에스컬레이션(=L2 붙이기) 판단은 아래 관측치로 한다(Verifier Spec §0.1 참고):
  - bucket별 `UNKNOWN rate` / `insufficient_evidence rate`
  - 반복 `failure_cluster_id`
  - `exec_unavailable` (L3 부재) vs “의미 검증 부재” 구분


### 3.2 선택 (강력 추천)

- **BudgetRouter(Policy)**: 예산/비용/impact 신호로 `should_scale`, `K_probe/K_full`, `synth_used`, `max_tokens`, `rule_top_k`를 **상한 통제**하는 정책 레이어
  - 핵심은 "무조건 다운그레이드"가 아니라, *버킷×impact 기준으로* 단계적으로 계산을 줄이고(Full→Probe→1-pass), high impact는 최소한의 보험 계산을 남기는 것
- **Offline FlowMap Analyzer(Policy Intelligence)**: `EventLog/VerifierResult/cost_profile`를 오프라인으로 집계해 `RiskMap`/`OpportunityMap`을 산출하고, `CandidateSelect/should_scale/BudgetRouter/Distiller`에 “될 놈에게만 계산” 신호를 제공
  - `RiskMap`: bucket×(stage|edge)에서 `FAIL/PARTIAL/UNKNOWN`이 집중되는 지점(필요 시 reason_codes로 분해)
  - `OpportunityMap`: 개입(`SoT-1pass`, `K_probe`, `K_full+synth`, 룰 타입/주입모드)이 `PASS` 회복/품질 상승을 만든 효율(`gain/cost`) 추정
- **ExecutionVerifier(VerifierAdapter, 옵션)**: “텍스트로만” 검증이 어려운 태스크(코드/실험/툴체인)에서 **실행 결과(성공/실패/메트릭)**로 `VerifierResult`를 만든다.
- **SandboxAdapter(LLM-in-Sandbox, 강력 추천)**: 일반 목적 Docker/Ubuntu 샌드박스를 data plane로 제공해, 모델이 터미널/파일을 통해 “비코드” 문제까지 해결하도록 한다.
  - 최소 툴셋: `execute_bash`(명령 실행), `str_replace_editor`(파일 생성/편집), `submit`(종료)
  - 기대 효과: (1) **약한 모델 증폭**(정확 계산/형식 강제/장문 컨텍스트 처리), (2) **관측 가능성**(행동 로그로 실패 유형 분해), (3) **루프 효율**(K를 늘리기 전에 환경으로 해결)
  - 운영 규율: `SandboxPolicy`로 네트워크/자원/턴을 캡하고, `EventLog.sandbox` + `SandboxActionTrace`로 감사/회귀 가능하게 남긴다(Addendum §3.10, ADR-0019).
  - 권장: `K_probe(저비용)` → frontier만 `K_full(+synth)`로 승격(§6.3의 Probe→Full 규칙을 그대로 재사용)
  - 운영 포인트: 평가 하네스/채점 코드는 **불변(core)** 로 두고, 패치 적용 범위를 대상 코드로만 제한(리워드 해킹 방지)
- **PolicySearchLoop(Evolutionary, 옵션)**: 실행 점수 기반으로 룰/정책 패치(트리거/예산/주입/증류 프롬프트)를 **진화적 탐색**으로 개선한다.
  - (권장) 목적함수는 평균이 아니라 *최대 개선*을 노리는 entropic utility(soft-max)를 사용하고, β는 KL-anchored로 캡해서 분포 붕괴를 방지한다(SSOT Addendum ADR-0017).
  - diversity/novelty quota를 보상에 얇게 섞어 mode collapse를 방지(§11.1/SSOT의 optional 필드 참고)
- **Compactor**: 롤아웃 결과를 `RolloutSummary`로 압축
- **Synth Pass**: 요약 묶음 기반 2nd-pass 통합
- **Distiller + Rulebook + RegressionRunner**: 룰 자동 생성/정리/회귀 운영

---

## 4) LLMAdapter 인터페이스 스펙 (권장)

### 4.1 공통 시그니처

```python
class LLMAdapter:
    def generate(
        self,
        messages: list[dict],              # [{"role": "system"|"user"|"assistant"|"tool", "content": "..."}]
        *,
        temperature: float = 0.2,
        max_tokens: int | None = None,
        tools: list[dict] | None = None,   # 툴콜/함수콜 지원 시
        response_format: dict | None = None, # 구조화 출력 지원 시
        seed: int | None = None,
    ) -> tuple[str | dict, dict]:
        """returns (text_or_toolcall, meta)"""
```

### 4.2 메타데이터(meta) 최소 필드

- `model`: str (모델명/버전)
- `backend`: `"local" | "api"`
- `latency_ms`: int
- `tokens_in`: int (가능하면)
- `tokens_out`: int (가능하면)
- `cost_usd`: float | None (API면 실제, 로컬이면 None 또는 0)
- `rate_limited`: bool (API면 유용)
- `error`: str | None

> 토큰 수를 못 얻는 로컬 런타임도 있으니, 그땐 `latency_ms`를 우선 기록하고 필요하면 추정치를 별도 필드로 남긴다.

---

## 5) 룰 주입(injection) 방식

- **system_guard**: GuardrailRule을 system 최상단에 배치 (우선순위 1)
- **prepend**: StrategyRule을 user 앞부분에 체크리스트/절차 형태로 추가
- **inline**: 특정 단계(도구 호출 전/출력 포맷 직전 등)에 짧게 삽입

### 5.1 적용 우선순위 (권장)

1) GuardrailRule → 2) StrategyRule → 3) 기타 힌트/예시

---

## 6) should_scale 트리거와 비용 정책

### 6.1 should_scale 트리거 예시

- high impact (금전/의료/법/대외발송/되돌리기 어려운 작업)
- Verifier verdict: `PARTIAL` / `FAIL`
- Verifier outcome: `UNKNOWN` / `FAIL`
- outcome: 불확실(근거 부족, 충돌, 포맷 위반, 제약 위반)
- reason_codes: “불확실/모호/상충” 계열
- hardcase 플래그 (과거 실패 빈도 높음)
- (권장) **FlowMap 기반 hardcase**: 버킷별 `RiskMap` 상위(또는 특정 reason_codes 상위) 구간은 hardcase로 자동 승격
- complex tool interaction (멀티 턴/연쇄 툴콜/의존성 그래프)
- tool-noise 감지: `tool_timeout|tool_failure|tool_output_invalid|partial_success` 등
- env-noise 감지: 동일 입력 재실행 시 상충/비결정성(샌드박스/테스트 플래키)
- **검증 불가/근거 수집 불가 태스크**(L3/harness 없음, 외부 사실 확인 금지/불가 등):
  - `outcome=UNKNOWN`은 실패가 아니라 *확정 불가*다(VerifierSpec §4.2).
  - 기본은 `SoT-1pass 1회` 또는 `명확화/분해`로 전환하고, 무의미한 `K_full+synth` 확장은 BudgetRouter로 캡한다.
  - `reason_codes`에 `insufficient_evidence|exec_unavailable` 등을 남겨 FlowMap에서 hardcase로 분리 집계한다.


### 6.2 SoT-1pass (Society-of-Thought 스타일 단일 패스 내부 토론)

SoT-1pass는 “멀티에이전트”가 아니라, **단일 생성 호출 안에서 역할 분화와 충돌-봉합 절차를 강제**하는 *중간 티어*다.
목표는 K를 무작정 키우기 전에, **저비용으로 오류/누락/가정 충돌을 한 번 더 걷어내는 것**이다.

- 권장 사용 지점(대표):
  - `verdict in {PARTIAL, FAIL}` 또는 `outcome == UNKNOWN`
  - `reason_codes`에 불확실/상충/근거 부족이 포함
  - high impact인데 근거가 얇아 “검증을 한 번 더” 하고 싶을 때
  - 로컬 예산(시간/동시성)이 빡세서 `K_probe`조차 부담일 때

- 권장 프로파일(예시):
  - Roles: `Solver → Challenger → Mediator → Verifier`
  - `sot_max_turns`: 2~3(권장 2)
  - 출력 규격: “최종 결론(1줄) + 근거/가정(3개 이내) + 버린 대안(2개 이내) + 남은 리스크(체크리스트)”
  - 길이 가드: `max_tokens`를 K-rollout보다 더 타이트하게(수다 방지)

- 종료/승격 규칙(권장):
  - SoT-1pass 후 Verifier가 PASS/OK면 종료(추가 K 생략)
  - SoT-1pass 후에도 `PARTIAL/UNKNOWN`이면 `K_probe → (frontier면) K_full+synth`로 승격
  - deadzone/불능군이면(기본 정책에 따름) K 확장 금지, 명확화/분해/상위 verifier로 전환

> 용어 주의: **SSOT**(Single Source of Truth, 스키마/계약의 단일 진실원천)와 **SoT**(Society-of-Thought, 대화적 추론 스캐폴딩)는 약어가 비슷하지만 목적이 다르다.


### 6.2.1 Heavy Thinking (폭+깊이 확장 TTC, 권장)

LongCat-Flash-Thinking-2601이 말하는 “Heavy Thinking”은 테스트타임에서 **깊이(반복/심화) + 폭(병렬 분기)**를 같이 키워 성능을 올리는 모드다.  
Rulecraft에서는 이를 “K_full 전에 한 번 더” 쓰는 **중간 티어**로 넣는 게 실용적이다.

- 기본 아이디어:
  - (폭) `N`개 병렬 브랜치(서로 다른 seed/role/관점)로 후보를 만든다
  - (깊이) 각 브랜치는 `max_turns=2` 정도의 짧은 자기교정만 허용한다(수다 금지)
  - `RolloutSummary`로 압축(긴 CoT 패싱 금지) → top-m 선별 → synth(2-pass) → 재검증
- 권장 파라미터(초기값):
  - `N=3~5`, `top_m=2`, `max_tokens_per_branch`는 SoT-1pass 수준으로 타이트하게
  - `forbid_cot=true` 유지(요약은 “핵심 단계/가정/리스크 체크리스트”만)
- 종료 규칙:
  - HeavyThinking 후 `PASS/OK`면 종료(추가 K 생략)
  - 여전히 `UNKNOWN/PARTIAL`이면 `K_probe → (frontier면) K_full+synth`로 승격
- 로그 규율:
  - `EventLog.flow_tags += ["heavy-thinking"]`
  - `EventLog.run.mode="kroll"` + `EventLog.run.cfg.plan_style="heavy_thinking_v1"`
  - `EventLog.rollout_select.rollouts_n=N`, `EventLog.rollout_select.top_m=top_m`


### 6.3 Probe → Full (권장)


### 6.3.0 GuidedTreeSearch(GTS) (형식-검증 가능한 도메인에서만, 선택)

**언제 쓰나**
- 수학/기하/정리증명/퍼즐처럼, (a) 상태(state)와 (b) 적용 가능한 변환(action)을 정의할 수 있고
- L1(형식) 또는 L3(실행/프로버)로 **가지치기(pruning)가 결정적으로** 가능한 경우

**핵심 아이디어(논문: TongGeometry 스타일)**
- LLM은 “정답을 직접 말하는 존재”가 아니라, 트리 서치에서 **유망한 다음 액션을 제안**하는 정책(policy) 역할
- Verifier/L3(프로버/하네스)가 각 노드에서 **성립 여부(outcome)와 실패 원인**을 확정하거나 UNKNOWN으로 남김
- 선택 정책은 Rulecraft에 이미 있는 `PUCT`(ReuseSeed 선택) 메타를 그대로 재사용해서, 노드 선택에도 적용 가능

**Rulecraft 매핑(최소 구현)**
- Node state: `WorkingSet`(현재 제약/가정/목표) + `TraceCapsule.refs`(근거/도형 객체 참조)
- Action: `tool_call`(기하 프로버/심볼릭 변환) 또는 “aux construction 제안(LLM)”을 `SandboxProbe`로 검증
- Search meta: EventLog에 `experiment.kind="policy_search"` + `run.mode="tree"`로 기록(SSOT/Playbook의 관측 가능성 유지)

**주의**
- GTS는 “모든 태스크 만능”이 아니다. 검증이 안 되는 영역에서 트리를 키우면 그냥 랜덤 워크가 된다(비용만 태움).


### 6.3.1 PaCoRe-lite 메시지 패싱 (요약→top-m→synth)

K-rollout을 “여러 개 만들기”에서 끝내면, 마지막에 모델이 그걸 무시하고 혼자 다시 풀어버리는 경우가 잦다.
그래서 **rollout 결과는 반드시 `RolloutSummary`로 압축**하고, synth(2nd-pass)는 **전체 trace가 아니라 summaries(top-m)만 입력**으로 삼는 걸 기본으로 둔다.

- 요약 산출물 계약(SSOT): SSOT `RolloutSummary`(정본) + Addendum rev11 §3.7(설명)
- top-m 선별: `VerifierResult.score + diversity` 기반(Playbook §10의 “synth가 더 망침” 케이스 대비로, synth 결과도 재검증)
- 요약 규율: `forbid_cot=true`(긴 CoT 메시지 패싱 금지) + `max_tokens` 상한



- **K_probe**(예: 3): 간단히 p_hat/p_lb95 측정
  - (초기) p_hat는 `VerifierResult.score`(예: yes_logit)를 성공확률로 취급하거나, PASS율로 추정
- **Frontier band**(예: 0.3~0.7): 가치가 있는 구간이면 **K_full**(예: 6~8) + synth
- **Deadzone**(예: p_lb95 < 0.05): K 확장 금지. 문제 분해/명확화/상위 모델 에스컬레이션

### 6.4 BudgetRouter(비용-성능 피드백 루프)와 예산 초과 정책

원칙: **비용을 ‘벌금’이 아니라 ‘입력 신호’로 취급**해서, 같은 안전 수준을 더 적은 계산으로 유지한다.

- `cost_profile[bucket, impact]`(권장: EWMA + p95)를 누적한다. bucket은 `task_type`/`failure_cluster`/`domain_tag` 중 하나로 시작하고, impact는 `normal/high`만으로도 충분하다.
- 예산이 빡세질수록 **단계형으로 계산을 줄인다**: `Full → Probe → 1-pass` (그리고 synth는 가장 먼저 꺼진다).
- 단, **high impact에서 ‘하드 캡 = 무조건 다운그레이드’는 금지**: 최소한 `K_probe` 수준의 보험 계산은 남기고, 대신 다른 버킷(normal)에서 먼저 감산한다.
- 하드 캡 시 우선순위(권장):
  1) synth off
  2) `K_full` 상한 하향
  3) `K_probe` 유지(특히 high impact)
  4) `max_tokens`, `rule_top_k` 캡
  5) 도구/비싼 verifier 차단 → 요구사항 명확화/분해
- (선택) **오버드래프트/부채 모델**: high impact에서 cap을 잠깐 넘겼으면, 이후 N분/다음 M요청에서 동일 bucket의 K/synth를 자동 감산해 ‘상환’한다(로그로 남김).


### 6.5 FlowMap(RiskMap/OpportunityMap) 기반 트리거 보정(권장)

- 목적: 불확실하다는 이유로 계산(K/synth)을 **무작정 늘리지 말고**, 오프라인 지도에서 “돈값하는 개입”만 선택한다.
- 입력: `EventLog`(run.mode/selected_rules), `VerifierResult`(verdict/outcome/reason_codes), `cost_profile[bucket×impact]`
- 출력:
  - `RiskMap`: 실패/불확실이 집중되는 stage/edge
  - `OpportunityMap`: 개입별 `PASS` 회복(또는 품질 상승) `gain`과 `cost`를 합친 `efficiency=gain/cost`

**추가(옵션): 학습된 FlowMap 추정기**
- 버킷이 희소하거나 노이즈가 큰 경우, 집계표 대신/보조로 `nn_field_v1` 같은 작은 NN을 붙여 `risk/opportunity`를 추정할 수 있다(Addendum §3.8.1, SSOT `FlowMapSnapshot.estimator`).
- 단, 이건 “정책 힌트”일 뿐 판결이 아니다. 반영 규율은 동일하게 `replay → canary → rollback`만 허용.

**적용 규칙(권장)**
- `OpportunityMap`이 낮은 버킷은, 트리거가 떠도 `K_full+synth`로 가지 말고 `SoT-1pass` 또는 요구사항 명확화/분해로 전환한다.
- `RiskMap`이 높은 버킷은 GuardrailRule을 우선 주입하고(`system_guard`), `selected_rules[].reasons`에 `risk_hotspot=...`, `opp_hotspot=...` 같은 태그를 남겨 정책 튜닝 가능성을 높인다.
- `BudgetRouter`는 `efficiency`를 기준으로 “full을 남길 버킷”과 “probe/1-pass로 강제할 버킷”을 단계형으로 나눈다.

---


### 6.6 Patterning(데이터 개입) — “어떤 데이터가 어떤 일반화를 만들까”를 역으로 푸는 루프(옵션)

arXiv:2601.13548 *Patterning: The Dual of Interpretability*의 핵심은,
- **관측가능한 구조 지표(Observable) 변화** `dμ` 와
- **데이터 분포 파라미터(h) 미세 변화** `dh`
사이를 **susceptibility 행렬 χ**로 선형 근사하고(`dμ = χ·dh`),
원하는 목표 변화 `dμ_target`를 만드는 **최소 개입**을 `dh = pinv(χ)·dμ_target`로 구하는 것이다.

Rulecraft에선 내부 회로를 직접 읽을 필요 없다. 대신 “구조”를 **행동 프록시(관측치)**로 두고,
`h`를 “로그에서 추출한 데이터 슬라이스/반례 타입/생성기 템플릿의 가중치”로 둔다.

#### 적용 대상(현실적인 것만)
- Distiller가 만드는 `distill_dataset` 샘플링 비율(예: reason_code별 반례 비중)
- CounterexampleGenerator / Synthesizer 프롬프트 템플릿 혼합 비율
- (선택) LoRA/SFT용 샘플 가중치(로컬에서만, canary 필수)

#### 최소 구현(권장)
1) **Observables μ**(측정값):  
   - `pass_rate[bucket]`, `unknown_rate[bucket]`  
   - `reason_code_rate[bucket, code]` (예: format_leak/tool_misroute/...)  
   - `avg_cost[bucket]` (제약: 비용 폭발 방지)

2) **Probes h**(개입 레버):  
   - 데이터 슬라이스 K개(예: “format_leak 반례”, “tool_misroute 반례”, “실행 성공 트레이스”, “요구사항 불명확 케이스”)

3) **χ 추정(가성비 버전)**:  
   - 각 probe k의 샘플링 가중치를 `+ε` 만큼 올린 “미세 개입”을 만들고,  
   - 동일 canary/replay 세트에서 μ 변화를 측정해 `χ_{i,k} ≈ Δμ_i / ε` 로 근사한다.  
   - `ε`는 작은 값(예: 0.05) + 클리핑으로 안정화한다.

4) **개입 해(가중치 계산)**:  
   - 목표 `dμ_target`(예: 특정 reason_code_rate를 낮추고 pass_rate를 올림)을 만들고  
   - `dh = pinv(χ)·dμ_target`를 계산한다(릿지 정규화 권장).  
   - `dh`는 `[0, w_max]`로 클립하고 총합을 1로 재정규화한다.

5) **적용/검증**:  
   - 결과는 `PatterningPlan`으로 기록한다(SSOT optional extension 참조).  
   - 적용은 항상 `replay → canary → rollback` 규범을 따른다. 회귀(regress)면 즉시 롤백.

#### 금지 사항
- 런타임에서 즉시 반응하는 “온라인 패턴링”은 금지. 학습-평가-배포 경계를 깨면 사고 난다.

---


## 7) Rulebook: 레이어/권한/수명(TTL)

Rulebook은 단순 저장소가 아니라 **운영 제어 장치**다. 공개/협업을 생각하면 레이어와 권한 분리가 필수.

### 7.1 권장 레이어

- `Rulebook.Core` (불변): 시스템 안전/보안/권한 모델의 뼈대. 최상위 우선순위.
- `Rulebook.Project`: 프로젝트 운영 규칙(팀/리포 기본값).
- `Rulebook.UserOverlay`: 권한 없는 유저 경로. 기본은 좁은 scope + TTL.
- `Rulebook.TrustedOverlay`: 권한 있는 유저 경로. 품질 저하는 본인 책임(단, 보안/권한은 별도).
- `Rulebook.SessionOverlay`: 세션 한정(강한 TTL), 실험용.

### 7.2 우선순위 (권장)

`Core Guardrail > Project Guardrail > User Guardrail(add-only) > Strategy(Project→User)`

> 핵심: 유저가 룰을 넣을 수는 있어도 Core/Project를 “무력화”는 못 한다.



### 7.3 검색/리콜(Phase 1, 권장)

Rulebook/ReasoningBank/ReuseBuffer는 “그냥 벡터 검색”으로 붙이면 재사용률이 급격히 떨어진다.  
Phase 1의 목표는 **intent/state 호환성으로 먼저 걸러서** “틀린 힌트”를 줄이는 것.

- **intent_key (안정)**: domain/task/tools/output/constraint 기반. “이런 종류의 작업”인지 판단.
- **state_key (휘발)**: run.mode/budget/policy/tool/sandbox/verifier 프로필 기반. “지금 실행 가능한가” 판단.

권장 파이프라인(SSOT §4.4):
1) Candidate gather(소스별 top-k’): Rulebook, ReasoningBank, ReuseBuffer(tactic_entries)(Phase 3), 필요 시 최근 TraceCapsule
   - seed/prior 재시드는 RECALL이 아니라 `reuse_select`(PUCT) 경로로 분리
2) Filter: bucket/intent/state 불일치 컷 + retired/저품질 컷
3) Rerank: `semantic + intent + state + quality` 가중합
4) top-m을 짧은 **MemoryHint**로 주입(장문 금지, refs 우선)

**메모리 주입 예산(권장 기본값)**  
(가볍게 굴리려면 숫자로 때려 박아야 한다.)

- `MemoryHint.summary`: ≤ 120 tokens (또는 ≤ 600 chars)
- `ConditionalTactic.injection.content`: ≤ 160 tokens (또는 ≤ 800 chars)
- 한 run에서 (룰 제외) 메모리 주입 총합 ≤ 256 tokens
- 상한 초과 시: 더 압축하거나 `payload_ref`로 넘기고, Runner는 초과분을 잘라서 주입

관측 가능성:
- 실제 사용한 memory/rule id는 EventLog의 `memory_recall.used_ids`에 남겨라. 아니면 “왜 좋아졌는지/나빠졌는지” 추적이 안 된다.

---


### 7.4 Folding + Memory Actions (Phase 2, 권장)

Phase 2는 “리콜(Phase 1)로 가져온 것을 기록”하는 수준을 넘어,
런이 끝날 때(또는 트리거 발생 시) **재사용 가능한 단위로 접고(Folding)**,
필요한 메모리 오퍼레이션을 **자동으로 계획/적용**한다.

권장 트리거:
- `end_of_run` (기본)
- `ws_overflow`
- `fail_cluster` (반복 실패/제약 위반 패턴)
- `phase_shift` (probe→full 등)

권장 절차(Plan→Apply→Record):
1) `fold()` → `FoldResult` 생성(WorkingSet/Trace/VerifierResult 기반)
2) `plan_memory_actions()` → `MemoryActionPlan` 생성
3) `apply_memory_actions()` → `MemoryActionRecord[]` 생성
4) EventLog에 `memory_fold` / `memory_actions`로 연결(관측 가능성)

안전장치:
- Rulebook은 “승격 룰 저장소”다. Phase 2 자동화는 `active` 승격을 하지 않는다(temporary/draft만).
- PRUNE는 PIN/보존 대상 제외. 기본은 RETIRE 우선.


### 7.5 PRAXIS: 조건부 전술(conditional tactics) 운용 (Phase 3, 권장)

목표: “재사용 가능한 전술”을 Rulebook(강한 규칙)로 바로 올리지 말고, **조건부 힌트 저장소**(ReuseBuffer.tactic_entries)에 먼저 쌓아 가성비를 본다.

- 단위: `ConditionalTacticRecord`
- 리콜: `RECALL(intent,state)`의 소스에 `ReuseBuffer`(tactic_entries)를 추가한다.
- 주입: 길이 제한(짧게), 충돌 시 **가장 보수적인 전술만** 남기고 나머지는 무시(또는 RETIRE 후보로 기록).
- 갱신: Phase 2의 Folding/Memory Actions가 끝난 뒤, 아래 3가지 중 하나로 반영한다.
  - WRITE: 새 전술 기록(처음 등장)
  - MERGE: 중복/유사 전술을 합쳐 상위 요약으로 정리
  - RETIRE: 실패/부적합/노이즈 전술 비활성화(기본), PRUNE는 제한적으로

관측 가능성:
- 사용된 전술은 EventLog의 `praxis.used_tactic_ids`에 남긴다.
- 실패 시(Verifier FAIL/정합성 깨짐) `praxis.retire_candidate`를 만들고, 다음 compaction에서 RETIRE한다.

---

## 8) 유저 룰 입력(User Rule Submission) 설계

“유저가 직접 룰을 집어넣는” 기능은 제품성이 강하지만, 자유 텍스트 무제한 허용은 사고 루트다. 최소 구조를 강제한다.

### 8.1 기본 원칙(안전장치)

- 기본값은 `temporary` + TTL + 좁은 scope(태스크/태그/툴/출력).
- 유저는 **추가(add)** 는 가능, **제거/완화(remove/disable)** 는 불가.
- 권한 없는 유저는 `system_guard` 금지. `prepend/inline`만 허용.
- 적용 전 **Rule Lint + Conflict Check + Dry-run**.
- 승격(promote)은 테스트 없으면 금지. 좋은 룰은 “candidate”로만 올리고 조건 충족 시 승격.

### 8.2 최소 스키마(권장)

```yaml
RuleSubmission:
  schema_version: "0.5.15"
  submission_id: string     # MUST (로그/감사를 위한 안정 ID)
  created_at: string|null   # MAY (ISO8601)
  title: string
  type: "strategy" | "guardrail"
  scope:
    tags: [string]        # 예: ["writing", "code", "finance"]
    tools: [string]       # 예: ["web", "filesystem"]
    outputs: [string]     # 예: ["json", "markdown"]
  injection_mode: "prepend" | "inline"   # (권한 없는 유저는 system_guard 금지)
  priority: int           # user 범위 내에서만 의미
  ttl: "session" | "hours:6" | "days:1"
  text: string
  rationale: string?      # optional
```

### 8.3 Lint에서 즉시 거르는 금지 패턴(예시)

- “앞의 지시를 무시” / “규칙을 공개” / “로그를 출력” / “키/비밀을 출력” 류
- tool-call을 무조건 실행(권한 상승)
- Verifier 결과 무시/우회 지시

---

## 9) Trusted vs Untrusted 정책 (공개 프로젝트 기본)

오픈소스 공개를 전제로 하면, 기본은 Untrusted가 맞다. Trusted는 명시적 opt-in.

### 9.1 역할(Role) 예시

- `admin / trusted / user / guest`

### 9.2 정책(요약)

- **Trusted path**: 룰 추가/수정/삭제/전역 적용 허용(품질 저하 본인 책임)
- **Untrusted path**: 룰은 제안/세션 TTL/좁은 scope만 허용, `system_guard` 금지, Core/Project 무력화 금지

### 9.3 Trusted라도 남겨야 하는 최소 가드(권장)

- 다른 사용자 데이터 접근 금지(멀티유저/공유 환경이면 필수)
- 키/로그 유출 방지(본인만 아픈 문제가 아님)
- tool 권한 모델은 룰로 바꿀 수 없게 고정(권한 상승 루트 차단)

---

## 10) 실패 모드 Runbook (운영자용)

| 실패/징후 | 대표 원인 | 1차 조치 | 2차 조치(필요 시) |
|---|---|---|---|
| Verifier FAIL/UNKNOWN | 근거 부족, 충돌, 제약 위반 | 명확화 질문 / 제약 재주입 | K_probe→K_full / 상위 Verifier / 보험(API) |
| tool-call JSON 파손 | 출력 포맷 불안정 | schema validate → 자동 repair 1회 | 텍스트 모드 강등 + 사용자 확인 |
| synth가 더 망침 | 통합 환각/과잉 일반화 | synth 결과도 재검증 | FAIL이면 best rollout로 fallback |
| rollouts 다양성 부족 | mode collapse/후보가 다 비슷함 | diversity_score 확인, resample | top-m 강제 + novelty/transform 적용 |
| API timeout/rate limit | 네트워크/쿼터 | 백오프+jitter, 재시도 제한 | circuit breaker(잠시 차단), 로컬/대체 모델 |
| 로컬 OOM/KV 폭발 | 컨텍스트/동시성 과다 | 컨텍스트 요약, max_tokens 제한 | 동시성↓, 모델 다운시프트, prompt 축소 |
| 비용 폭발(API) | should_scale 과다/롤아웃 남발 | probe만 유지, synth off | untrusted 강화, 하이브리드 verifier 전환 |

---

## 11) 관측 가능성(Observability) 표준

### 11.1 권장 로그 필드(최소)

- (SSOT/EventLog) `schema_version`, `trace_id`, `x_ref`, `bucket_key`
- (SSOT/EventLog) `flow_tags`, `policy_signals`(risk/opp/efficiency)
- (SSOT/EventLog) `selected_rules[]`(rule_id/version/type)
- (SSOT/EventLog) `run.mode`, `run.cfg`(temperature/seed_prompt/plan_style/self_refine_steps/tool_order)
- (SSOT/EventLog) `sandbox.*`(enabled/network/turns/actions_n/traces_ref...)
- (SSOT/EventLog) `sot_profile`, `sot_max_turns`, `outputs.sot_signals`
- (SSOT/EventLog) `outputs.*`(y_ref/rollout_summary/synth_inputs...)
- (SSOT/EventLog) `verifier.*`(verifier_id/verdict/outcome)
- (SSOT/EventLog) `cost.*`(latency_ms/tokens_in/tokens_out/tool_calls)
- (SSOT/EventLog) `rollout_select.*`(rollouts_n/top_m/selection_method/selected_summary_ids/diversity_score)
- (SSOT/EventLog) (옵션) `experiment.*`, `reuse_select.*`, `repr.*`
- (SSOT/EventLog) (옵션, Phase 1) `memory_recall.*`
- (SSOT/EventLog) (옵션, Phase 2) `memory_fold.*`, `memory_actions.*`

- (콜 레벨/별도 스토어 권장) `backend`, `model`, `adapter_version`, `cost_usd`, `rate_limited`, `error`
- (제품/서비스 레벨) `request_id`, `session_id`, `failure_class` 등은 EventLog 외부에서 함께 묶어도 된다(SSOT 강제 필드는 아님).


### 11.2 샘플링 정책(권장)

- 정상: 1~5% 저장
- 실패/UNKNOWN: 100% 저장
- high impact: 100% 저장 + 리다액션(민감정보/키/개인정보)

---

## 12) 로컬 LLM 적용

### 12.1 장점
- 데이터가 로컬에만 남음(프라이버시/주권)
- 병렬 롤아웃을 과금 부담 없이 시도 가능(대신 시간/전력)
- 백엔드 커스터마이징 자유도 높음

### 12.2 제약
- VRAM/컨텍스트/속도 한계가 병목
- tool-call/구조화 출력/logprobs 지원 편차 큼
- 동시성(병렬 롤아웃)에서 런타임 안정성 차이

### 12.3 로컬 예산 정의 예시
- `budget = time_ms` 또는 `budget = joules` 또는 `budget = (time_ms, max_concurrency)`

---

## 13) API LLM 적용

### 13.1 장점
- 모델 품질/도구 기능 지원이 대체로 안정적
- 로컬 하드웨어 제약에서 탈출
- 구조화 출력/툴콜 운영이 쉬움

### 13.2 제약 및 운영 주의점
- K-rollout은 곧 비용 증가. should_scale가 필수
- 레이트리밋/쿼터로 병렬 설계가 막힐 수 있음
- 민감 컨텍스트/룰/로그는 요약/마스킹 후 전송 권장

---

## 14) 하이브리드 권장 조합

1) **API 메인 + 로컬 verifier**: 품질 확보, 검증 비용 절감  
2) **로컬 메인 + API verifier(보험형)**: 평소 0원, 위험 시만 API  
3) **로컬 메인 + 로컬 verifier**: 완전 로컬(성능은 하드웨어가 결정)  
4) **API 메인 + API verifier**: 가장 깔끔하지만 비용이 가장 무겁다

---

## 15) 릴리즈/버전/회귀(Regression) 운영

### 15.1 Rulebook 상태 전이(권장)

- `temporary`: 실험/세션 룰. 테스트 없어도 존재 가능(기본 TTL).
- `active`: 회귀/반례 최소 기준 통과 후 승격.
- `retired`: 성능 악화/충돌/쓸모 없음 확인 시 퇴역(롤백 가능).

### 15.2 승격 최소 기준(권장)

- **기본 최소(프로토타입)**  
  - 회귀 1개 이상(스모크)  
  - 반례 2개 이상(클러스터형 1 + 경계형 1 권장)

- **오픈소스/운영 모드(권장 강제)**  
  - Micro-Regression(자동 채점) 5개 이상  
  - 반례 2개 이상(클러스터형 1 + 경계형 1)  
  - Distiller가 `failure_prediction`(작동 가설 + 의존성 + 실패예측 2개 이상)을 포함  
  - 위 강화 기준을 못 채우면 `active`로 올리지 말고 `temporary`로 남긴다(코어 셋 제외).


### 15.3 Canary/롤백(권장)

- 새 룰/새 Runner는 일부 트래픽(또는 샘플)에서 먼저 적용
- 지표(FAIL/UNKNOWN 비율, latency, cost) 악화 시 즉시 롤백
- **BudgetRouter 정책(임계치/상한/버킷 설정)도 동일하게 Canary로 튜닝하고, 악화 시 정책만 즉시 롤백**

---

### 15.4 실패예측(taxonomy) 운영 규율(권장)

- Distiller는 룰을 만들 때 “왜 먹히는가”만 쓰지 말고, **어떻게 깨질지**를 같이 낸다.
- 권장 taxonomy(초기 8개):
  - `context_dilution` : 길이/턴 증가로 제약 희석
  - `instruction_conflict` : 상충 지시
  - `format_leak` : 포맷 밖 텍스트/구조 누수
  - `tool_misroute` : 툴 호출 종류/시점/순서 오류
  - `overconstraint` : 룰 과잉 적용(정상 케이스 망침)
  - `underconstraint` : 룰 적용 누락
  - `distribution_shift` : 도메인/스타일 변화로 깨짐
  - `adversarial_prompting` : 교란/탈선/탈출 프롬프트
- 운영 팁:
  - 실패 로그(Event/Trace)에 taxonomy 라벨을 붙이면, 룰 리팩토링 우선순위가 빨라진다.
  - 예측은 “판결”이 아니라 “힌트”로 취급하고, 회귀/반례 테스트로 교차검증한다.

### 15.5 Micro-Regression Pack(팩) 운영 규율(권장)

- Micro-Regression은 “작고 자동 채점 가능한” 테스트다. (정규식/스키마/툴콜 여부 등)
- 팩을 미리 만들어두면, 룰 작성자가 테스트를 매번 창작하지 않아도 된다.
- 초기 추천 팩 5종:
  - **FORMAT**: JSON/YAML/마크다운 포맷 준수(스키마/정규식)
  - **TOOL**: 툴 호출 강제/금지/순서/args 스키마
  - **BUDGET**: 길이/반복/루프 감지/조기 종료
  - **NOISE**: 출력 잘림/툴 실패/부분 성공/재시도 복구/비결정성 대응
  - **ENV**: 샌드박스/하네스 재현성(시드/반복 실행) + 플래키 감지
- counterexample는 팩과 별도로 “클러스터형 1 + 경계형 1”을 최소 규율로 둔다.


### 15.6 FlowMap 정책 튜닝(권장)

- **Replay → Canary → Rollback** 순서로만 반영한다(룰 승격과 동일한 운영 규율).
- Replay(오프라인): 기존 로그로 `Risk/Opportunity/efficiency`를 산출하고, 정책 변경안으로 결과(FAIL/UNKNOWN, cost/latency)를 재생 비교한다.
- Canary(온라인): 버킷/impact 일부에만 적용하고, 악화 시 **정책만 즉시 롤백**한다.
- 주의: FlowMap은 상관 기반 지도다. 인과는 A/B(정책 on/off), 개입 강제/차단 같은 반사실 비교로 보정한다.
- (옵션) `FlowMapSnapshot.estimator`로 학습된 추정기(nn_field)를 쓰더라도, **반사실 비교 + 롤백 규율**은 더 엄격해져야 한다(추정기 과신 금지).

## 16) 오픈소스 공개 체크리스트 (GitHub)

### 16.1 기본 정책
- Default는 **Untrusted**
- Trusted는 명시적 opt-in(예: `RULECRAFT_TRUSTED=1`)

### 16.2 저장소 구조(권장)

```
rulecraft/
  src/rulecraft/          # core (의존성 최소)
    runner/
    rulebook/
    verifier/
    logging/
    policy/               # trusted/untrusted, lint, conflict
    compactor/
    synth/
  adapters/
    local/
    api/
  examples/
    minimal_runner.py
    local_quickstart.py
    api_quickstart.py
  docs/
    ARCHITECTURE.md
    SECURITY.md
  tests/
```

### 16.3 공개 전 문서 최소 세트
- README.md (60초 Quickstart)
- ARCHITECTURE.md
- SECURITY.md
- CONTRIBUTING.md
- LICENSE
- CHANGELOG.md
(+ 가능하면 CODE_OF_CONDUCT.md)

### 16.4 CI 최소 테스트(생존형)
- rule lint 테스트(무력화/유출/권한 상승 패턴)
- conflict check 테스트
- runner smoke test(examples가 끝까지 돈다)

---

## 부록 A) 운영 기본값 표 (초기 권장)

| 항목 | 로컬 기본 | API 기본 |
|---|---:|---:|
| K_probe | 3 | 3 |
| K_full | 6 (동시성/속도 고려) | 6 (비용 고려) |
| frontier band (p_lb95) | 0.3~0.7 | 0.3~0.7 |
| deadzone (p_lb95) | < 0.05 | < 0.05 |
| synth 조건 | high impact 또는 frontier | high impact 또는 frontier |
| 재시도 | 1회(대부분 의미 적음) | 2~3회(백오프+jitter) |

> 이 값들은 “시작점”이다. 실제 운영 로그를 보고 조정한다.

---

## 부록 B) 메타데이터 표준 예시

```json
{
  "schema_version": "0.5.15",
  "trace_id": "t_01H...",
  "x_ref": "xhash_01H...",
  "bucket_key": "I2|coding|clarity_med",
  "flow_tags": ["heavy-thinking", "tool-heavy"],
  "selected_rules": [
    {"rule_id": "core.g1", "version": "0.5.15", "type": "GuardrailRule"},
    {"rule_id": "proj.s3", "version": "0.5.15", "type": "StrategyRule"}
  ],
  "run": {
    "mode": "kroll",
    "cfg": {"temperature": 0.2, "seed_prompt": "jitter_v1", "self_refine_steps": 0}
  },
  "outputs": {
    "y_ref": "yhash_01H...",
    "rollout_summary": null,
    "sot_signals": null,
    "synth_inputs": {"used_trace_ids": null, "used_summary_ids": null}
  },
  "verifier": {"verifier_id": "vf_l1l2_v1", "verdict": "PARTIAL", "outcome": "UNKNOWN"},
  "cost": {"latency_ms": 1830, "tokens_in": 1240, "tokens_out": 420, "tool_calls": 1}
}
```

---

## 부록 C) 용어 미니 사전

- **Runner/Orchestrator**: 전체 파이프라인을 실행하는 상위 루프
- **Adapter**: 로컬/API 백엔드를 동일 인터페이스로 추상화
- **Verifier**: 결과의 제약 준수/근거/형식 등을 판정
- **K-rollout**: 다회 생성(또는 다경로 탐색)으로 신뢰도 추정
- **Compactor**: 롤아웃 결과를 짧은 요약으로 압축
- **Synth**: 요약 묶음을 보고 최종안을 통합 생성
- **Rulebook**: 규칙 저장+운영(권한/승격/회귀)의 중심

- **SoT-1pass**: 단일 호출에서 “질문/반박/관점전환/통합” 절차를 강제하는 중간 티어 추론 스캐폴딩
- **SSOT**: 계약/스키마/설계 결정에서 “단일 진실원천”으로 취급되는 정의(문서 또는 파일)
- **Regression**: 룰/행동의 품질을 유지하기 위한 회귀 테스트

## 17) 구현 체크리스트 (바로 붙이는 순서)

1) **Runner/Adapter/Logger**부터 고정  
   - LLMAdapter meta: `model/backend/latency_ms/tokens_in/out/cost_usd/error`(Playbook §4)  
   - EventLog 최소 필드: `trace_id, selected_rules, verdict/outcome, cost`(Playbook §11, Addendum §3.4)

2) **VerifierResult를 SSOT 계약으로 고정**  
   - `verdict/outcome/reason_codes/(violated_constraints)` 구조(=Addendum §3.3)  
   - PASS 판정은 `verdict==PASS && outcome!=FAIL`로 단일화(Addendum §5.1)

3) **should_scale + BudgetRouter**를 “옵션”이 아니라 “상한 제어 장치”로 둔다  
   - high impact 최소 보험 계산(`K_probe` 또는 SoT-1pass) 남기기(Playbook §6.4)  
   - 나머지 버킷에서 먼저 감산하는 단계형 정책(Full→Probe→1-pass)

4) **PaCoRe-lite(요약→synth)**는 처음부터 넣는 게 낫다  
   - rollout을 만들어놓고 안 쓰면 비용만 늘어난다(Playbook §6.3.1)

5) **룰 승격 게이트(temporary→active)**는 초기에 빡세게  
   - tests 없으면 무조건 temporary(Playbook §15.2, Addendum §6.3)  
   - 최소: regression ≥1 + counterexample ≥2(클러스터 1 + 경계 1)

6) **FlowMap은 마지막에**  
   - 로그가 쌓인 뒤 replay→canary→rollback으로만(Playbook §15.6, Addendum §3.8)