# Integration Test Instructions

## Purpose
단일 유닛이지만 외부 시스템 3개(Claude Code CLI, Google Chrome/LabelOn, 로컬 웹 UI)와의 연동을 검증한다. 자동화 가능한 부분은 2026-09-23 에 수행했고, LabelOn 로그인이 필요한 부분은 사용자가 수행한다.

## Test Scenarios

### Scenario 1: ModelClient → Claude Code CLI (자동, 수행 완료)
- **Description**: `ClaudeCliModelClient._call` 이 stdin 프롬프트 + `--system-prompt-file` + `--effort` + `--json-schema` 로 구조화 출력을 받는지, 플래그 프로필 3종이 모두 수용되는지
- **Setup**: Claude Code 로그인 상태, `config.yaml`
- **Test Steps**: `.venv\Scripts\python scripts\bench_cli_context.py --config config.yaml`
- **Expected Results**: 3개 프로필 모두 ok, `answer` 필드 반환
- **Actual (2026-09-23)**:

| profile | context_total | cache_create | out | cost($ list) | api_ms |
|---|---|---|---|---|---|
| basic | 35,659 | 35,657 | 52 | 0.1432 | 2,050 |
| system_prompt | 27,160 | 27,158 | 52 | 0.1092 | 2,806 |
| minimal | 2,193 | 2,191 | 52 | 0.0093 | 1,399 |

  → `cli.flags_profile` 기본값을 `minimal` 로 확정(config.py, config.example.yaml 반영). 호출당 기본 컨텍스트 약 4만 → 2천 토큰
- **Cleanup**: 없음

### Scenario 2: BrowserSession → Chrome → LabelOn (자동, 수행 완료)
- **Description**: 설치된 Chrome 을 전용 프로필로 실행, 미로그인 판별, 작업 화면 접근 시 LOGIN 판별
- **Test Steps**: `BrowserSession.start(headless=True)` → `is_logged_in()` → `open_job_page(688)`
- **Expected Results**: 새 프로필에서 `is_logged_in()==False`, 작업 화면은 `/access` 로 리다이렉트되어 kind `LOGIN`
- **Actual (2026-09-23)**: Chrome 1.4초 기동, `False`, `LOGIN | https://www.labelon.kr/access` — 최초 구현은 헤더의 "로그아웃" 문구로 판별해 오탐이 있었고, 요청 API(`context.request.get('/project/home')`)의 리다이렉트 여부로 판별하도록 수정함
- **Cleanup**: 프로필 `.profile/chrome` 은 유지(로그인 세션 보존용)

### Scenario 3: Web UI → FastAPI → 서비스 (자동, 수행 완료)
- **Description**: 서버 기동, 정적 파일, Origin 검사, SSE, 종료
- **Test Steps**: `python -m labelon_reviewer --config config.yaml --no-chrome --no-browser` 후 curl
- **Expected/Actual**: `/state` 200(READY), `/`·`app.js`·`style.css` 200, evil Origin POST 403, `/events` 첫 `event: state` 수신, `POST /actions/shutdown` → 서버 종료 확인
- **Cleanup**: 없음

### Scenario 4: 서비스 조립 (자동, pytest)
- `tests/test_services.py`, `tests/test_web.py` 가 Fake 브라우저·제출기·모델로 FetchAndAnalyze → Edit → Submit 전 흐름과 실패 경로를 검증. 70 passed

### Scenario 5: 실제 LabelOn 로그인 → 가져오기 → 판정 → 제출 (수동, 사용자 수행 필요)
- **Description**: 실제 작업 화면 파싱, 실제 이미지로 judge/revise, Submitter 의 DOM 조작(textarea fill, 확인 모달, 결과 모달), 작업내역 반영
- **Setup**: `run.bat` 실행, Chrome 창에서 로그인
- **Test Steps**: `docs/manual-checklist.md` 0~5절
- **Expected Results**: 체크리스트 각 항목 통과. 특히 "저장되었습니다" 결과 모달 텍스트, 불가 사유 입력란 selector, 반환 요청 응답
- **Cleanup**: 제출된 건은 되돌릴 수 없음. 검수자에게 보내도 되는 건으로 수행
- **Status**: 미수행 (로그인이 필요하며 사용자만 수행 가능)

## Setup Integration Test Environment
```bat
cd C:\Users\sbahn\label_work
copy config.example.yaml config.yaml
.venv\Scripts\python -m labelon_reviewer --config config.yaml
```

## Run Integration Tests
1. 자동: `pytest -q tests/test_services.py tests/test_web.py`
2. 벤치: `scripts\bench_cli_context.py`(구독 사용량 소량)
3. 수동: `docs/manual-checklist.md`

## Verify Service Interactions
- **Logs Location**: `logs/app.log` (모델 호출 duration·토큰, 상태 전이, 제출 결과)
- 실패 시 `--debug` 로 재실행하면 CLI stderr 와 프롬프트 요약이 기록됨

## Cleanup
```bat
rmdir /s /q data logs
```
(이력 DB 와 이미지 캐시 삭제. 프로필은 유지)
