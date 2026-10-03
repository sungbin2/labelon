# Cycle 3 Code Summary - 검수 가이드 반영

생성일: 2026-09-28. 계획: `cycle3-code-generation-plan.md` (6단계 전부 [x]).

## 변경 파일
| 파일 | 변경 |
|---|---|
| `domain.py` | `ArchetypeSuggestion`, `FieldVerdict.role_fits/beyond_cot3`, `JudgeResult` 새 필드(qa_matches_cot3, task_qa_direction_match, appliance_controls_visible, archetype_suggestion, phone_numbers, impossible_reasons) + `archetype_correction()`, `RevisedDraft.instruction_changed/dropped_turns`, `Draft.get_field` 에 instruction 읽기 |
| `config.py`, `config.example.yaml`, `config.yaml` | `impossible_rules{max_false_facts 3, max_inconsistent_fields 4}`, `text_rules{remove_phone_numbers}` |
| `rules.py` | `subject_particle`, `build_task`, `correct_instruction`, `find/strip_phone_numbers` |
| `schemas.py` | judge: cot.role_fits, dialogue_turns.beyond_cot3, qa_matches_cot3, task_qa_direction_match, appliance_controls_visible(bool|null), archetype_suggestion. revise: dialogue_assistant.drop |
| `prompts/judge_system.md` | 구조 이해(CoT 단계 정의, QA↔CoT3, Facts 오류 예시), 추가 판정 항목 설명 |
| `prompts/revise_system.md` | 턴 삭제(drop)·병합, 정정된 Instruction 반영, 텍스트 정리(불필요 단어, 전화번호, 어린이 말투) |
| `prompts/__init__.py` | 판정 블록에 새 항목, `build_revise_user(..., corrected)` 정정 Instruction 안내 |
| `judge.py` | 새 필드 정규화, 전화번호 검출, 불가 규칙(D2: 점수·방향·조작부·거짓 팩트·불일치 개수), 방향 불일치는 정정 가능하면 불가 아님, needs_revision 조건(D3) |
| `revise.py` | 아키타입 정정(템플릿 치환, 모델에는 정정본 전달), 턴 drop·재번호(첫 턴 보호), 증가 금지, 전화번호 제거, instruction_changed/dropped_turns |
| `diff.py` | archetype·task 필드 diff |
| `model/base.py`, `model/fake.py` | `revise(..., corrected=None)` |
| `labelon/parser.py`, `labelon/submitter.py` | instruction textarea locator, 값 다를 때 채움, 없는 턴 비우기 |
| `web/static/app.js`, `style.css` | Instruction 정정 diff, 삭제 턴 배지, 판정 패널(불가 사유 목록, 아키타입 제안, QA↔CoT3, 전화번호, 역할/CoT3밖 태그), 승인 다이얼로그 안내 |
| `tests/` | test_rules(+3), test_judge(+7), test_revise(재작성 +4), test_diff, test_services(+1), test_submitter(신규 3), conftest·fake 기본값 |

## 테스트
`pytest -q` → **102 passed** (사이클 2: 84). ruff 통과. `node --check app.js` 통과.

## 규칙 요약 (동작)
- 불가 후보 = 점수 ≤ 40 OR Task·QA 방향 불일치(정정 불가 시) OR 가전조작+조작부 미가시 OR 거짓 팩트 ≥ 3 OR 불일치 필드 ≥ 4. 사유 목록을 화면과 불가 사유 제안에 표시
- 수정 필요 = 불가가 아니고 (거짓 팩트 / 불일치 / 페르소나·태스크 부적합 / 유효한 아키타입 제안 / QA↔CoT3 불일치 / CoT 역할 부적합 / CoT3 밖 턴 / 전화번호)
- 아키타입 정정: 6종 중 하나이고 현재와 다를 때만. task = 템플릿 + 페르소나 + 조사(받침 → 이, 없음 → 가). 되돌리기로 원본 복원
- 턴: drop 은 첫 턴 제외, 남은 턴 1..k 재번호, 제출 시 빈 turn textarea 비움

## 미검증 (Build and Test)
- 실제 모델이 새 스키마 필드(특히 `appliance_controls_visible` null 허용, `drop`)를 정확히 채우는지 → 실제 건 1회
- 실제 화면에서 Instruction textarea fill 이 React 상태에 반영되어 제출 본문에 들어가는지
- 가이드의 이미지 슬라이드(불가 예시)는 미반영
