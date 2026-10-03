# Code Generation Plan - labelon-ucle-reviewer

이 문서는 Code Generation의 단일 진실(source of truth)이다. Part 2는 이 계획의 체크박스 순서대로만 실행한다.

## 유닛 컨텍스트

- **워크스페이스 루트**: `C:\Users\sbahn\label_work` (Greenfield, 단일 유닛 → `src/`, `tests/`, 설정은 루트)
- **구현 스토리**: US-1 ~ US-9 (Must 7, Should 1, Could 1) 모두 이번 생성 범위
- **의존 유닛**: 없음. 외부 시스템: LabelOn(브라우저), Claude Code CLI(서브프로세스)
- **소유 데이터**: SQLite `data/history.db` 6테이블(domain-entities.md DDL)
- **인터페이스**: HTTP API 15개(component-methods.md C-13), SSE `/events`
- **기술 스택**: Python 3.13 64-bit, FastAPI/uvicorn, pydantic v2, Playwright(channel=chrome), Pillow, sqlite3, PyYAML, pytest/pytest-asyncio (tech-stack-decisions.md)
- **설계 입력**: application-design/*.md, functional-design/*.md, nfr-requirements/*.md, nfr-design/*.md

## 코드 위치

```
C:\Users\sbahn\label_work\
  pyproject.toml  run.bat  config.example.yaml  README.md  .gitignore
  src\labelon_reviewer\...   (아래 단계별 파일)
  tests\...
  scripts\bench_cli_context.py
  docs\manual-checklist.md
```
문서 요약은 `aidlc-docs/construction/labelon-ucle-reviewer/code/`에만 쓴다.

---

## 생성 단계

### Step 1. 프로젝트 골격 (US-9)
- [x] `pyproject.toml` (패키지 `labelon_reviewer`, src 레이아웃, 의존성 고정, pytest 설정, ruff)
- [x] `.gitignore` (`.venv/ data/ logs/ .profile/ __pycache__/ .pytest_cache/ config.yaml`)
- [x] `config.example.yaml` (모든 설정 키와 기본값, 아키타입 템플릿 6종, 페르소나 "장난기가 많은 어린아이", dataset_id 688)
- [x] `src/labelon_reviewer/__init__.py`, `tests/__init__.py`, `tests/conftest.py`(공용 픽스처: 샘플 SourceItem/Draft JSON, 메모리 DB, FakeModelClient)

### Step 2. 설정 로더 C-01 (US-9)
- [x] `src/labelon_reviewer/config.py`: `AppConfig`(pydantic) — dataset_id, persona, archetype_templates, threshold, models{judge,revise}, effort{judge,revise}, model_backend, image_max_side, cache_retention_days, ui_port, chrome{channel, profile_dir}, cli{path, cwd, timeouts{judge,revise}, flags_profile}, paths{data, logs}; `load(path)`; `ConfigError(field, reason)`
- [x] `tests/test_config.py`: 정상 로드, 누락 필드 오류에 항목명 포함, 임계값 범위 검증

### Step 3. 도메인 엔티티 (전 스토리)
- [x] `src/labelon_reviewer/domain.py`: SourceItem, RelatedQA, Instruction, DialogueTurn, Dialogue, Draft, InstructionCheck, FactVerdict, FieldVerdict, PersonaTaskFit, JudgeResult, RevisedDraft, FinalDraft, SubmissionRecord, ModelUsage, ReviewItem, ReviewState(enum), FieldDiff/DiffSegment, 도메인 예외 6종
- [x] `tests/test_domain.py`: Draft JSON 왕복, 턴 수·facts 5개 제약

### Step 4. 규칙 검사기 C-05 (US-3)
- [x] `src/labelon_reviewer/rules.py`: `check(instruction, config) -> InstructionCheck` (BR-01, BR-02: 공백 제거 + 조사 허용 정규식)
- [x] `tests/test_rules.py`: 688 실제 초안 일치, 조사 "이/가" 변형 허용, 다른 아키타입 문구 불일치, 미지 아키타입, 페르소나 불일치

### Step 5. Diff 서비스 C-09 (US-4)
- [x] `src/labelon_reviewer/diff.py`: 문장 분할, SequenceMatcher 기반 세그먼트, facts 인덱스 비교, `diff(base, other) -> list[FieldDiff]`
- [x] `tests/test_diff.py`: 동일/치환/삽입/삭제, 빈 턴 처리

### Step 6. 상태 기계 C-10 (US-2, US-5, US-7)
- [x] `src/labelon_reviewer/state.py`: `ReviewStateMachine` — 전이표(business-logic-model.md 5절), `transition`, `subscribe`(async 콜백), `remaining_seconds`, `IllegalTransition`
- [x] `tests/test_state.py`: 정상 경로, 모델 생략 경로, 불법 전이, DONE→FETCHING, 만료 전이, 구독자 통지

### Step 7. 이력 저장소 C-12 (US-8)
- [x] `src/labelon_reviewer/history.py`: `HistoryRepository` — DDL 생성, save_*/mark_state/list_recent/get_detail/summary/find_unfinished, 메모리 DB 지원, WAL
- [x] `tests/test_history.py`: 저장·조회 왕복, summary 집계, 미완료 조회

### Step 8. 이미지 서비스 C-04 (US-2, US-8)
- [x] `src/labelon_reviewer/images.py`: `ImageService` — 다운로드(Playwright request 주입 가능), 캐시·축소(EXIF 회전), cleanup
- [x] `tests/test_images.py`: 축소 크기 계산, cleanup 보관 일수

### Step 9. 모델 클라이언트 C-06 (US-3, US-4)
- [x] `src/labelon_reviewer/model/__init__.py`: `make_client(config)` 팩토리
- [x] `src/labelon_reviewer/model/base.py`: `ModelClient` Protocol, `BaseModelClient`(재시도·타임아웃·usage 수집·스키마 검증), `JudgeRaw/ReviseRaw` 타입
- [x] `src/labelon_reviewer/model/claude_cli.py`: `ClaudeCliModelClient` — 인자 조립(tech-stack-decisions 3.2), 환경변수 정리, `create_subprocess_exec`, 타임아웃 시 `taskkill /T`, stdout JSON 파싱(`structured_output`, `usage`, `total_cost_usd`, `is_error`), flags_profile(basic / system_prompt / minimal)
- [x] `src/labelon_reviewer/model/anthropic_sdk.py`: `AnthropicSdkModelClient` — `anthropic` 패키지 지연 import, base64 이미지 + `output_config.format` 구조화 출력, 미설치 시 명확한 오류
- [x] `src/labelon_reviewer/model/fake.py`: `FakeModelClient` — 미리 정한 JudgeRaw/ReviseRaw 반환, 호출 기록
- [x] `tests/test_model_cli.py`: 인자 조립 스냅샷, JSON 파싱, 실패 재시도 횟수(서브프로세스 목)

### Step 10. 프롬프트 (US-3, US-4)
- [x] `src/labelon_reviewer/prompts/judge_system.md`: 역할·판정 원칙·방향 기준·R1~R3·아키타입 템플릿·출력 스키마 설명·한국어 지시
- [x] `src/labelon_reviewer/prompts/revise_system.md`: 역할·BR-20~BR-28 전문·출력 스키마 설명
- [x] `src/labelon_reviewer/prompts/__init__.py`: 파일 로더, user 프롬프트 조립 함수(고정 지시문 → 초안·QA → 이미지 경로)

### Step 11. 판정·수정 단계 C-07, C-08 (US-3, US-4)
- [x] `src/labelon_reviewer/judge.py`: `JudgeStage.run` — RuleChecker → model.judge → 스키마 보정 → Score(BR-10~13) → impossible_candidate → needs_revision(BR-04); judge JSON 스키마 상수
- [x] `src/labelon_reviewer/revise.py`: `ReviseStage.run`, `enforce_constraints`(BR-20~28); revise JSON 스키마 상수
- [x] `tests/test_judge.py`: 점수 산식 예시(79점 케이스), 불가 후보, needs_revision 규칙, 누락 필드 보정
- [x] `tests/test_revise.py`: 제약 강제(instruction·context·user·턴 수·facts 5), skipped 경로

### Step 12. LabelOn 연동 C-02, C-03, C-11 (US-1, US-2, US-5, US-6, US-7)
- [x] `src/labelon_reviewer/labelon/__init__.py`
- [x] `src/labelon_reviewer/labelon/parser.py`: 스크립트 텍스트에서 `vqaCotList`/`vqaCotResultList` 배열 추출(정규식 + json.loads, 유니코드 이스케이프 처리), SourceItem/Draft 변환, `csrf_token`, `field_locators`(textarea 클래스·순서 기반), `page_kind(url, html)`
- [x] `src/labelon_reviewer/labelon/browser.py`: `BrowserSession` — persistent context(channel=chrome), is_logged_in(로그아웃 링크), wait_for_login, open_job_page, current_page_kind, liveness
- [x] `src/labelon_reviewer/labelon/submitter.py`: `Submitter.approve/impossible/release` (business-logic-model.md 6절 절차, 페이지 id 재확인, fill 검증, 모달 대기)
- [x] `tests/fixtures/job_page_sample.html`: 2026-09-23 관찰 구조를 재현한 최소 HTML(인라인 스크립트에 실제 초안 JSON 포함, textarea 구조)
- [x] `tests/test_parser.py`: 픽스처 파싱, 필드 매핑, 구조 오류 감지, page_kind 판별

### Step 13. 서비스 계층 S-01~S-07 (전 스토리)
- [x] `src/labelon_reviewer/services.py`: SessionService, FetchAndAnalyzeService(단일 태스크·취소·모델 실패 폴백), EditService, SubmitService(전제 검사·만료·중복 차단), DeadlineService, HistoryService(이벤트 구독·미완료), ConfigService
- [x] `tests/test_services.py`: FakeBrowser/FakeParser/FakeModelClient로 가져오기 전 흐름, 모델 실패 폴백, 승인 전제 위반 거부, 만료 시 제출 거부, skip 흐름

### Step 14. 웹 API C-13 (US-2 ~ US-8)
- [x] `src/labelon_reviewer/web/__init__.py`
- [x] `src/labelon_reviewer/web/app.py`: FastAPI 앱 팩토리, lifespan(시작·종료 시퀀스), Origin 검사 미들웨어, 엔드포인트 15개 + `/actions/shutdown`, SSE 브로드캐스터(heartbeat 30초), 정적 파일
- [x] `tests/test_web.py`: `/state`, Origin 불일치 403, fetch 중복 409, approve 상태 위반 409, 이미지 경로 노출 차단

### Step 15. 프론트엔드 C-14 (US-1 ~ US-8)
- [x] `src/labelon_reviewer/web/static/index.html`: 3열 레이아웃 골격, `data-testid` 부여(`action-fetch-button`, `action-approve-button`, `action-impossible-button`, `action-skip-button`, `action-revert-button`, `draft-field-{name}`, `history-tab` 등)
- [x] `src/labelon_reviewer/web/static/app.js`: store, sse(재연결), api, 컴포넌트 12개(frontend-components.md), 단축키, debounce 편집, diff 렌더, 카운트다운, 이력 탭, 확인 다이얼로그
- [x] `src/labelon_reviewer/web/static/style.css`: 3열 그리드, diff 색상, 상태 배지, 반응형 최소

### Step 16. 진입점·실행 스크립트 (US-1, US-9)
- [x] `src/labelon_reviewer/__main__.py`: argparse(`--config`, `--debug`, `--no-browser`), 로깅(RotatingFileHandler), 디렉터리 생성, API 키 경고, uvicorn 실행, 기본 브라우저 오픈
- [x] `run.bat`: venv 활성화 → `python -m labelon_reviewer --config config.yaml`

### Step 17. 벤치·운영 스크립트 (NFR C-3)
- [x] `scripts/bench_cli_context.py`: 플래그 조합 3가지로 짧은 호출 후 usage·duration 표 출력(실행은 Build 단계)
- [x] `scripts/capture_job_page.py`: 로그인된 프로필로 작업 화면 HTML을 `tests/fixtures/`에 저장(파서 회귀 픽스처 갱신용, 실행은 사용자 확인 후)

### Step 18. 문서 (US-9, Build 준비)
- [x] `README.md`: 설치(64-bit Python 3.13, venv), 설정, 실행, 단축키, 문제 해결(로그인, API 키 경고, 포트)
- [x] `docs/manual-checklist.md`: 실브라우저·실모델 수동 검증 체크리스트(로그인 → 1건 가져오기 → 승인 제출 → 작업내역 확인, 불가 제출 1건, 건너뛰기 1건, 만료 시나리오)

### Step 19. 코드 요약 문서 (aidlc-docs)
- [x] `aidlc-docs/construction/labelon-ucle-reviewer/code/code-summary.md`: 생성 파일 목록, 모듈 ↔ 컴포넌트 매핑, 스토리 커버리지, 테스트 목록, 미검증 항목(Build에서 확인)

---

## 스토리 추적

| 스토리 | 구현 단계 |
|---|---|
| US-1 로그인 세션 준비 | 12(browser), 13(SessionService), 15, 16 |
| US-2 다음 건 가져오기 | 6, 8, 12, 13, 14, 15 |
| US-3 판정 결과 확인 | 4, 9, 10, 11, 15 |
| US-4 수정안 편집 | 5, 11, 13(EditService), 14, 15 |
| US-5 승인·제출 | 12(submitter), 13(SubmitService), 14, 15 |
| US-6 불가 제출 | 12, 13, 14, 15 |
| US-7 반환·제한시간 | 6, 12(release), 13(DeadlineService), 15 |
| US-8 이력·비용 | 7, 8, 13(HistoryService), 14, 15 |
| US-9 설정 변경 | 1, 2, 16, 18 |

## 범위 메모
- 총 19단계, 파일 약 40개. 테스트는 Build and Test 단계에서 실행한다(생성 중에도 문법 확인 수준의 실행은 허용).
- 실브라우저·실모델 연동은 Build 단계의 수동 체크리스트로 검증한다.
