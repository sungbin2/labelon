# Cycle 4 Code Generation Plan - 검수 가이드 이미지 슬라이드 반영

단일 진실. 순서대로 실행, 완료 즉시 [x]. Brownfield: 제자리 수정.
요구사항: `cycle4-requirements.md` (FR-C4-1~5, AC-C4-1~5). 가이드 정리: `cycle4-guide-notes.md` (N1~N8).

## 설계 결정 (Functional Design 대체)

### D1. 판정 출력 확장 (schemas.JUDGE_SCHEMA, domain.JudgeResult)
- 최상위 `archetype_fits_environment: bool` + `environment_note: str`
- 최상위 `impossible_flags: {core_error_propagated: bool, persona_infeasible_guidance: bool, unsafe_guidance: bool, note: str}` (한 객체로 묶어 스키마 required 를 단순화)
- 최상위 `text_issues: list[{field: str, kind: "typo"|"speculation"|"number", wrong: str, correct: str}]` (field 예: scene, fact_2, cot1, turn_3_assistant)
- domain: `ImpossibleFlags`, `TextIssue` 모델. JudgeResult 에 `archetype_fits_environment=True`, `environment_note=""`, `impossible_flags`, `text_issues` 추가
- 누락 보정: 필드 없으면 "문제 없음"(fits_environment=True, flags 모두 False, text_issues=[])

### D2. 불가 규칙 확장 (JudgeStage.run)
사이클 3 사유 5종 뒤에 추가:
- archetype_fits_environment=False → "아키타입이 이미지 환경과 맞지 않음: {environment_note}". **이 경우 correction=None 으로 강제**(정정 미적용, AC-C4-1). 모델 제안이 있었다면 경고 "환경 충돌로 아키타입 정정을 적용하지 않음"
- core_error_propagated → "핵심 물체·팩트 오인식이 CoT·QA 전반에 전파됨: {note}"
- persona_infeasible_guidance → "페르소나가 수행할 수 없는 확인·행동을 요구함: {note}"
- unsafe_guidance → "위험 행위를 권고함: {note}"
- note 는 공통 한 개(impossible_flags.note)이며 비어 있으면 콜론 이하 생략

### D3. needs_revision (JudgeStage.run)
기존 조건 OR `text_issues` 비어 있지 않음

### D4. 프롬프트
- judge_system.md: (a) "QA 검수 포인트" 절(단순 설명형 X, 상황 맥락·Facts·CoT 기반, 페르소나 맞춤형), (b) "텍스트 오류" 절(오탈자·맞춤법 모든 영역, 주관적 추측 금지, 이미지 숫자는 숫자 그대로 예 열세 번 → 13번) + text_issues 출력 설명, (c) "불가 예시" 절(가이드 불가 예시 1~7 요약: 오인식 전파, 시각적 확인 요구, 팩트 오해로 멀티턴 꼬임, 무단횡단 권고, 실외에 일상지원, 실외에 실내탐색·음식, 가전 조작부 미가시) + archetype_fits_environment·impossible_flags 출력 설명. 환경 충돌과 라벨 불일치(archetype_suggestion) 구분 명시
- revise_system.md: 규칙 15 "텍스트 오류 반영": 판정의 text_issues 를 그대로 반영(오탈자 → 바른 표기, 숫자 → 숫자 표기, 추측 문장 → 삭제 또는 사진에서 확인되는 사실). 그 외 오탈자를 발견하면 함께 고치되 의미 변경 금지
- prompts/__init__.py 판정 블록(`_judge_block` 또는 build_revise_user 내부)에 text_issues 목록 추가

### D5. 화면 (app.js, style.css)
- 판정 패널: 불가 사유 목록은 기존 `impossible_reasons` 렌더링 재사용(사유 추가로 자동 반영). "환경 부적합" 배지(archetype_fits_environment=false), 텍스트 오류 목록(필드 · 종류 라벨 · 잘못 → 바름)
- 종류 라벨: typo=오탈자, speculation=추측, number=숫자 표기

### D6. 문서
- README 판정 항목, business-rules BR-05 개정 메모(불가 사유 9종), domain-rules 6절(사이클 4 가이드), cycle4-code-summary.md

## 생성 단계

### Step 1. 도메인·스키마
- [x] `domain.py`: `ImpossibleFlags`, `TextIssue`, JudgeResult 필드 4개
- [x] `schemas.py`: D1 반영(required 에 archetype_fits_environment, environment_note, impossible_flags, text_issues 추가; kind enum)
- [x] `tests/conftest.py`: judge_raw_all_true 에 새 필드 기본값

### Step 2. 프롬프트
- [x] `prompts/judge_system.md`: D4(a)(b)(c)
- [x] `prompts/revise_system.md`: 규칙 15
- [x] `prompts/__init__.py`: 판정 블록에 text_issues, 환경 충돌·불가 플래그 표시

### Step 3. 판정 로직
- [x] `judge.py`: normalize_raw 새 필드(누락 보정), D2 불가 규칙·정정 미적용, D3
- [x] `tests/test_judge.py`: 환경 충돌 → 불가·정정 미적용(AC-C4-1), 플래그 3종 각각 → 불가·사유 문구(AC-C4-2), text_issues 만 → needs_revision(AC-C4-3), 모두 없음 → 사이클 3 과 동일(AC-C4-4), 누락 보정
- [x] `tests/test_revise.py` 또는 `test_prompts`: build_revise_user 에 text_issues 포함 확인

### Step 4. 화면
- [x] `web/static/app.js`, `style.css`: D5
- [x] `node --check`

### Step 5. 문서
- [x] `README.md`, `business-rules.md`(BR-05), `domain-rules.md`(6절), `cycle4-code-summary.md`

## 인수 기준 추적
| AC | 단계 |
|---|---|
| AC-C4-1 환경 충돌 불가·정정 미적용 | 1, 2, 3 |
| AC-C4-2 불가 사유 3종 | 1, 2, 3 |
| AC-C4-3 text_issues → 수정 필요·프롬프트 포함 | 1, 2, 3 |
| AC-C4-4 문제 없으면 기존 동작 | 3 |
| AC-C4-5 화면 표시 | 4 |
