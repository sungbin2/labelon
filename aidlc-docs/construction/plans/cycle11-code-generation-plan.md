# Cycle 11 Code Generation Plan

## 설계 결정
- D1 `AppContext.ai_enabled: bool = True`. `DatasetService` 의 ui-state 파일에 `ai_enabled` 도 저장·복원(`load_saved` 가 ai_enabled 를 ctx 에 반영, `save` 가 함께 기록). `snapshot()` 에 `ai_enabled` 포함 → `/state`·SSE 에 실림
- D2 `SettingsService.set_ai(enabled)`: SELECTABLE 상태에서만, ctx.ai_enabled 갱신 + save + publish. `PUT /settings/ai`
- D3 `FetchAndAnalyzeService._analyze(..., use_ai: bool)`: run() 은 `ctx.ai_enabled`, reanalyze() 는 항상 True. use_ai=False 면 이미지 처리 후 `rule_warnings(draft)`(rules.check 불일치 상세, 전화번호, 두 방향 표현)를 warnings 에 넣고 `REVIEW_READY` 전이, final=초안, diff 계산, 저장
- D4 프론트: 헤더 토글(checkbox, `ai-toggle`), 판정 패널 — judge 없고 수동 모드면 "수동 검토 모드" + 체크리스트(`GUIDE_CHECKLIST` 상수, 건 바뀌면 초기화) + 규칙 경고는 warnings 패널. judge 있으면 하단에 `<details>` 체크리스트. 다시 판독 툴팁 "AI 로 판정·수정 실행"
- D5 문서: README(토글·수동 모드), operations

## 생성 단계
- [x] Step 1 services(ctx.ai_enabled, ui-state, SettingsService, _analyze use_ai, rule_warnings) + web/app.py(PUT /settings/ai) + tests(services 수동 가져오기·재판독 AI, ui-state 복원; web PUT/state)
- [x] Step 2 index.html/app.js/style.css 토글·체크리스트, node --check
- [x] Step 3 문서, 버전 0.11.0, 커밋
