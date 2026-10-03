# Cycle 7 Code Summary - Instruction 편집 · 건수 집계 · 재로그인 복구 · 다시 판독

생성일: 2026-10-02. 계획: `cycle7-code-generation-plan.md` (4단계 전부 [x]).

## 변경 파일
| 파일 | 변경 |
|---|---|
| `domain.py` | `set_field` 에 archetype/persona/task, `editable_fields` 앞에 세 항목, `ReviewEvent.REANALYZE` |
| `state.py` | `(REVIEW, REANALYZE) → JUDGING` |
| `diff.py` | `persona` diff |
| `history.py` | 오늘/누적 = APPROVE 만(불가 제외), 데이터셋 카드 total 도 동일 |
| `services.py` | `AppContext.login_watch_task`; `SessionService.start_login_watch/watch_login`(5초 간격, 로그인 확인 시 플래그 해제·경고·데이터셋 갱신), login_required 를 켜는 두 곳에서 감시 시작; `FetchAndAnalyzeService._analyze` 분리, `start_reanalyze/reanalyze`(같은 item_id, 편집 초기화); `validate_final` Instruction 빈 값 차단; `ConfigService.public` 에 `archetype_templates` |
| `web/app.py` | `on_state` 가 집계를 실어 보냄(제출 즉시 갱신), `POST /actions/reanalyze`(202/409), shutdown 시 감시 태스크 취소 |
| `web/static/index.html` | `btn-reanalyze` "다시 판독 Alt+S", 보조 `btn-skip` "반환"(작은 버튼) |
| `web/static/app.js` | Instruction 편집 UI(select/input/textarea, "템플릿으로 Task 채우기", JS 조사 규칙), `bindEditable` 공통화(지연·IME·blur), 편집 중 Instruction·초안 패널 재렌더 보류, validate Instruction, 가져오기는 로그인 필요여도 활성, 승인 다이얼로그 문구, 집계 문구 "승인 제출 기준", `doReanalyze` |
| `style.css` | Instruction 편집 컨트롤 |
| `tests/` | test_domain(instruction set_field·순서), test_diff(persona), test_history(승인만 집계), test_state(REANALYZE), test_services(로그인 감시, 다시 판독, validate), test_web(/config 템플릿, PUT task·diff) |
| `README.md`, `docs/manual-checklist.md`, `business-rules.md` | 문서 |

## 테스트
`pytest -q` → **117 passed** (사이클 6: 115). ruff·node check 통과.

## 미검증 (사용자 화면)
- 세션 만료 후 Chrome 재로그인 → 5초 내 배너 "로그인이 확인되었습니다", 가져오기 정상
- 다시 판독 → 진행 패널 → 같은 건이 새 판정으로 검토 대기
- Instruction 편집·"템플릿으로 Task 채우기" → 제출 후 LabelOn Instruction 칸 반영
