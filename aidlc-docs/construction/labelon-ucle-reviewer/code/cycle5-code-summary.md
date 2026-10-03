# Cycle 5 Code Summary - 검수자 피드백 반영

생성일: 2026-09-30. 계획: `cycle5-code-generation-plan.md` (5단계 전부 [x]).

## 변경 파일
| 파일 | 변경 |
|---|---|
| `config.py`, `config.example.yaml`, `config.yaml` | 일상지원 템플릿 새 문장, `legacy_archetype_templates`(옛 문장) + 검증, `AppConfig.templates_for()` |
| `rules.py` | `check` 가 현재+레거시 템플릿 중 하나와 일치하면 OK. `DIRECTION_RE`, `find_compound_directions` |
| `schemas.py`, `domain.py` | text_issues.kind 에 `direction` |
| `judge.py` | `_text_fields`, `detect_compound_directions`(결정론), `merge_text_issues`(도구 검출 우선, 모델 보고 중복 제거) |
| `prompts/judge_system.md` | direction 정의, 도움 요청은 보이는 사람에게만(턴 불일치), 가전조작 가구 포함(조작부·환경·정정 제안), 불가 예시 5 삭제·일상지원 실외 허용, 신호 확인 안내는 안전 안내, 템플릿 목록 갱신 |
| `prompts/revise_system.md` | 규칙 16 방향 한 가지, 17 도움 요청 → 스스로 안전하게(예문), 18 가전조작 가구 |
| `web/static/app.js`, `style.css` | "방향" 라벨 |
| `tests/test_rules.py`(+2), `tests/test_judge.py`(+1) | 레거시·새 템플릿 일치·정정 Task 새 문장, 방향 정규식, 결정론 검출·중복 제거 |
| `README.md`, `domain-rules.md`(표·7절), `business-rules.md`(BR-05) | 문서 |

## 테스트
`pytest -q` → **114 passed** (사이클 4 hotfix 후 111). ruff·node check 통과. `config.yaml` 로드 확인.

## 미검증 (실제 건)
- 가전조작 + 가구 사진에서 불가·정정 제안이 나오지 않는지
- 사진에 없는 어른에게 도움 요청하는 턴이 불일치로 잡히고 수정안이 신호 확인 안내로 바뀌는지
