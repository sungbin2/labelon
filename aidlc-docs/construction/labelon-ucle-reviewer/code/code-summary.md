# Code Summary - labelon-ucle-reviewer

생성일: 2026-09-23. 워크스페이스: `C:\Users\sbahn\label_work`. 생성 계획: `aidlc-docs/construction/plans/labelon-ucle-reviewer-code-generation-plan.md` (19단계 전부 [x]).

## 1. 생성 파일과 컴포넌트 매핑

| 경로 | 컴포넌트/서비스 | 내용 |
|---|---|---|
| `pyproject.toml`, `.gitignore`, `run.bat`, `config.example.yaml`, `README.md` | 골격, US-9 | 패키지·의존성·ruff·pytest 설정, 실행 스크립트, 설정 예시, 사용 안내 |
| `src/labelon_reviewer/config.py` | C-01 | `AppConfig`(pydantic), `load()`, `ConfigError(field, reason)` |
| `src/labelon_reviewer/domain.py` | 엔티티 | SourceItem, Draft, JudgeResult, RevisedDraft, FinalDraft, SubmissionRecord, ReviewItem, 상태·이벤트 enum, 예외 8종, 필드 주소 체계(`scene`, `fact_n`, `cotN`, `turn_n_assistant`) |
| `src/labelon_reviewer/rules.py` | C-05 | BR-01/02 템플릿·페르소나 검사(공백 무시, 조사 허용) |
| `src/labelon_reviewer/diff.py` | C-09 | 문장 분할 + SequenceMatcher, facts 인덱스 비교 |
| `src/labelon_reviewer/state.py` | C-10 | 전이표 기반 상태 기계, async 구독자 통지 |
| `src/labelon_reviewer/history.py` | C-12 | SQLite 6테이블 DDL, 저장·조회·요약·미완료 |
| `src/labelon_reviewer/images.py` | C-04 | 다운로드(주입 fetcher), 캐시, EXIF 회전 축소, 정리 |
| `src/labelon_reviewer/schemas.py` | C-07/08 | judge·revise 출력 JSON 스키마 |
| `src/labelon_reviewer/prompts/` | C-07/08 | `judge_system.md`, `revise_system.md`(고정부), user 프롬프트 조립 |
| `src/labelon_reviewer/model/base.py` | C-06 | `ModelClient` Protocol, `BaseModelClient`(재시도 2회, 백오프, 타임아웃 가드) |
| `src/labelon_reviewer/model/claude_cli.py` | C-06 기본 | `claude -p` 서브프로세스, flags_profile 3종, stdin 프롬프트, JSON 파싱, 트리 종료 |
| `src/labelon_reviewer/model/anthropic_sdk.py` | C-06 대안 | Anthropic SDK(선택 의존성), base64 이미지 + structured outputs. **미검증** |
| `src/labelon_reviewer/model/fake.py` | 테스트 | 미리 정한 결과 반환 |
| `src/labelon_reviewer/judge.py` | C-07 | 규칙 검사 → 모델 → 누락 보정 → 점수(BR-10~13) → 불가 후보 → needs_revision |
| `src/labelon_reviewer/revise.py` | C-08 | 모델 수정 → `enforce_constraints`(BR-20~28) |
| `src/labelon_reviewer/labelon/parser.py` | C-03 | 스크립트 배열 추출(괄호 매칭), SourceItem/Draft 변환, jobDate 시간대 보정, csrf, page_kind, locator 맵 |
| `src/labelon_reviewer/labelon/browser.py` | C-02 | Playwright persistent context(channel=chrome), 로그인 감지·대기, 작업 화면 열기, 이미지 다운로드 |
| `src/labelon_reviewer/labelon/submitter.py` | C-11 | approve/impossible(UI fill·클릭·모달), release(페이지 컨텍스트 jQuery) |
| `src/labelon_reviewer/services.py` | S-01~S-07 | Session, FetchAndAnalyze(단일 태스크·폴백), Edit, Submit(전제·만료·중복), Deadline, History, Config |
| `src/labelon_reviewer/web/app.py` | C-13 | FastAPI 팩토리, lifespan, Origin 검사, SSE 브로드캐스터, 엔드포인트 16개 |
| `src/labelon_reviewer/web/static/index.html, app.js, style.css` | C-14 | 3열 화면, SSE 구독·재연결, diff 렌더, 편집 debounce, 단축키, 카운트다운, 이력 탭, 확인 다이얼로그, `data-testid` |
| `src/labelon_reviewer/__main__.py` | 진입점 | argparse, 회전 로그, API 키 경고, uvicorn |
| `scripts/bench_cli_context.py` | NFR C-3 | 플래그 프로필 3종 컨텍스트 실측 |
| `scripts/capture_job_page.py` | 운영 | 실제 작업 화면 HTML 캡처(+선택 반환) |
| `docs/manual-checklist.md` | Build 준비 | 실브라우저·실모델 수동 검증 8절 |
| `tests/` (12 파일) | 검증 | 70개 테스트 |

## 2. 스토리 커버리지

| 스토리 | 구현 | 자동 테스트 | 수동 검증(체크리스트) |
|---|---|---|---|
| US-1 로그인 세션 | browser.py, services.SessionService, app.js 배너 | test_services(login_expired) | 0절 |
| US-2 가져오기 | services.FetchAndAnalyzeService, parser, images | test_services(full_flow, no_job, duplicate), test_web(fetch) | 2절 |
| US-3 판정 확인 | judge.py, rules.py, app.js judgePanel | test_judge, test_rules | 2절 |
| US-4 편집 | revise.py, diff.py, EditService, draftPanel | test_revise, test_diff, test_web(put draft/revert) | 3절 |
| US-5 승인·제출 | submitter.approve, SubmitService | test_services(submit, failure), test_web(409/410) | 3절 |
| US-6 불가 제출 | submitter.impossible | test_services(impossible), test_web(422) | 4절 |
| US-7 반환·제한시간 | submitter.release, DeadlineService, 카운트다운 | test_services(skip, expired, deadline_tick) | 5, 6절 |
| US-8 이력·비용 | history.py, HistoryService, historyTab | test_history, test_web | 8절 |
| US-9 설정 | config.py | test_config | 1절 |

## 3. 테스트

`.venv\Scripts\python -m pytest -q` → **70 passed** (2026-09-23 생성 시점). `ruff check src tests scripts` 통과.

| 파일 | 대상 |
|---|---|
| test_config, test_domain, test_rules, test_diff, test_state, test_history, test_images | 순수 로직 |
| test_model_cli | CLI 인자 조립, 출력 파싱, 재시도 횟수, Fake |
| test_judge, test_revise | 점수 산식(BR-10~13), 수정 실행 조건(BR-04), 제약 강제(BR-20~28) |
| test_parser | 픽스처 HTML(실제 초안 구조) 파싱, 시간대 보정, page_kind |
| test_services | Fake 브라우저·제출기·모델로 전 흐름, 폴백, 전제 위반, 만료, skip |
| test_web | 상태·설정, Origin 403, 409/410/422, 경로 노출 차단 |

## 4. Build and Test 단계 결과 반영 (2026-09-23)

- 확인 완료: 5번(CLI stdin 프롬프트 + system-prompt-file + effort + json-schema, `minimal` 프로필 플래그 수용 → 기본값 확정), 7번(shutdown 엔드포인트 종료 확인), 8번(컨텍스트 2,193 토큰), Chrome 기동·로그인 판별(요청 API 방식으로 수정)
- 남은 미검증(사용자 E2E): 아래 1~4, 6

## 4-1. 원래 목록

1. Playwright `launch_persistent_context(channel="chrome")` 실제 실행과 로그인 감지 문구("로그아웃" 존재, password 입력 없음)
2. Submitter 의 실제 DOM 동작: textarea `fill()` 후 React 상태 반영, 확인 모달 버튼 이름 "확인", 결과 모달 텍스트 "저장되었습니다", 불가 사유 입력란 selector(`placeholder*='불가 사유'`) — 관찰되지 않은 부분은 첫 실제 제출에서 확인 후 `parser.FieldLocatorMap` 조정
3. `release()` 의 `/job/ucle/annotator/resetData` 응답 형식
4. jobDate 시간대 보정이 실제 카운트다운과 일치하는지 (`server_tz_offset_hours`)
5. `claude -p` 를 stdin 프롬프트 + `--system-prompt-file` + `--effort` 로 호출했을 때의 동작(검증된 호출은 `-p "text"` + `--allowedTools Read --add-dir --json-schema` 조합). `minimal` 프로필의 `--tools`, `--permission-prompts none`, `--strict-mcp-config` 플래그 수용 여부는 벤치로 확인
6. `AnthropicSdkModelClient` 전체(선택 의존성, 미설치)
7. `POST /actions/shutdown` 의 SIGINT 기반 종료가 Windows uvicorn 에서 정상 동작하는지
8. 컨텍스트 절감 실측치(NFR C-3)와 `cli.flags_profile` 기본값 확정
