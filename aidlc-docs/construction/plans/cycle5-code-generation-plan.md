# Cycle 5 Code Generation Plan - 검수자 피드백 반영

순서대로 실행, 완료 즉시 [x]. 요구사항: cycle5-requirements.md.

## 설계 결정
- D1 `AppConfig.legacy_archetype_templates: dict[str, list[str]]` (기본 {일상지원: [옛 문장]}). `rules.check` 는 primary 또는 legacy 중 하나와 일치하면 task_matches_template=True. `build_task`/`correct_instruction` 은 primary 사용
- D2 `rules.DIRECTION_RE = (앞|뒤)\s?(왼|오른)쪽|(왼|오른)쪽\s?(앞|뒤)쪽?`, `find_compound_directions(text) -> list[str]`. judge 가 초안 텍스트 필드마다 검출해 `TextIssue(field, kind="direction", wrong=표현, correct="")` 를 text_issues 앞에 추가(모델이 같은 field+wrong 을 보고했으면 중복 제거). kind enum 에 "direction" 추가
- D3 프롬프트: judge — 방향 결합 표현 정의(text_issues direction), 도움 요청은 사진에 그 사람이 보일 때만(없으면 해당 턴 consistent=false), 가전조작 가구 포함(appliance_controls_visible·환경 충돌·정정 제안 모두), 불가 예시 5 삭제·환경 충돌 예시에서 일상지원 제거, 템플릿 목록 갱신, unsafe_guidance 와 신호 확인 안내 구분. revise — 규칙 16 방향 한 가지로, 규칙 17 도움 요청 → 스스로 안전하게 건너는 안내(예문), 가전조작 가구 언급
- D4 화면: TEXT_KIND.direction = "방향", style 태그 색은 typo 와 동일
- D5 문서: domain-rules 템플릿 표 갱신(+옛 문장 주석), README, business-rules BR-05 메모(일상지원 실외 예외), cycle5-code-summary.md

## 생성 단계
- [x] Step 1 `config.py`(DEFAULT 갱신, legacy 필드·검증), `config.example.yaml`, `config.yaml`, `rules.py`(레거시 일치, DIRECTION_RE), `tests/test_rules.py`(옛·새 문장 일치, 정정 Task 는 새 문장, 방향 검출), `tests/test_config.py`(예시 설정 로드)
- [x] Step 2 `schemas.py`(direction), `domain.py`(주석), `judge.py`(결정론 방향 검출·중복 제거), `tests/test_judge.py`
- [x] Step 3 `prompts/judge_system.md`, `prompts/revise_system.md`
- [x] Step 4 `web/static/app.js`(라벨), `node --check`
- [x] Step 5 문서
