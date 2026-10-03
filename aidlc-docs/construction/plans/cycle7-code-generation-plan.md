# Cycle 7 Code Generation Plan

## 설계 결정
- D1 `Draft.set_field` 에 archetype/persona/task(instruction 속성). `editable_fields` 앞에 세 항목. `diff.compute_diff` 에 `persona`
- D2 `validate_final`: instruction 세 값 비면 차단. 프론트 validate 동일. `ConfigService.public()` 에 `archetype_templates`
- D3 `history.summary`: done_kinds = ("APPROVE",). 데이터셋 카드 total 도 APPROVE 만. UI 문구 "제출 N · 불가 N · 건너뜀 N"
- D4 `web/app.py on_state`: `snapshot_payload(item, await history.summary(), datasets.snapshot())`
- D5 `SessionService.watch_login()`: `ctx.login_watch_task` 가 없거나 끝났을 때만 생성. 루프: 5초 대기 → `is_logged_in()` → True 면 flags(login_required=False), add_warning, DatasetService.refresh(), 종료. `set_flags(login_required=True)` 를 호출하는 두 곳(fetch LOGIN, dataset refresh LoginRequired) 뒤에 `SessionService(ctx).start_login_watch()`. shutdown 에서 취소. 프론트 canFetch 에서 `!item.login_required` 제거
- D6 `ReviewEvent.REANALYZE`, TRANSITIONS `(REVIEW, REANALYZE) → JUDGING`. `FetchAndAnalyzeService.reanalyze()`: REVIEW 아니면 IllegalTransition; 현재 source/draft/image_paths/item_id/deadline 보존; `_analyze(item_id, source, draft, images, t0)` 로 판정·수정·최종안 공통부를 분리해 run() 과 공유. 경고 목록은 초기화. `POST /actions/reanalyze`(202, 백그라운드 태스크, fetch_task 와 동일 슬롯)
- D7 프론트: Instruction 패널을 편집 UI 로(select/input/textarea + "템플릿으로 Task 채우기" + 템플릿 일치 태그 유지). 액션바: `btn-skip` → `btn-reanalyze` "다시 판독 Alt+S"(확인 다이얼로그: 사람 편집이 초기화됨), 보조 `btn-release` "반환"(작은 버튼). renderActions 갱신. JS 조사 규칙 `subjectParticle`

## 생성 단계
- [x] Step 1 domain/diff/services(validate, public)/history + tests(test_domain, test_diff, test_history, test_services validate)
- [x] Step 2 state(REANALYZE)/services(reanalyze, watch_login)/web/app.py(on_state summary, /actions/reanalyze, shutdown cancel) + tests(test_state, test_services: reanalyze, login watch; test_web: reanalyze 409, summary in state)
- [x] Step 3 app.js/index.html/style.css, node --check
- [x] Step 4 문서(README 단축키·편집, BR-03/BR-05 메모, cycle7-code-summary.md)
