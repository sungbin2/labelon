# Component Inventory (Reverse Engineering, 2026-09-28)

| ID | 컴포넌트 | 모듈 | 주요 공개 연산 | 테스트 |
|---|---|---|---|---|
| C-01 | ConfigLoader | config.py | `load(path)`, `AppConfig.ensure_dirs()` | test_config |
| C-02 | BrowserSession | labelon/browser.py | `start(headless)`, `is_logged_in`, `wait_for_login`, `open_job_page`, `fetch_bytes`, `close` | 수동 |
| C-03 | LabelOnPageParser | labelon/parser.py | `parse_html`, `current_job_id`, `csrf_token`, `page_kind`, `field_locators` | test_parser |
| C-04 | ImageService | images.py | `fetch`, `cleanup` | test_images |
| C-05 | RuleChecker | rules.py | `check` | test_rules |
| C-06 | ModelClient | model/* | `judge`, `revise` (+ refusal 폴백) | test_model_cli |
| C-07 | JudgeStage | judge.py | `run`, `compute_score`, `normalize_raw` | test_judge |
| C-08 | ReviseStage | revise.py | `run`, `enforce_constraints` | test_revise |
| C-09 | DiffService | diff.py | `diff` | test_diff |
| C-10 | ReviewStateMachine | state.py | `transition`, `subscribe`, `publish`, `set_flags` | test_state |
| C-11 | Submitter | labelon/submitter.py | `approve`, `impossible`, `release` | 수동 |
| C-12 | HistoryRepository | history.py | save_*/list/detail/summary/unfinished | test_history |
| C-13 | ReviewWebApp | web/app.py | `create_app`, Broadcaster | test_web |
| C-14 | Frontend | web/static/* | store/sse/api/renderers | 수동 |
| S-01~07 | Services | services.py | Session, FetchAndAnalyze, Edit, Submit, Deadline, History, Config | test_services |

품질: pytest 74 passed, ruff clean, 커버리지 약 71%(브라우저·제출기·CLI 실경로 제외).
