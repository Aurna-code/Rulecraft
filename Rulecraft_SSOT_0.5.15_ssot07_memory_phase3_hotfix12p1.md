# Rulecraft Contracts & Schemas SSOT — v0.5.15

문서 리비전: **ssot07**  
작성일: 2026-01-26 (Asia/Seoul)


수정일: 2026-01-29 (Asia/Seoul)
패치: TongGeometry(GTS) 메타데이터 — run.mode="tree" + EventLog.tree_search 추가
패치: NN-FT(2601.14453) — FlowMapSnapshot.estimator(옵션) 추가

패치: Memory Subsystem 계약(Phase 0/1) + intent/state 기반 RECALL(Phase 1) + Folding + Memory Actions(Phase 2) + PRAXIS(Phase 3, 조건부 전술 저장소)
패치: hotfix09(원천) — InFi-Check FGFC(근거/오류타입/교정) 확장 계약 추가 + 관련 참조 갱신
패치: hotfix12 — Patterning(데이터 개입) 오프라인 계약(PatterningPlan) 추가
패치: hotfix12p1 — Verifier/Router 무(無)모델 기본값 + 에스컬레이션 지표/트리거(관측 가능성) 추가
> 이 파일은 Rulecraft v0.5.15의 **계약/스키마 단일 진실원천(SSOT)** 이다.
> Addendum(`Rulecraft_Addendum_0.5.15_rev15_memory_phase3_longcat2601_hotfix12p1.md`)의 §3은 이 파일의 핵심 내용을 발췌/요약하며, 불일치가 생기면 **이 파일을 먼저 수정**한다.

---

## 3.0 공통 규칙

- 모든 레코드는 `schema_version`(문자열)을 **MUST** 포함한다.
- 모든 ID는 안정적 식별자이며, `*_id`는 **MUST** 전역 유일(충돌 없음)해야 한다.
- `verdict == PASS` 이더라도 `outcome == FAIL`이면 pass가 아니다(§5.1의 pass 정의를 따른다).
- `bucket_key`는 최소한 `impact_level × domain_tag × user_clarity`로 구성되는 문자열을 **SHOULD** 포함한다.

> 아래 형태는 구현 언어/스토리지와 무관한 “계약 형태”이다.
> 실제 JSON Schema로 분리할 경우 필드명·의미는 동일해야 한다.


---

## 5) 파생 정의(derived semantics) — 불변 규율

> 아래 항목은 “필드 추가”가 아니라, 여러 컴포넌트가 **같은 의미**로 해석해야 하는 전역 정의다.
> 문서 내 다른 곳에서 §5.1 등을 참조할 때는 이 정의를 따른다.

### 5.1 PASS 정의 (전역)
Rulecraft 전체에서 “PASS(pass=1)”는 **Verifier의 verdict/outcome을 합성한 파생값**이다.

- `PASS := (verdict == "PASS") AND (outcome != "FAIL")`

의미:
- `outcome=="OK"`: 실행/근거로 **맞음이 확정**된 상태(가능하면 이 상태를 목표로).
- `outcome=="UNKNOWN"`: 검증 불가/불충분. `verdict`가 PASS이면 시스템은 “반증되지 않음”으로 PASS 처리하되,
  `should_scale`/재검증/추가 근거 요구 등 **운영 정책으로 보강**할 수 있다.
- `outcome=="FAIL"`: 틀림이 확인된 상태. 이 경우 `verdict`가 PASS여도 pass는 0이다.

### 5.2 violated_constraints 키 규범 (집계 가능성)
`VerifierResult.violated_constraints`는 운영/회귀/FlowMap 집계를 위해 **자유 서술이 아니라 안정적인 키**로 기록한다.

- 권장 형태: `PREFIX:SUB:DETAIL` (문자열)
  - 예: `SCHEMA:VerifierResult`, `FORMAT:JSON_ONLY`, `TOOL:CALL_REQUIRED:web.search_query`, `POLICY:NO_NETWORK`
- 키의 의미/범위는 `Rulecraft_Verifier_Spec_*`의 taxonomy와 일치해야 하며, 변경 시에는 **회귀/집계 코드도 같이 갱신**한다.

### 5.3 bucket_key 구성(최소 권장)
`EventLog.bucket_key`는 최소한 아래 3축을 포함하는 문자열을 권장한다.

- `impact_level × domain_tag × user_clarity`

예(표준은 아님, 가독성 우선):
- `I3|coding|clarity_low`
- `I1|general|clarity_high`
- `I2|math|clarity_med`

### 5.4 Verifier/Router “무(無)모델” 운영을 위한 파생 지표(derived observables)

Rulecraft는 기본적으로 Verifier/Router를 **코드 기반**으로 운영한다.  
따라서 “모델을 추가해야 하나?”는 주관이 아니라 **로그에서 계산되는 관측치**로 판단한다.

권장 파생 지표(집계는 EventLog + VerifierResult에서 계산):
- **unknown_rate**: `count(outcome=="UNKNOWN") / N`
- **exec_unavailable_rate**: `count(reason_codes contains one of {sandbox_denied,sandbox_timeout,exec_unavailable}) / N`
- **l1_violation_rate**: `count(violated_constraints != null) / N`  (형식/제약 위반 비율)
- **insufficient_evidence_rate**: `count(reason_codes contains "insufficient_evidence") / N`
- **cluster_recurrence**: 윈도우 내 `failure_cluster_id` 재발 빈도(상위 K개)
- **overinject_rate**(옵션): `count(reason_codes contains "memory_overinject" or "praxis_tactic_overinject") / N`

운영 해석(권장):
- `unknown_rate`가 높아도, 그 원인이 `exec_unavailable_rate`라면 “L2 붙이기”보다 **L3(하네스/샌드박스) 확보**가 우선이다.
- 반대로 `insufficient_evidence_rate`가 높고 L3로 확정이 불가능한 텍스트 태스크가 병목이면, 그때만 제한적으로 L2(저비용 grader)를 검토한다.

---

---

## 4) Memory Subsystem 계약 (Phase 0/1/2)

Rulecraft의 “메모리”는 감성적인 회상이 아니라, **실행 기반 재사용/학습을 위한 데이터 계약**이다.  
목표는 딱 4개:

1) 실행 기록을 구조화해(TraceCapsule/EventLog) **다음 런의 품질/비용을 낮춘다**  
2) 태스크 진행 중 컨텍스트를 WorkingSet으로 정리해 **현재 fold를 안정화**한다  
3) 장기 재사용 단위(에피소드/전술)를 ReasoningBank로 모아 **전술적 지식 베이스**를 만든다  
4) 즉시 재시드/프롬프트 prior 캐시를 ReuseBuffer로 유지해 **가성비 롤아웃**을 돕는다  

### 4.1 저장소 역할(Phase 0)

- **EventLog / TraceCapsule (저장소)**  
  - EventLog: 런의 **요약 메타**(선택된 룰, verifier 결과, 비용, rollout 선택 등)  
  - TraceCapsule: 런의 **상세 컨텍스트 캡슐**(주입/툴/출력/근거 참조). EventLog는 TraceCapsule을 `trace_id`로 조인한다.

- **WorkingSet (작업 메모리)**  
  - “현재 task fold 전”: 지금 수행 중인 문제에서 필요한 중간 상태/결정/가정/제약을 모은다.  
  - 원칙: *작게, 빠르게, 자주 갱신* (장기 기억 아님).

- **ReasoningBank (장기 메모리: 에피소드/전술)**  
  - 에피소드: “무엇을 했고 왜 통했는지” 요약(TraceCapsule ↔ EventLog ↔ 결과)  
  - 전술: 재사용 가능한 패턴(전략적 절차/체크리스트/검증 루틴/실험 설계)

- **Rulebook (승격 룰)**  
  - 장기 “규칙”은 RuleRecord로 승격/버전관리한다(=Rulebook은 RuleRecord의 저장소 역할).

- **ReuseBuffer (캐시: seed/prior + 조건부 전술)**  
  - 롤아웃/탐색 재시드용 seed/prior 상태(Phase 2까지) + PRAXIS의 조건부 전술(Phase 3)을 함께 담는다.
  - seed/prior는 `ReuseStateRecord`(PUCT로 선택), 조건부 전술은 `ConditionalTacticRecord`(intent/state로 리콜)로 구분한다.

### 4.2 메모리 오퍼레이션(Phase 0)

모든 저장소에서 아래 오퍼레이션은 **동일 의미**로 해석돼야 한다.

- **WRITE**: 새 레코드 생성(또는 동일 `memory_id`에 대한 버전 증가)  
- **PIN**: TTL/PRUNE 대상에서 제외(강한 보존)  
- **MERGE**: 여러 레코드를 합쳐 상위 요약(예: 여러 TraceCapsule → 에피소드)  
- **PRUNE**: 품질/신선도/중복 기준으로 삭제(또는 축약)  
- **RETIRE**: “삭제”가 아니라 **비활성화 상태로 보관**(재현성/감사를 위해)  
- **RECALL(intent,state)**: 아래 §4.3/§4.4 규율에 따른 검색/리콜

### 4.3 intent_key / state_key (Phase 1 핵심)

`bucket_key`가 “큰 바구니”라면, Phase 1의 핵심은 **리콜 오차를 줄이는 2중 키**다.

- **intent_key (안정)**: “무슨 종류의 일을 하려는가”  
  - 예: `(domain_tag, task_family, required_tools, output_format, constraint_profile)`를 기반으로 만든 문자열/해시
- **state_key (휘발)**: “지금 어떤 실행 상태인가”  
  - 예: `(run.mode, budget_tier, policy_profile, tool_availability, verifier_profile, sandbox_flags)` 등

원칙:
- intent_key는 **재사용 가능성**을 가르고, state_key는 **호환성(실행 가능성)** 을 가른다.
- 둘 다 없는 경우 Phase 1 리콜은 “의미 유사도만”으로 퇴행(fallback)해도 된다(하지만 성능은 당연히 떨어진다).

### 4.4 RECALL 규율: STITCH-style filter → rerank (Phase 1)

RECALL은 “검색”이 아니라 “재사용 후보를 안전하게 좁히는 의사결정”이다.

1) **Candidate Gather** (소스별 top-k’):  
   `ReasoningBank`, `Rulebook`, `ReuseBuffer`(tactic_entries, Phase 3), 필요 시 `TraceCapsule`(최근/핀된 것 우선)
   - seed/prior 재시드는 RECALL이 아니라 `reuse_select`(PUCT) 경로로 분리한다.

2) **Filter (호환성 컷)**:  
   - bucket_key/intent_key가 **명백히 불일치**하면 제거  
   - state_key 호환성(툴/모드/정책/제약)이 깨지면 제거  
   - (옵션) `PASS` 이력이 매우 낮거나 `RETIRE`된 항목은 기본 제외

3) **Rerank (가중 점수)**:  
   `S = w_sem*sim(query, summary) + w_int*sim(intent, mem_intent) + w_state*compat(state, mem_state) + w_qual*quality(mem)`  
   - quality(mem): pass_p_hat, cost 효율, recency, pinned bonus 등

4) **Return (MemoryHint)**:  
   - top-m을 `MemoryRecallResponse.items[]`로 반환(요약/이유/trace 참조 포함)  
   - 실제로 사용한 항목은 EventLog의 `memory_recall.used_ids`에 기록한다(관측 가능성).

#### 4.4.1 주입 예산(가벼운 메모리 기본값)

RECALL 산출물은 “좋은 글”이 아니라 **짧은 주입 단위**다. Runner는 주입 예산을 **MUST** 강제한다(단위는 tokens 또는 chars 중 하나로 통일).

권장 기본값(Policy로 조정 가능):
- `MemoryHint.summary`: **≤ 120 tokens** (또는 ≤ 600 chars)
- `ConditionalTacticRecord.injection.content`: **≤ 160 tokens** (또는 ≤ 800 chars)
- 한 run에서 (룰 제외) **메모리 주입 총합 ≤ 256 tokens**

상한 초과 시:
- 내용은 더 압축(compaction)하거나 `payload_ref`로 외부화하고, Runner는 초과분을 **잘라서 주입**한다.
- 장문 주입으로 컨텍스트가 오염되면, 그 순간부터 메모리는 “도움”이 아니라 “노이즈”다(인간과 LLM 모두에게).


### 4.5 Folding 규율 (Phase 2)

Folding은 “현재 task의 진행 상태(WorkingSet) + 실행 흔적(TraceCapsule/EventLog) + 검증 신호(VerifierResult)”를
**재사용 가능한 단위(ReasoningBank/ReuseBuffer)로 접어 넣는 과정**이다.

원칙:
- Folding은 **요약(summarize)** 이 아니라 **재사용 단위 생성(distill-for-reuse)** 이다.
- Folding 결과는 “자동 승격”이 아니라 **후보 생성 + 관측 가능 로그**로 남겨야 한다.

권장 트리거(trigger.kind):
- `end_of_run` (기본)
- `ws_overflow` (WorkingSet 과대)
- `fail_cluster` (유사한 violated_constraints/reason_codes 반복)
- `phase_shift` (probe→full, mode 전환 등)
- `manual` (운영자/테스트 하네스 강제)

Folding 산출물:
- `FoldResult` (무엇을 접었고 무엇을 생성했는지)
- (옵션) `MemoryActionPlan` (어떤 메모리 오퍼레이션을 실행할지)

### 4.6 Memory Actions: Plan → Apply → Record (Phase 2)

Phase 0/1에서 정의한 메모리 오퍼레이션(WRITE/PIN/MERGE/PRUNE/RETIRE)은 Phase 2에서 **자동 실행 가능 형태**가 된다.

- Planner는 `MemoryActionPlan`을 생성한다(“무엇을, 어디에, 왜”).
- Executor는 Plan을 적용하고 `MemoryActionRecord`로 결과를 남긴다.

안전장치(필수):
- **Rulebook 자동 승격 금지**: Phase 2는 Rulebook에 “draft/temporary 후보”를 만들 수는 있어도,
  `status=active` 승격은 **tests/게이트를 통과한 별도 루프**에서만 수행한다.
- **PRUNE는 PIN/보존 대상 제외**: `status=pinned` 또는 최소 TTL 보호 대상은 PRUNE하지 않는다.
- 기본은 **RETIRE 우선**(재현성/감사). PRUNE은 저장소 부하/중복이 명확할 때만 제한적으로 사용한다.
- 모든 적용 결과는 EventLog에 연결되어야 한다(관측 가능성).

### 4.7 EventLog 확장: memory_fold / memory_actions (Phase 2)

Phase 2의 Folding/Actions는 “오프라인 집계(FlowMap/회귀/정책 개선)”를 위해 반드시 로그로 남겨야 한다.

- EventLog.memory_fold: FoldResult 연결 + 산출물(ReasoningBank/ReuseBuffer 후보) 요약
- EventLog.memory_actions: Plan/Record 연결(적용 결과, 실패 원인 포함)


---


### 4.8 PRAXIS: 조건부 전술 저장소로의 확장 (Phase 3)

Phase 3의 목적은 ReuseBuffer를 단순한 seed/prior 캐시에서 끝내지 않고, **“조건부 전술(conditional tactics)”** 을 담는 재사용 저장소로 확장하는 것이다.

- **ConditionalTacticRecord**는 “언제(조건) + 무엇(짧은 전술) + 왜(근거/효율)”을 담는다.
- 저장 위치는 ReuseBuffer 내부의 `tactic_entries`이며, seed/prior(`seed_entries`)와 **혼합하지 않는다**.
- 사용 경로:
  - (리콜) Phase 1 `RECALL(intent,state)`에서 `ReuseBuffer`(tactic_entries) 소스로 후보를 모아 filter→rerank 후 top-m을 `MemoryHint`로 반환한다.
  - (갱신) Phase 2의 Folding/Actions가 끝날 때, `MemoryActionPlan`에 따라 `WRITE/MERGE/RETIRE/PIN`으로 전술을 기록/갱신한다.
- 안전 규율(필수):
  - Conditional tactics는 **룰이 아니다**. Rulebook의 `active` 승격과 동치로 취급하면 안 된다.
  - 주입은 “힌트/체크리스트/짧은 절차” 수준으로 제한한다(장문 금지, 과주입 금지).
  - 실패/충돌 시에는 `RETIRE`를 우선하고, `PRUNE`은 저장소 부하가 명확할 때만 제한적으로 수행한다.


## 스키마 목록


### RuleRecord
```yaml
RuleRecord:
  schema_version: "0.5.15"
  rule_id: string               # MUST
  version: string               # MUST (예: semver 또는 내부 버전)
  type: "StrategyRule" | "GuardrailRule"     # MUST
  status: "temporary" | "active" | "retired" # MUST

  title: string                 # SHOULD
  body: string                  # MUST (룰의 실제 텍스트/절차/금지사항)

  applicability:                # MUST
    domain_tag: string          # SHOULD
    task_family: string         # SHOULD
    predicates:                 # MAY (간단 규칙식 / feature predicate)
      - string
    bucket_keys:                # MAY (명시적 버킷 타겟)
      - string

  priority:                     # SHOULD (주입/적용 순서)
    guardrail_first: bool       # MUST (GuardrailRule이면 true 권장)
    rank: int                   # MAY

  evidence:                     # MUST (근거 링크)
    trace_ids: [string]         # SHOULD
    verifier_ids: [string]      # MAY
    regression_ids: [string]    # MAY

  tests:                        # MUST
    regression_tests: [string]        # MUST (없으면 empty)
    counterexample_tests: [string]    # MUST (없으면 empty)

  metrics:                      # MUST
    utility_q_ema: float               # SHOULD
    pass_p_hat: float | null           # SHOULD
    pass_p_lb95: float | null          # SHOULD
    pass_p_K: int | null               # SHOULD
    pass_p_bucket:                    # MAY
      "<bucket_key>":
        p_hat: float
        p_lb95: float
        K: int


    pass_p_bucket_delta:               # MAY (룰 적용 전후 변화 추정; replay/canary에서 갱신)
      "<bucket_key>":
        delta_p_hat: float|null
        delta_p_lb95: float|null
        delta_K: int|null
  lifecycle:                    # MAY
    created_at: string
    updated_at: string
    last_used_at: string
    retire_candidate: bool
```


### CandidateSelectRequest/Response
```yaml
CandidateSelectRequest:
  schema_version: "0.5.15"
  request_id: string        # MUST
  x_ref: string             # MUST (입력/태스크 식별자 또는 해시)
  bucket_key: string        # SHOULD
  context:
    impact_level: "low"|"med"|"high"   # SHOULD
    domain_tag: string                   # SHOULD
    user_clarity: "low"|"med"|"high"  # SHOULD
  constraints:
    max_rules: int          # MUST
    allow_types: ["StrategyRule","GuardrailRule"]  # MUST
    prompt_profile: string  # SHOULD

CandidateSelectResponse:
  schema_version: "0.5.15"
  request_id: string        # MUST
  selected_rules:           # MUST
    - rule_id: string
      version: string
      type: "StrategyRule"|"GuardrailRule"
      injection_mode: "prepend"|"inline"|"system_guard"  # MUST
      score: float          # SHOULD
      reasons: [string]     # MAY
  exploration:
    used_debias: bool       # SHOULD
    debias_weight: float|null
    used_novelty: bool|null     # MAY (mode collapse 방지용 탐색 신호)
    novelty_weight: float|null  # MAY (보상/선택에서 novelty 가중치)
    diversity_score: float|null # MAY (집단 내 유사도↓일수록↑ 같은 얕은 지표)
```


### VerifierResult
```yaml
VerifierResult:
  schema_version: "0.5.15"
  verifier_id: string       # MUST
  verdict: "PASS"|"FAIL"|"PARTIAL"   # MUST
  outcome: "OK"|"FAIL"|"UNKNOWN"      # MUST
  score: float|null             # SHOULD (0~1, 선별/스케일링에 쓰는 주 점수)
  score_method: "yes_logit"|"pairwise_rank"|"rule_check"|"hybrid"|null  # MAY
  score_evidence: object|null   # MAY (예: {yes_logit:float, confidence:float})
  failure_cluster_id: string|null       # MAY
  notes: string|null        # MAY
  reason_codes: [string]|null          # SHOULD (FAIL/PARTIAL 시 최소 1개 권장)
  violated_constraints: [string]|null  # MAY (정적 규칙/제약 위반 목록)
  fgfc: object|null   # MAY (Fine-Grained Fact Checking payload; see FGFCReport)
  scores:                   # MAY
    holdout_score: float|null
    safety_score: float|null
```


### FGFCReport (Fine-Grained Fact Checking) — optional extension

> 목적: Verifier가 단순 PASS/FAIL을 넘어서, **어디가 어떻게 틀렸는지(세부 오류 타입) + 근거 + 교정안**을 구조화해 반환할 수 있게 한다.
> 기본 아이디어는 InFi-Check(2601.06666)의 “fine-grained fact-check” 출력 형태와 호환된다.

```yaml
FGFCReport:
  schema_version: "0.5.15"
  mode: "infi_check_v1"            # 고정 문자열(호환성 키)
  unitization: "sentence"|"atomic_claim"  # 권장: sentence부터 시작
  units:
    - unit_id: string              # 예: "s0", "s1" (candidate 내부 단위)
      text: string
      verdict: "SUPPORTED"|"REFUTED"|"NOT_ENOUGH_INFO"
      error_type: "PredE"|"EntE"|"CircE"|"CorefE"|"LinkE"|"OutE"|null  # REFUTED 시 권장
      evidence:
        - source: "x_ref"|"artifact"|"tool"
          ref: string              # 예: "x_ref:doc#p3" / "artifact:testlog#L120-L140"
          quote: string|null       # 25단어 이내 권장(집계/검토용)
      justification: string|null   # 짧게(요약형)
      correction: string|null      # 교정문(가능하면 최소 수정)
  overall:                          # 단순 집계(옵션)
    supported: int|null
    refuted: int|null
    nei: int|null
  metrics:                          # 평가/오프라인에서 주로 사용(옵션)
    sar: float|null                 # 판정-근거 정합성(Strict/Normal 비율 등)
    strict_acc: float|null          # 단위+타입까지 맞춘 정확도(벤치마크용)
```

권장 매핑(집계용):
- `error_type → reason_codes` (예시)
  - PredE → `fact_predicate_mismatch`
  - EntE  → `fact_entity_mismatch`
  - CircE → `fact_circumstance_mismatch`
  - CorefE→ `fact_coreference_mismatch`
  - LinkE → `fact_discourse_link_mismatch`
  - OutE  → `fact_extrinsic_claim`



- `search/prover → reason_codes` (예시)
  - Search budget 소진 → `search_budget_exhausted`
  - 외부 prover/solver 불완전(unknown/incomplete) → `prover_incomplete`
  - prover가 증명을 찾지 못함(시간/깊이 내) → `proof_not_found`

### EventLog
```yaml
EventLog:
  schema_version: "0.5.15"
  trace_id: string          # MUST
  x_ref: string             # MUST
  bucket_key: string        # SHOULD

  flow_tags: [string]|null     # MAY (예: planner-heavy, tool-heavy, verifier-heavy)
  policy_signals:              # MAY (FlowMap/Policy 입력 투명화)
    risk_score: float|null
    opp_score: float|null
    efficiency: float|null

  selected_rules:              # MUST (CandidateSelectResponse의 일부 미러)
    - rule_id: string
      version: string
      type: string

  # (옵션) 실행-기반 평가/탐색 컨텍스트(Execution-grounded loop)
  experiment:                  # MAY
    kind: "policy_search"|"execution_eval"|"rule_evolve"|"scaling_law"|null
    harness_id: string|null
    idea_id: string|null
    search_epoch: int|null
    population_id: string|null
    parent_ids: [string]|null
    mutation_ops: [string]|null
    exec_ok: bool|null
    exec_failure_class: string|null
    reward:                    # MAY
      total: float|null
      pass: float|null
      cost: float|null
      diversity: float|null
      consistency: float|null

  # (옵션) ReuseBuffer에서 seed를 선택해 롤아웃/탐색을 '재시드'한 경우의 선택 메타데이터
  reuse_select:                        # MAY
    enabled: bool|null                 # MAY
    policy: string|null                # MAY (예: "puct_maxq_rankprior_v1")
    selected_state_id: string|null     # MAY
    selected_score: float|null         # MAY (PUCT score)
    puct:                              # MAY
      c: float|null                    # MAY (exploration constant)
      Q_method: "max_reward"|"mean_reward"|null   # MAY
      P_method: "rank_prior"|"uniform"|null       # MAY
      Q: float|null                    # MAY (selected state's Q)
      P: float|null                    # MAY (selected state's P)
      T_total: int|null                # MAY (총 선택 횟수)
      N: int|null                      # MAY (selected state's 선택 횟수)


  # (옵션) Guided Tree Search 메타데이터 (형식-검증 가능한 도메인용)
  tree_search:                         # MAY
    enabled: bool|null                 # MAY
    algo: string|null                  # MAY (예: "puct_guided_tree_v1", "beam_guided_tree_v1")
    node_expanded: int|null            # MAY
    depth_max: int|null                # MAY
    frontier_max: int|null             # MAY
    best_node_ref: string|null         # MAY (예: trace_id:step#k 또는 외부 저장소 ref)
    notes: string|null                 # MAY



  # (옵션) Phase3 PRAXIS 조건부 전술 리콜/사용 메타데이터
  praxis:                              # MAY
    enabled: bool|null                 # MAY
    policy: string|null                # MAY (예: "praxis_conditional_tactics_v1")
    retrieved_tactic_ids: [string]|null # MAY (top-k 후보)
    used_tactic_ids: [string]|null      # MAY (실제로 주입/참조한 전술)
    top_scores: [float]|null            # MAY (retrieved와 동일 순서)
    notes: string|null                  # MAY (failover, override 등)

  # (옵션) Phase1 메모리 RECALL 메타데이터 (intent/state 기반)
  memory_recall:                      # MAY
    enabled: bool|null                # MAY
    method: string|null               # MAY (예: "intent_state_recall_v1")
    intent_key: string|null           # MAY
    state_key: string|null            # MAY
    sources: [string]|null            # MAY (예: ["ReasoningBank","Rulebook","ReuseBuffer","TraceCapsule"])
    retrieved_ids: [string]|null      # MAY (top-k 후보)
    used_ids: [string]|null           # MAY (실제로 주입/참조한 항목)
    top_scores: [float]|null          # MAY (retrieved_ids와 동일 순서)
    notes: string|null                # MAY (failover, override 등)

  # (옵션) Phase2 Folding + Memory Actions 메타데이터
  memory_fold:                        # MAY
    enabled: bool|null                # MAY
    fold_id: string|null              # MAY (FoldResult.fold_id)
    trigger_kind: string|null         # MAY (예: "end_of_run", "ws_overflow")
    ws_id: string|null                # MAY (WorkingSet.current_ws_id 등)
    produced_reasoning_ids: [string]|null   # MAY (ReasoningMemoryRecord ids)
    produced_rule_draft_ids: [string]|null  # MAY (DistillDraft.draft_id 등)
    produced_reuse_state_ids: [string]|null # MAY (ReuseStateRecord ids)
    action_plan_id: string|null       # MAY (MemoryActionPlan.plan_id)
    action_record_ids: [string]|null  # MAY (MemoryActionRecord.op_id 리스트)
    notes: string|null                # MAY

  memory_actions:                     # MAY (Phase2)
    enabled: bool|null                # MAY
    plan_id: string|null              # MAY
    op_ids: [string]|null             # MAY
    notes: string|null                # MAY


  run:
    mode: "main"|"sot"|"matts"|"kroll"|"synth"|"tree"    # MUST
    cfg:                               # MAY (jitter, seed 등)
      seed_prompt: string|null
      tool_order: string|null
      temperature: float|null
      plan_style: string|null
      self_refine_steps: int|null

  sandbox:                              # MAY (LLM-in-Sandbox)
    enabled: bool|null
    image_id: string|null               # 예: docker image digest/tag
    network: "off"|"allowlist"|"on"|null
    allowlist: [string]|null
    turns: int|null                     # sandbox interaction turns
    actions_n: int|null                 # tool actions (bash/edit)
    files_read_n: int|null
    files_written_n: int|null
    external_fetch_n: int|null          # network fetch count (if any)
    exec_fail_n: int|null
    traces_ref: [string]|null           # SandboxActionTrace ids (separate store)

  sot_profile: string|null           # MAY (예: "sot_mini_v1")
  sot_max_turns: int|null            # MAY (예: 2~3)

  outputs:
    y_ref: string|null                   # SHOULD (결과 참조)
    rollout_summary: RolloutSummary|null # SHOULD (kroll/matts에서 요약 메시지)
    sot_signals: object|null             # SHOULD (sot에서 대화 행동 신호: qa/shift/conflict/reconcile 등)
    synth_inputs:                        # MAY (synth에서 사용한 메시지 참조)
      used_trace_ids: [string]|null
      used_summary_ids: [string]|null

  verifier:                             # MUST
    verifier_id: string
    verdict: string
    outcome: string

  cost:                                 # SHOULD
    latency_ms: int|null
    tokens_in: int|null
    tokens_out: int|null
    tool_calls: int|null

  rollout_select:                        # MAY (K-rollout 결과 선별 메타; 요약 공간 TTS)
    rollouts_n: int|null                 # MAY (생성된 rollout 수)
    top_m: int|null                      # MAY (synth 입력으로 선택된 요약 수)
    selection_method: string|null        # MAY (예: "score+diversity")
    selected_summary_ids: [string]|null  # MAY
    diversity_score: float|null          # MAY (선별된 집합 기준)

  repr:                                  # MAY (Representation Space 캐시 참조)
    encoder_id: string|null
    dim: int|null
    x_vec_id: string|null
    y0_vec_id: string|null
    summary_vec_ids: [string]|null
```



### TraceCapsule
```yaml
TraceCapsule:
  schema_version: "0.5.15"
  trace_id: string                 # MUST (EventLog.trace_id와 조인)
  created_at: string               # MUST (ISO8601)

  bucket_key: string|null          # SHOULD (EventLog.bucket_key와 일치 권장)
  intent_key: string|null          # MAY
  state_key: string|null           # MAY

  # 저장은 "참조(ref)" 중심. 원본은 별도 스토리지(파일/DB/오브젝트)에 둘 수 있다.
  refs:
    x_ref: string|null             # MAY (입력 원문/요약 참조)
    injection_ref: string|null     # MAY (주입된 룰/메모리 스니펫 참조)
    tool_trace_refs: [string]|null # MAY (SandboxActionTrace ids 등)
    y_ref: string|null             # MAY (출력 원문/요약 참조)
    verifier_ref: string|null      # MAY (Verifier 상세 로그 참조)

  # RECALL/주입에 실제로 쓰인 항목 기록(관측 가능성)
  used_memory_ids: [string]|null   # MAY
  used_rule_ids: [string]|null     # MAY

  # 민감정보/대형텍스트는 기본적으로 여기에 넣지 말고 refs로 분리한다.
  notes: string|null               # MAY
```


### FoldResult
```yaml
FoldResult:
  schema_version: "0.5.15"
  fold_id: string                 # MUST
  created_at: string              # MUST (ISO8601)

  trigger:                        # MUST
    kind: "end_of_run"|"phase_shift"|"ws_overflow"|"budget_hit"|"fail_cluster"|"manual"
    details: string|null          # MAY

  ws_id: string|null              # MAY (WorkingSet.current_ws_id 등)
  trace_id: string|null           # MAY (대표 TraceCapsule)
  bucket_key: string|null         # MAY
  intent_key: string|null         # SHOULD
  state_key: string|null          # SHOULD

  produced:                       # MUST (생성/갱신된 메모리 단위 연결)
    reasoning_ids: [string]|null        # MAY (ReasoningMemoryRecord ids)
    rule_draft_ids: [string]|null       # MAY (DistillDraft.draft_id 등)
    reuse_state_ids: [string]|null      # MAY (ReuseStateRecord ids)

  action_plan_id: string|null     # MAY (MemoryActionPlan.plan_id)
  notes: string|null              # MAY
```

### MemoryActionPlan
```yaml
MemoryActionPlan:
  schema_version: "0.5.15"
  plan_id: string                 # MUST
  created_at: string              # MUST (ISO8601)

  fold_id: string|null            # MAY (FoldResult.fold_id)
  bucket_key: string|null         # MAY
  intent_key: string|null         # SHOULD
  state_key: string|null          # SHOULD

  actions:                        # MUST
    - op: "WRITE"|"PIN"|"MERGE"|"PRUNE"|"RETIRE"   # MUST
      target_store: "ReasoningBank"|"Rulebook"|"ReuseBuffer"|"TraceCapsule"   # MUST
      target_ids: [string]|null   # MAY
      payload_ref: string|null    # MAY (요약/절차/프롬프트/코드 등 외부 참조)
      reason_keys: [string]|null  # MAY (집계 가능한 안정 키)
      safety:                     # MAY
        dry_run: bool|null
        ttl_days: int|null
        max_bytes: int|null

  notes: string|null              # MAY
```

### MemoryActionRecord
```yaml
MemoryActionRecord:
  schema_version: "0.5.15"
  op_id: string                   # MUST
  created_at: string              # MUST (ISO8601)

  plan_id: string|null            # MAY
  fold_id: string|null            # MAY

  op: "WRITE"|"PIN"|"MERGE"|"PRUNE"|"RETIRE"       # MUST
  status: "APPLIED"|"SKIPPED"|"FAILED"             # MUST
  target_store: string            # MUST
  target_ids: [string]|null       # MAY
  produced_ids: [string]|null     # MAY

  reason_keys: [string]|null      # MAY
  error: string|null              # MAY
```


### DistillDraft
```yaml
DistillDraft:
  schema_version: "0.5.15"
  draft_id: string              # MUST
  source_trace_ids: [string]    # MUST
  proposed_rule:                # MUST (RuleRecord의 부분집합)
    type: "StrategyRule"|"GuardrailRule"
    title: string
    body: string
    applicability: object
  evidence: object              # MUST

  # v0.5.15-addendum(rev03, 이전) 강화: “설명→실패예측→반례”를 Distiller 산출물 규격으로 포함(승격 게이트에서 사용)
  failure_prediction:           # SHOULD (승격 후보라면 사실상 REQUIRED)
    mechanism: string           # SHOULD  (작동 가설: 왜 먹히는가)
    dependencies: [string]      # SHOULD  (의존성: tool/router/format/memory 등)
    predicted_failures:         # SHOULD  (최소 2개 권장)
      - id: string              # taxonomy id (예: context_dilution, instruction_conflict...)
        description: string
        triggers: [string]
        severity: "low"|"med"|"high"

  # v0.5.15-addendum(rev03, 이전) 강화: Micro-Regression 팩 선택(테스트 자동 생성용)
  micro_regression_packs: [string]  # MAY (예: ["FORMAT","TOOL","BUDGET"])

  tests:                        # MUST
    regression_tests: [string]        # SHOULD (micro-regression 포함 권장)
    counterexample_tests: [string]    # SHOULD (>=2: cluster 1 + boundary 1 권장)
```




### PatterningPlan (optional extension) — Patterning(데이터 개입) 오프라인 산출물 계약

> 목적: “원하는 행동/일반화”를 만들기 위해 **데이터 믹싱/가중치**를 역으로 설계한다.  
> 런타임 컴포넌트가 아니라, Distiller/Trainer가 로그/회귀 결과를 기반으로 만드는 **오프라인 레시피**다.

```yaml
PatterningPlan:
  schema_version: "0.5.15"
  patterning_id: string                 # MUST
  generated_at: string                  # MUST (ISO8601)
  base_dataset: string                  # MUST (예: distill_v3, regress_v2)

  # 개입 레버: 데이터 슬라이스/생성기/템플릿의 혼합 비율
  probes:                               # MUST (K개)
    - probe_id: string                  # MUST
      description: string               # SHOULD
      slice_query: string|null          # MAY  (bucket_key/reason_code/tag 등)
      max_weight: float|null            # MAY  (상한, 클립용)

  # 관측치(Observable): Rulecraft에서는 내부 구조 대신 “행동 프록시”로 둔다
  observables:                          # MUST (I개)
    - obs_id: string                    # MUST
      kind: "pass_rate"|"unknown_rate"|"reason_code_rate"|"avg_cost"|"custom"
      bucket_key: string|null           # MAY
      reason_code: string|null          # MAY (kind=reason_code_rate)
      target_value: float|null          # MAY (절대 목표)
      target_delta: float|null          # MAY (상대 목표, dμ_target)

  chi_estimation:                       # MUST
    method: "finite_diff"|"grad_proxy"  # MUST
    epsilon: float|null                 # SHOULD (finite_diff일 때)
    regularizer: float|null             # SHOULD (pinv 안정화: ridge)
    condition_number: float|null        # MAY
    notes: string|null                  # MAY

  solution:                             # MUST (dh)
    weights: [float]                    # MUST (probes와 같은 길이)
    clipped: bool                       # MUST
    renormalized: bool                  # MUST

  validation:                           # MUST
    canary_suite_id: string|null        # SHOULD
    replay_window: object|null          # MAY
    rollback_on_regress: bool           # MUST
    results: object|null                # MAY (pass/unknown/cost 변화 요약)

  applied: bool                         # MUST
  notes: string|null                    # MAY
```

#### PatterningPlan 규범
- `PatterningPlan`은 **MUST** 오프라인에서만 생성/적용한다.
- 적용은 **MUST** `replay → canary → rollback`(Playbook §15.6) 순서를 따른다.
- `weights`는 **MUST** 클립/정규화(폭주 방지) 후 기록한다.
- `reason_code_rate`를 observable로 쓸 경우, Verifier는 taxonomy를 안정적으로 유지하는 것을 **SHOULD** 한다(Verifier Spec §5.5).

---


### RegressionTestSpec
```yaml
RegressionTestSpec:
  schema_version: "0.5.15"
  test_id: string                 # MUST
  test_type: "regression"|"counterexample"   # MUST
  severity: "critical"|"normal"              # SHOULD

  # 입력 참조: 기존 x_ref 유지(SSOT). 필요 시 prompt를 inline으로 둘 수도 있음(옵션).
  x_ref: string                   # MUST
  prompt: string|null             # MAY (포터블/오픈소스 배포용으로 inline 제공 가능)

  # v0.5.15-addendum(rev03, 이전) 강화: Micro-Regression 자동 채점을 위한 assertion(가능한 경우)
  assert:                         # MAY
    type: "json_schema"|"regex_present"|"regex_absent"|"tool_called"|"tool_not_called"|"length_lte"|"exact_match"|"contains"
    args: object

  # v0.5.15-addendum(rev03, 이전) 강화: 반례는 최소한 cluster/boundary를 구분하면 운영이 편해짐
  kind: "cluster"|"boundary"|"transform"|null   # MAY

  tags: [string]|null            # MAY (예: ["context_dilution","format_leak"])
  expected:
    must_pass: bool               # MUST
    notes: string|null            # MAY
  linked_rule_ids: [string]       # SHOULD
```


### RolloutSummary
```yaml
RolloutSummary:
  schema_version: "0.5.15"
  summary_id: string            # MUST
  trace_id: string              # MUST (요약이 생성된 실행 trace)

  answer: string                # MUST (한 줄 답 후보)
  key_reasoning:                # MUST (핵심 근거 1~3줄)
    - string
  assumptions:                  # SHOULD (가정/해석 포인트)
    - string
  checks:                       # SHOULD (반례/엣지/검증 포인트)
    - string
  confidence: float             # SHOULD (0~1)

  verifier_score: float|null     # MAY (VerifierResult.score 미러)
  selection_score: float|null    # MAY (top-m 선택 점수: score+diversity-penalty)
  repr:                          # MAY (RepSpace 참조; 요약 공간 TTS용)
    encoder_id: string|null
    dim: int|null
    summary_vec_id: string|null

  verifier_mirror:              # SHOULD (요약 생성 시점의 검증 요약)
    verdict: "PASS"|"FAIL"|"PARTIAL"
    outcome: "OK"|"FAIL"|"UNKNOWN"

  compaction_policy:            # SHOULD
    max_tokens: int|null        # SHOULD (요약 상한)
    forbid_cot: bool            # MUST (true 권장)
    format: string|null         # MAY (template id)
```


### FlowMapSnapshot
```yaml
FlowMapSnapshot:
  schema_version: "0.5.15"
  generated_at: string                 # MUST
  window:
    start_at: string                   # MUST
    end_at: string                     # MUST
  bucket_key: string                   # MUST

  estimator:                           # MAY
    kind: string                        # 예: "aggregate_v1" | "nn_field_v1"
    model_ref: string|null              # MAY (아티팩트 id/path/hash)
    feature_set: string|null            # MAY (입력 피처 세트 id)
    calibration: string|null            # MAY (보정/캘리브레이션 메모)

  risk:                                # MUST
    stage_hotspots:                    # SHOULD (상위 K개)
      - stage: string                  # 예: main→verify, synth→verify
        reason_code: string|null       # 예: format_leak, tool_misroute
        risk_rate: float               # (verdict∈{FAIL,PARTIAL} OR outcome∈{FAIL,UNKNOWN}) 비율
        support_n: int                 # 표본 수

  opportunity:                         # MUST
    interventions:                     # SHOULD
      - intervention: string           # 예: SoT-1pass, K_probe, K_full+synth
        gain_pass: float               # 개입 전후 PASS 회복(또는 품질 상승) 추정
        delta_cost: float              # 추가 비용(토큰/지연/툴콜 등) 추정
        efficiency: float              # gain_pass / max(delta_cost, ε)
        support_n: int

  notes: string|null                   # MAY
```


### ReuseStateRecord
```yaml
ReuseStateRecord:
  schema_version: "0.5.15"
  state_id: string                       # MUST (예: "rs_01H...")
  created_at: string                     # MUST (ISO8601)
  bucket_key: string|null                # MAY
  seed_summary: string                   # MUST (짧은 상태 요약. 비밀/민감정보 금지)
  seed_prompt: string|null               # MAY (프롬프트 prefix로 직접 쓰고 싶다면)
  source_trace_ids: [string]|null        # MAY (어떤 로그에서 유래했는지)
  rule_set_hash: string|null             # MAY (주입된 룰 집합의 해시/버전)

  verifier:                              # MAY
    verdict: "PASS"|"PARTIAL"|"FAIL"|null
    outcome: "OK"|"UNKNOWN"|"FAIL"|null
    score: float|null
    score_method: string|null

  reward:                                # MAY (Execution-grounded loop과 정렬)
    total: float|null
    pass: float|null
    cost: float|null
    diversity: float|null
    consistency: float|null

  exec_ok: bool|null                     # MAY
  exec_failure_class: string|null        # MAY

  lineage:                               # MAY
    parent_state_id: string|null
    parent_ids: [string]|null
    mutation_ops: [string]|null

  counters:                              # MAY (PUCT용)
    N: int|null                          # 선택 횟수(노드 방문)
    last_used_at: string|null

  ttl: string|null                       # MAY (예: "days:7")
  tags: [string]|null                    # MAY
```


### ConditionalTacticRecord (Phase 3)
```yaml
ConditionalTacticRecord:
  schema_version: "0.5.15"
  tactic_id: string                    # MUST
  created_at: string                   # MUST (ISO8601)
  bucket_key: string|null              # MAY
  intent_key: string|null              # MAY
  state_key: string|null               # MAY

  status: "active"|"pinned"|"retired"  # MUST
  ttl: string|null                     # MAY (예: "days:14")
  last_used_at: string|null            # MAY

  summary: string                      # MUST (짧은 전술 요약)
  injection:                           # MUST (주입 단위)
    mode: "prepend"|"inline"|null      # MAY
    content: string                    # MUST (짧은 절차/체크리스트/힌트)

  predicates: [string]|null            # MAY (간단 조건식/태그)
  evidence:                            # MAY
    trace_ids: [string]|null
    verifier_ids: [string]|null

  metrics:                             # MAY
    pass_p_hat: float|null
    efficiency_est: float|null         # (gain/cost) 추정
    avg_cost: float|null
    use_n: int|null
    fail_n: int|null

  embedding_ref: string|null           # MAY
  payload_ref: string|null             # MAY
```

### ReuseBuffer
```yaml
ReuseBuffer:
  schema_version: "0.5.15"
  buffer_id: string                      # MUST
  policy_id: string                      # MUST
  max_size: int                          # MUST
  eviction: "lru"|"score_decay"|"hybrid"|null     # MAY

  # Phase 2까지: 탐색/롤아웃 재시드용 seed/prior
  seed_entries: [ReuseStateRecord]       # MUST

  # Phase 3(PRAXIS): 조건부 전술(힌트/절차) 저장소
  tactic_entries: [ConditionalTacticRecord]   # MUST

  stats:                                 # MAY
    seed_size: int|null
    tactic_size: int|null
    last_compact_at: string|null
```


### ReuseSelectMeta
```yaml
ReuseSelectMeta:
  schema_version: "0.5.15"
  enabled: bool
  policy: string
  selected_state_id: string|null
  selected_score: float|null
  puct:
    c: float|null
    Q_method: "max_reward"|"mean_reward"|null
    P_method: "rank_prior"|"uniform"|null
    Q: float|null
    P: float|null
    T_total: int|null
    N: int|null
```



### WorkingSetRecord / WorkingSet
```yaml
WorkingSetRecord:
  schema_version: "0.5.15"
  ws_id: string                    # MUST
  trace_id: string|null            # MAY (현재 런과 연결)
  bucket_key: string|null          # SHOULD
  intent_key: string|null          # MAY
  state_key: string|null           # MAY

  status: "active"|"retired"       # MUST
  ttl: string|null                 # MAY (예: "session", "hours:6")
  updated_at: string|null          # MAY

  # 현재 fold의 핵심 중간상태(작게 유지)
  facts: [string]|null             # MAY (확정 사실)
  assumptions: [string]|null       # MAY (가정)
  constraints: [string]|null       # MAY (제약)
  decisions: [string]|null         # MAY (분기/선택)
  open_questions: [string]|null    # MAY (미해결)

WorkingSet:
  schema_version: "0.5.15"
  current_ws_id: string|null       # MAY
  stack: [string]|null             # MAY (ws_id 스택)
```

### ReasoningMemoryRecord / ReasoningBank
```yaml
ReasoningMemoryRecord:
  schema_version: "0.5.15"
  memory_id: string                # MUST
  kind: "episode"|"tactic"         # MUST
  created_at: string               # MUST
  updated_at: string|null          # MAY

  bucket_key: string|null          # SHOULD
  intent_key: string|null          # SHOULD
  state_key: string|null           # MAY

  status: "active"|"pinned"|"retired"|"temporary"  # MUST
  ttl: string|null                 # MAY

  summary: string                  # MUST (짧은 재사용 단위)
  tags: [string]|null              # MAY (domain/tool/output/constraint 등)
  trace_ids: [string]|null         # MAY (근거 TraceCapsule/EventLog 연결)

  # 품질/가성비 통계(옵션)
  pass_p_hat: float|null           # MAY (0~1, 경험적 성공률)
  avg_cost: float|null             # MAY (상대값/정규화 가능)
  last_used_at: string|null        # MAY

  embedding_ref: string|null       # MAY (벡터 저장 참조)
  payload_ref: string|null         # MAY (상세 절차/코드/프롬프트 등 외부 참조)

ReasoningBank:
  schema_version: "0.5.15"
  bank_id: string                  # MUST
  policy: string|null              # MAY (예: "episodic+tactic_v1")
  max_items: int|null              # MAY
  items: [ReasoningMemoryRecord]   # MUST
```

### MemoryRecallRequest/Response (RECALL 계약)
```yaml
MemoryRecallRequest:
  schema_version: "0.5.15"
  request_id: string               # MUST
  trace_id: string|null            # MAY
  query: string                    # MUST (리콜 질의/요구)
  bucket_key: string|null          # SHOULD
  intent_key: string|null          # MAY
  state_key: string|null           # MAY
  sources: [string]|null           # MAY (기본: ReasoningBank/Rulebook/ReuseBuffer)
  top_k: int|null                  # MAY
  filters: object|null             # MAY (status/ttl/tool/output 등)

MemoryHint:
  memory_id: string                # MUST
  source: string                   # MUST ("ReasoningBank"|"Rulebook"|"ReuseBuffer"|"TraceCapsule")
  score: float|null                # MAY
  reason: string|null              # MAY (왜 올라왔는지)
  summary: string|null             # MAY (주입 가능한 짧은 요약)
  trace_ids: [string]|null         # MAY

MemoryRecallResponse:
  schema_version: "0.5.15"
  request_id: string               # MUST
  items: [MemoryHint]              # MUST
  method: string|null              # MAY
  fallback_used: bool|null         # MAY
```

### SandboxPolicy
```yaml
SandboxPolicy:
  schema_version: "0.5.15"
  enabled: bool                # SHOULD
  image_id: string|null        # SHOULD (docker image digest/tag)
  network: "off"|"allowlist"|"on"  # SHOULD
  allowlist: [string]|null     # MAY
  caps:                        # SHOULD
    max_turns: int|null
    wall_ms: int|null
    cpu_ms: int|null
    mem_mb: int|null
    disk_mb: int|null
  toolset: ["execute_bash","str_replace_editor","submit"]  # SHOULD (논문 기본)
  workdir: string|null         # MAY (예: /testbed)
```


### SandboxActionTrace
```yaml
SandboxActionTrace:
  schema_version: "0.5.15"
  trace_id: string             # MUST (EventLog.trace_id와 연결)
  action_id: string            # MUST
  turn: int                    # MUST
  tool: "execute_bash"|"str_replace_editor"|"submit"   # MUST
  args: object                 # SHOULD (민감정보는 redaction)
  obs:
    ok: bool                   # MUST
    exit_code: int|null        # MAY
    stdout_digest: string|null # SHOULD (해시/요약)
    stderr_digest: string|null # SHOULD
    error_class: string|null   # MAY
  io:
    files_read: [string]|null      # MAY
    files_written: [string]|null   # MAY
    bytes_read: int|null           # MAY
    bytes_written: int|null        # MAY
  net:
    used: bool|null                # MAY
    fetch_n: int|null              # MAY
    domains: [string]|null         # MAY
```