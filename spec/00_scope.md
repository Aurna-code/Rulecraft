# Rulecraft Intermediate Spec Pack (ISP) — v0.5.15-m0

## 목표
- 문서(SSOT/Addendum/Verifier Spec)의 핵심을 코드로 내리기 전에,
  구현자가 흔들릴 구간을 “계약+불변식+결정표+테스트”로 고정한다.
- Codex/사람 모두가 '상상으로 빈칸을 메꾸는' 걸 금지한다.

## 비범위
- K-rollout, synth, PaCoRe-lite, TreeSearch, Patterning 같은 고급 루프 구현은 여기서 안 한다.
- 대신 그 기능들이 꽂힐 자리(필드/인터페이스/로그)만 계약으로 박는다.

## 정의
- schema_version: "0.5.15" 고정
- PASS 정의: PASS := (verdict=="PASS") AND (outcome!="FAIL")
- Verifier 기본: 무(無)모델 운영이 default. L2는 기본 OFF. L3는 가능하면 붙이는 쪽.

## 성공 조건
- Acceptance tests(40_acceptance_tests.md)에 적힌 테스트가 모두 통과.
- EventLog JSONL이 남아 재현/집계 가능.
- Verifier가 UNKNOWN을 숨기지 않고 드러내며, Router가 그 신호로 스케일/중단을 계산.
