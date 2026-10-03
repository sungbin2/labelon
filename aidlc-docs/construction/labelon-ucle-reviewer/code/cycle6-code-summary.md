# Cycle 6 Code Summary - QA 질문 편집 · 편집 반영 지연

생성일: 2026-10-01. 계획: `cycle6-code-generation-plan.md` (4단계 전부 [x]).

## 변경 파일
| 파일 | 변경 |
|---|---|
| `domain.py` | 필드 주소 `turn_N_user` (get/set/editable_fields) |
| `diff.py` | 턴마다 `turn_N_user` diff 추가 |
| `services.py` | validate_final: assistant 있고 user 비면 차단. ConfigService.public 에 `edit_delay_ms` |
| `config.py`, `config.yaml`, `config.example.yaml` | `UiConfig.edit_delay_ms`(기본 1500, 300~10000) |
| `web/static/app.js` | 턴 카드에 user textarea(`turnHTML`), fieldValue/fieldLabel user 지원, 저장 지연 = 설정값, IME 조합 중 저장 보류, blur 즉시 저장, **편집 중 초안 패널 재렌더 금지**(pendingItem 보관 → blur 후 반영), validate user 비움 |
| `style.css` | user textarea 스타일 |
| `tests/` | test_domain(user 주소), test_services(user 편집·diff, validate), test_submitter(수정된 질문이 question textarea·payload 에 반영), test_web(PUT turn_1_user, /config edit_delay_ms) |
| `README.md`, `business-rules.md`(BR-21) | 문서 |

## 테스트
`pytest -q` → **114 passed**(기존 테스트에 검증 추가), 커버리지 79%. ruff·node check 통과. `/config` 에 `edit_delay_ms: 1500`.

## 미검증 (사용자 화면)
- 한글 빠른 입력 시 조합이 끊기지 않는지, 입력 멈춤 1.5초 뒤 "변경됨"·diff 표시
- 질문 편집 후 제출 시 LabelOn 질문 칸에 반영
