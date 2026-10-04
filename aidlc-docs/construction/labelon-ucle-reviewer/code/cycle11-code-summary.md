# Cycle 11 Code Summary - AI 끄기(수동 검토 모드) · 가이드 체크리스트

생성일: 2026-10-04.

| 파일 | 변경 |
|---|---|
| `services.py` | `AppContext.ai_enabled`, ui-state 에 저장·복원(`DatasetService.load_saved/save/snapshot`), `SettingsService.set_ai`(검토 중 변경 불가), `_analyze(use_ai)` 수동 분기(모델 0회, `rule_warnings`, REVIEW_READY), run() 은 `ctx.ai_enabled`, reanalyze 는 항상 AI, `rule_warnings()` |
| `web/app.py` | `AiSetting`, `PUT /settings/ai` |
| `web/static/index.html`, `app.js`, `style.css` | 헤더 "AI 판정" 토글, 판정 패널 수동 모드 문구, `GUIDE_CHECKLIST` 10항(건 바뀌면 초기화, AI 모드에서는 접힘), 진행 패널 "수동 모드: AI 생략", 다시 판독 툴팁 |
| `README.md` | 수동 모드 설명 |
| `tests/` | test_services(수동 가져오기 모델 0회·재판독 AI·검토 중 변경 불가, ui-state 복원), test_web(PUT /settings/ai, /state ai_enabled) |

테스트 123 passed, ruff·node 통과. v0.11.0.
