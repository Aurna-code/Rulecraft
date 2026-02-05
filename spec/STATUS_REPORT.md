# STATUS REPORT — SSOT07 vs SSOT08(hotfix13) 혼입 판정

| 항목 | 판정 | 근거 (파일 + 스니펫) |
| --- | --- | --- |
| A. 문서 기준 버전(SSOT/Verifier/Playbook/Addendum 파일명) | SSOT07 계열 | `Rulecraft_SSOT_0.5.15_ssot07_memory_phase3_hotfix12p1.md`<br>`Rulecraft_Verifier_Spec_r06_memory_phase3_longcat2601_hotfix12p1.md`<br>`Rulecraft_Playbook_r15_memory_phase3_longcat2601_hotfix12p1.md`<br>`Rulecraft_Addendum_0.5.15_rev15_memory_phase3_longcat2601_hotfix12p1.md` |
| B. EventLog 저장 포맷 (nested vs flat+dotted) | **Nested(run.mode)** 단일화 | `contracts/eventlog.schema.json`<br>```json
"run": {"type": "object", "required": ["mode"]}
``` |
| C. fixtures에 tree_search / memory_recall / praxis 이벤트 존재 여부 | **있음** | `fixtures/eventlog_with_tree_search.json`<br>```json
"run": {"mode": "tree"}
```<br>`fixtures/eventlog_with_memory_recall.json`<br>```json
"memory_recall_used_ids": ["mem_rule_1"]
```<br>`fixtures/eventlog_with_praxis.json` |
| D. selected_rules 객체 리스트 고정 여부 | **고정** | `contracts/eventlog.schema.json`<br>```json
"selected_rules": {"items": {"required": ["rule_id","version","type"]}}
``` |
| E. policy/verifier가 FAIL/insufficient_evidence 신호로 run.mode escalation 수행 여부 | **수행함** | `rulecraft/policy.py`<br>```python
if verifier.verdict == "FAIL":
    return "tree"
```<br>`rulecraft/verifier.py`<br>```python
reason_codes.append("insufficient_evidence")
``` |

## hotfix13 업그레이드에서 깨질 포인트 (사전 봉합)
- **run.mode dotted key**: hotfix13에서 nested(run:{mode}) 표준화가 예상되므로, 산출물은 nested로 고정하고 dotted key는 출력하지 않는다.
- **EventLog strict schema**: additionalProperties=false를 유지하여 계약 위반이 조기에 드러나도록 고정.
- **selected_rules 타입**: string[]로 회귀하는 변경은 schema에서 차단.

## additionalProperties 결정
- `contracts/eventlog.schema.json`은 **additionalProperties=false**로 설정했다. (reason: 계약 위반을 빠르게 드러내기 위한 엄격 모드)
