# Cycle 3 Requirements: 검수 가이드 반영

작성일: 2026-09-28. 깊이: Standard. 기반: cycle3-guide-notes.md, 사이클 1·2 요구사항.

## 1. Intent Analysis
| 항목 | 내용 |
|---|---|
| User Request | guide/ 폴더의 검수 가이드(메모·스크린샷·PDF)를 도구의 판정·수정 기준에 반영 |
| Request Type | Enhancement (Brownfield) |
| Scope | Multiple Components: 프롬프트, 스키마, 판정 단계, 수정 단계, 규칙 검사, 상태 스냅샷·화면, 설정 |
| Complexity | Moderate (판정·수정 로직 확장) |

## 2. 기능 요구사항

### FR-C3-1. 아키타입 정정 제안 (가이드 D)
- judge 출력에 `archetype_suggestion {fits: bool, suggested: str|"", reason}` 추가. 모델은 사진·QA·CoT 내용으로 현재 archetype 이 맞는지, 아니면 6종 중 어느 것이 맞는지 판정한다
- suggested 가 6종 중 하나이고 현재와 다르면 needs_revision=True 이며, ReviseStage 는 **모델 호출 없이** 도구가 Instruction 을 정정한다: archetype=suggested, task=템플릿의 `(Persona)`를 초안 persona + 조사로 치환(예: "장난기가 많은 어린아이가"). persona 는 불변
- 정정된 Instruction 은 수정안·diff·제출(textarea instruction 3개 채움)에 반영된다. 사람이 승인 전 되돌릴 수 있다
- 제출 시 Instruction textarea(3개)도 채운다(현재는 건드리지 않음). 값이 초안과 같으면 건너뛴다

### FR-C3-2. 규칙 기반 불가 후보 (가이드 B-2, C, D)
- judge 출력에 `task_qa_direction_match: bool`, `appliance_controls_visible: bool|null`(가전조작일 때만) 추가
- 불가 후보 조건(OR): 점수 ≤ threshold / task_qa_direction_match=False / archetype=가전조작 이고 appliance_controls_visible=False / 수정량 과다(거짓 팩트 ≥ `impossible_rules.max_false_facts`(기본 3) 또는 불일치 필드 ≥ `impossible_rules.max_inconsistent_fields`(기본 4))
- 각 조건은 `impossible_reasons: list[str]` 로 판정 결과에 남기고, 불가 사유 제안 문구에 합친다. 불가 후보이면 2단계 수정은 생략(기존 BR-05 유지)

### FR-C3-3. 멀티턴 정리 (가이드 E)
- judge 출력에 `dialogue_turns[].beyond_cot3: bool` 추가(CoT 3단계 범위를 넘는 추론: 사진에 없는 인물·상황)
- revise 출력에 `dialogue_assistant[].drop: bool` 허용. drop 된 턴은 최종안에서 제거하고, 모델은 필요한 내용을 앞 턴 assistant 에 합친다
- 제약: 턴 수 감소만 허용(증가 금지), 첫 턴은 삭제 불가, user 발화 불변. 삭제된 턴은 diff 에 DELETE 로 표시하고 제출 시 해당 textarea 를 빈 값으로 채운다

### FR-C3-4. 텍스트 정리 (가이드 F)
- revise 프롬프트 규칙 추가: 문맥에 맞지 않는 단어 삭제, 전화번호 삭제, 어린이 페르소나면 딱딱한 문장을 부드럽게(의미 유지)
- 전화번호 정규식 검사(`\d{2,4}-\d{3,4}-\d{4}` 및 `\d{3,4}-\d{4}`)를 초안 전 텍스트 필드에 결정론으로 적용: 발견 시 warnings 에 표시하고 needs_revision=True, 수정안에서 제거 확인(남아 있으면 도구가 제거)

### FR-C3-5. CoT 단계·QA↔CoT3 판정 (가이드 A, E)
- judge 프롬프트에 CoT 단계 정의(1 장소·상황, 2 위험·주의점, 3 행동·답변 정리)와 "QA 는 CoT 3단계와 맞아야 함" 명시
- judge 출력에 `cot[].role_fits: bool`, `qa_matches_cot3: bool` 추가. False 는 불일치 필드로 취급(needs_revision)

### FR-C3-6. 화면
- 판정 패널: 아키타입 제안(현재 → 제안, 사유), 불가 사유 목록, CoT3↔QA 일치, 전화번호 경고
- Instruction 패널: 수정안이 Instruction 을 바꾼 경우 diff 표시(archetype, task)
- 삭제 턴 표시("삭제됨" 배지), 승인 시 확인 다이얼로그에 "Instruction 변경/턴 삭제 포함" 문구

### FR-C3-7. 설정
- `impossible_rules: {max_false_facts: 3, max_inconsistent_fields: 4}`, `text_rules: {remove_phone_numbers: true}`

## 3. 비기능·제약
- 모델 호출 수 불변(judge 1 + revise ≤ 1). 스키마 확장만
- Instruction 정정은 템플릿 치환으로 결정론 생성(모델이 task 문장을 쓰지 않음)
- 기존 테스트 84개 유지. 신규: 아키타입 정정, 불가 규칙, 턴 삭제 제약, 전화번호 검사, 제출 시 instruction·빈 턴 채움
- 가이드 이미지 슬라이드(불가 예시)는 미반영. 자료가 오면 후속 사이클

## 4. 인수 기준
- AC-C3-1 Archetype 음식·QA 쇼핑 내용의 초안에서 판정이 "쇼핑" 제안을 내면 수정안 Instruction 이 쇼핑 템플릿(페르소나 치환)으로 바뀌고 diff 에 보인다
- AC-C3-2 Task·QA 방향 불일치 판정 시 불가 후보와 사유가 표시된다
- AC-C3-3 거짓 팩트 3개 이상이면 불가 후보(수정 생략)
- AC-C3-4 revise 가 턴 5를 drop 하면 최종안은 4턴이고 diff 에 삭제 표시, 제출 시 5번 textarea 는 빈 값
- AC-C3-5 초안에 "234-5678" 이 있으면 경고가 뜨고 최종안에서 제거된다
- AC-C3-6 qa_matches_cot3=False 이면 수정 필요로 표시된다

## 5. 추적
| 답변 | 반영 |
|---|---|
| Q1=A | FR-C3-1, AC-C3-1 |
| Q2=A | FR-C3-2, FR-C3-7, AC-C3-2/3 |
| Q3=A | FR-C3-3, AC-C3-4 |
| Q4=A | FR-C3-4, FR-C3-7, AC-C3-5 |
| Q5=A | FR-C3-5, AC-C3-6 |
| Q6=A | 제약(이미지 슬라이드 미반영) |
