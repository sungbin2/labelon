# Cycle 3 Code Generation Plan - 검수 가이드 반영

단일 진실. 순서대로 실행, 완료 즉시 [x]. Brownfield: 제자리 수정.
요구사항: `cycle3-requirements.md` (FR-C3-1~7, AC-C3-1~6). 가이드 정리: `cycle3-guide-notes.md`.

## 설계 결정 (Functional Design 대체)

### D1. 판정 출력 확장 (schemas.JUDGE_SCHEMA, domain.JudgeResult)
- `cot[]` 에 `role_fits`(1단계 장소·상황 / 2단계 위험·주의 / 3단계 행동·답변 역할에 맞는가)
- `dialogue_turns[]` 에 `beyond_cot3`(사진에 없는 인물·상황 등 CoT 3단계 범위를 넘는 추론)
- 최상위 `qa_matches_cot3: bool`, `task_qa_direction_match: bool`, `appliance_controls_visible: bool|null`(가전조작일 때만 의미), `archetype_suggestion {fits: bool, suggested: str, reason: str}`(suggested 는 6종 중 하나 또는 "")
- 도구 계산: `phone_numbers: list[str]`(정규식 `\b\d{2,4}-\d{3,4}-\d{4}\b|\b\d{3,4}-\d{4}\b`, 초안 전 텍스트 필드), `impossible_reasons: list[str]`

### D2. 불가 후보 (JudgeStage)
impossible_candidate = 점수 ≤ threshold OR task_qa_direction_match=False OR (archetype=가전조작 AND appliance_controls_visible=False) OR 거짓 팩트 ≥ impossible_rules.max_false_facts OR 불일치 필드 ≥ impossible_rules.max_inconsistent_fields. 각 조건은 한국어 사유 문자열로 impossible_reasons 에 누적하고 impossible_reason_suggestion 이 비어 있으면 사유를 "; " 로 합쳐 채운다.

### D3. 수정 필요 (JudgeStage)
needs_revision = not impossible AND (기존 조건 OR archetype_suggestion 적용 가능 OR qa_matches_cot3=False OR cot.role_fits=False 있음 OR beyond_cot3 턴 있음 OR phone_numbers 있음). "적용 가능" = fits=False AND suggested ∈ 템플릿 6종 AND suggested != 현재 archetype.

### D4. 아키타입 정정 (rules + ReviseStage)
- `rules.subject_particle(word)`: 마지막 글자 받침 있으면 "이", 없으면 "가"(한글 아닌 경우 "가")
- `rules.build_task(template, persona)`: `(Persona)` → persona + 조사, 나머지 템플릿 본문 그대로
- `rules.correct_instruction(instruction, suggested, config) -> Instruction`: archetype=suggested, persona 불변, task=build_task
- ReviseStage: 정정이 적용되면 모델에 보내는 초안의 Instruction 을 정정본으로 교체하고 프롬프트에 "Instruction 이 아래처럼 정정되었으니 CoT·QA 를 이 task 목적에 맞게 조정" 명시. 최종안 instruction = 정정본. `RevisedDraft.instruction_changed=True`
- 초안 원본 Instruction 은 ReviewItem.draft 에 그대로 남아 diff 로 비교

### D5. 턴 삭제 (schemas.REVISE_SCHEMA, ReviseStage)
- `dialogue_assistant[]` 에 선택 필드 `drop: bool`
- raw_to_draft: drop=True 인 턴 제외. 첫 활성 턴은 drop 무시. 남은 턴을 1부터 순서대로 재번호. user 발화는 원래 턴의 것을 유지
- enforce_constraints: 활성 턴 수 ≤ 원본, ≥ 1. 원본에 없던 턴 금지. `RevisedDraft.dropped_turns=[원래 번호]`
- 제출: turn n 이 최종안에 없으면 question·answer textarea 를 빈 값으로 채움(값이 있을 때만)

### D6. 텍스트 정리
- revise_system.md 규칙: 문맥에 맞지 않는 단어 삭제, 전화번호 삭제, 어린이 페르소나(persona 에 "어린이" 포함)면 딱딱한 문장을 부드럽게(의미·사실 유지)
- enforce_constraints 마지막에 `text_rules.remove_phone_numbers` 이면 모든 텍스트 필드에서 전화번호 제거

### D7. Diff·화면
- diff 에 `archetype`, `task` 필드 추가(instruction). 삭제 턴은 other 가 빈 문자열 → 기존 diff_text 가 DELETE 로 표시
- Instruction 패널: final.instruction 이 draft 와 다르면 "수정안" 배지 + 이전→이후 표시, 되돌리기로 복원
- 판정 패널: 아키타입 제안, 불가 사유 목록, QA↔CoT3, CoT 역할, 전화번호 경고
- 대화: draft 에 있고 final 에 없는 턴 → "삭제됨" 배지(원문 취소선)
- 승인 다이얼로그: instruction 변경·턴 삭제가 있으면 문구 추가

### D8. 제출 (Submitter.approve)
- `textarea.ucle_instruction_textarea` nth 0/1/2 = archetype/persona/task 를 final 값으로 채움(값이 다를 때만)
- 턴 1~6: final 에 있으면 채움, 없으면 기존 값이 있을 때 빈 값으로

## 생성 단계

### Step 1. 도메인·설정·규칙
- [x] `domain.py`: `ArchetypeSuggestion`, `FieldVerdict.role_fits/beyond_cot3`, `JudgeResult` 필드 추가, `RevisedDraft.instruction_changed/dropped_turns`, `Draft.get_field/set_field` 에 archetype/task 읽기(편집 불가)
- [x] `config.py`, `config.example.yaml`, `config.yaml`: `impossible_rules`, `text_rules`
- [x] `rules.py`: `subject_particle`, `build_task`, `correct_instruction`, `find_phone_numbers`, `strip_phone_numbers`
- [x] `tests/test_rules.py`: 조사 선택(어린아이→가, 성인→이), build_task, correct_instruction, 전화번호 검출·제거

### Step 2. 스키마·프롬프트
- [x] `schemas.py`: D1, D5 반영
- [x] `prompts/judge_system.md`: CoT 단계 정의, QA↔CoT3, Task·QA 방향, 아키타입 적합성(6종 의미), 가전조작 조작부, 새 출력 필드 설명, 가이드 오류 예시 3종(컵/화분, 흰색/파란색, 하나/여러 개)
- [x] `prompts/revise_system.md`: 턴 삭제 규칙(drop), 텍스트 정리 규칙, 정정된 Instruction 반영 규칙
- [x] `prompts/__init__.py`: build_revise_user 에 정정 Instruction 안내 블록, 판정 블록에 새 항목

### Step 3. 판정·수정 로직
- [x] `judge.py`: normalize 새 필드, 전화번호 검사, D2 불가 규칙, D3 needs_revision
- [x] `revise.py`: D4 정정, D5 턴 삭제·재번호, D6 전화번호 제거, instruction_changed/dropped_turns
- [x] `diff.py`: archetype/task 필드
- [x] `tests/test_judge.py`: 불가 규칙 3종, 수정 필요 조건(제안/qa_cot3/전화번호/beyond), 누락 보정
- [x] `tests/test_revise.py`: 정정 적용·미적용, 턴 drop(첫 턴 보호, 재번호, user 유지, 증가 금지), 전화번호 제거
- [x] `tests/test_diff.py`: instruction diff, 삭제 턴 DELETE

### Step 4. 제출기
- [x] `labelon/submitter.py`: instruction textarea 채움(값 다를 때), 없는 턴 비우기
- [x] `tests/test_submitter.py`(신규): Fake page/locator 로 approve 의 fill 순서·빈 턴 처리 검증

### Step 5. 서비스·화면
- [x] `services.py`: 흐름 변경 없음 확인(정정은 ReviseStage 내부). validate_final 은 턴 감소 허용(이미 활성 턴 기준)
- [x] `web/static/app.js`, `index.html`, `style.css`: D7
- [x] `tests/test_services.py`: 제안 적용 흐름(final.instruction 변경, diff 에 task 변경, dropped_turns 반영)

### Step 6. 문서
- [x] `README.md` 판정 항목 설명, `cycle3-code-summary.md`, `business-rules.md` BR-05/BR-20/BR-22 개정 메모, `domain-rules.md` 가이드 링크

## 인수 기준 추적
| AC | 단계 |
|---|---|
| AC-C3-1 아키타입 정정 | 1, 2, 3, 5 |
| AC-C3-2 방향 불일치 불가 | 2, 3 |
| AC-C3-3 수정량 과다 불가 | 1, 3 |
| AC-C3-4 턴 삭제 | 2, 3, 4, 5 |
| AC-C3-5 전화번호 | 1, 3 |
| AC-C3-6 QA↔CoT3 | 2, 3 |
