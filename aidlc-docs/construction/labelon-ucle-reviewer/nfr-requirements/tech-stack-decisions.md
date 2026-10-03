# Tech Stack Decisions - labelon-ucle-reviewer

작성일: 2026-09-23

## 1. 런타임·패키징

| 항목 | 결정 | 근거·비고 |
|---|---|---|
| Python | 3.13.14 64-bit (`py -3.13`) | 기본 `python`은 32-bit 3.12.9로 네이티브 휠(cryptography 등) 빌드 실패. 64-bit로 venv 재생성함 |
| 가상환경 | `C:\Users\sbahn\label_work\.venv` (생성 완료) | `run.bat`이 활성화 |
| 패키징 | `pyproject.toml` + pip | 패키지명 `labelon_reviewer`, 진입점 `python -m labelon_reviewer` |
| 설치된 의존성 | fastapi 0.141.1, uvicorn[standard] 0.53.0, pydantic 2.13.5, pillow 12.3.0, playwright 1.63.0, httpx 0.28.1, PyYAML 6.0.3, pytest 9.1.1, pytest-asyncio 1.4.0 | 2026-09-23 설치 |
| 추가 예정 | ruff (개발용) | |

## 2. 브라우저 자동화

| 항목 | 결정 |
|---|---|
| 라이브러리 | Playwright(Python, async API) |
| 브라우저 | 설치된 Google Chrome, `channel="chrome"`, `headless=False` |
| 프로필 | `launch_persistent_context(user_data_dir=<project>/.profile/chrome)`. 로그인 세션 보존. `.gitignore` 포함 |
| 페이지 컨텍스트 JS | `page.evaluate`로 `vqaCotList`, `vqaCotResultList` 전역 배열 접근(스크립트 전역 `const`는 evaluate에서 접근 불가할 수 있어 스크립트 텍스트 정규식 파싱을 기본으로 하고 evaluate를 보조로 사용) |
| 이미지 다운로드 | `context.request.get(image_url)` (쿠키 공유) |
| 제출 조작 | `locator.fill()` → `input_value()` 검증 → `click()` → 모달 텍스트 대기 `expect(...).to_contain_text` |

## 3. 모델 백엔드

### 3.1 결정: 1순위 `claude_cli` (Claude Code headless 서브프로세스)

- 이 PC의 Claude Code 2.1.280과 기존 로그인을 그대로 사용. **검증 완료(2026-09-23)**:
  - 텍스트 호출: `claude -p "Reply with exactly: OK" --model claude-sonnet-5 --output-format json --max-turns 1` → `is_error:false`, 응답 OK, API 1.6초
  - 이미지 + 구조화 출력: 테스트 이미지(빨간 사각형 왼쪽, 파란 원 오른쪽)를 `--allowedTools Read --add-dir <dir> --json-schema {...}`로 호출 → `structured_output = {"shapes":[{"shape":"rectangle","color":"red","position":"left"},{"shape":"circle","color":"blue","position":"right"}]}`, 4턴, API 7.5초
- Python Agent SDK 패키지는 사용하지 않는다. 이유: (1) 동일한 바이너리를 감싼 것이라 기능 차이가 없음, (2) 문서상 SDK 경로는 API 키 인증을 안내하고 있어 구독 로그인 동작이 보증되지 않음, (3) CLI 서브프로세스는 이 PC에서 실제 검증됨.

### 3.2 호출 규격 (ClaudeCliModelClient)

```
claude -p <user_prompt_text>
  --model <claude-sonnet-5 | claude-fable-5-1>
  --effort <medium | high>
  --output-format json
  --json-schema <schema_json>
  --system-prompt-file <prompts/judge_system.md | prompts/revise_system.md>
  --tools Read                       # Read 도구만 노출
  --allowedTools Read
  --permission-mode dontAsk --permission-prompts none
  --add-dir <image_cache_dir>        # Read가 이미지를 읽을 수 있게
  --max-turns 4
  --no-session-persistence
  --disable-slash-commands
  --strict-mcp-config --mcp-config '{"mcpServers":{}}'
```
- 실행 cwd: `config.cli.cwd` (기본 `C:\labelon-reviewer-work`처럼 CLAUDE.md가 조상 경로에 없는 디렉터리). 사용자 홈 아래는 `C:\Users\sbahn\CLAUDE.md`가 로드되므로 피한다
- 환경변수: `CLAUDECODE`, `CLAUDE_CODE_ENTRYPOINT` 제거(중첩 세션 가드 회피). `ANTHROPIC_API_KEY`가 설정되어 있으면 그것이 우선 사용되므로 주의 문구 표시
- `--bare`는 사용하지 않는다(문서: bare 모드는 OAuth 자격증명을 읽지 않음)
- 이미지 전달: 프롬프트에 축소 이미지 절대 경로를 명시하고 Read 도구로 읽게 한다(검증된 방식). `--input-format stream-json`으로 이미지 블록을 직접 넣는 방식은 미검증이라 채택하지 않음
- 응답 파싱: stdout JSON의 `is_error`, `structured_output`, `usage{input_tokens, output_tokens, cache_read_input_tokens, cache_creation_input_tokens}`, `total_cost_usd`, `duration_api_ms`, `num_turns`, `permission_denials`
- 재시도: 비0 종료·`is_error`·`structured_output` 없음·타임아웃 → 최대 2회

### 3.3 대안: `anthropic_sdk`

- Anthropic Python SDK `anthropic` 패키지(설계 시점 미설치, 전환 시 설치). 인증은 `ANTHROPIC_API_KEY` 또는 `ant auth login` OAuth 프로파일(Console 계정)
- 이미지 base64 블록 + structured outputs(`output_config.format`)로 동일 스키마 사용. 프롬프트 캐싱 `cache_control` 적용
- 전환: `config.model_backend: anthropic_sdk`

### 3.4 정책 확인 사항 (사용자 판단 필요)

Agent SDK 개요 문서의 원문: "Unless previously approved, Anthropic does not allow third party developers to offer claude.ai login or rate limits for their products, including agents built on the Claude Agent SDK." 이 문구는 제3자 개발자가 자기 제품 사용자에게 claude.ai 로그인을 제공하는 경우를 대상으로 한다. 본 도구는 계정 소유자가 자기 PC에서 자기 작업에 쓰는 개인 도구이며 Claude Code의 공식 headless(`-p`) 기능을 그대로 호출한다. 그럼에도 구독 약관 해석은 사용자의 책임이며, 문제가 있다고 판단되면 3.3의 API 키 경로로 전환한다.

## 4. 웹 서버·UI

| 항목 | 결정 |
|---|---|
| 프레임워크 | FastAPI + uvicorn, `host=127.0.0.1`, `port=8765` |
| SSE | `StreamingResponse(media_type="text/event-stream")`, asyncio.Queue 기반 브로드캐스트, 30초 heartbeat |
| 정적 파일 | `static/index.html`, `static/app.js`(ES 모듈), `static/style.css`. 빌드 없음 |
| 스키마 | pydantic v2 모델을 도메인 엔티티·API 응답·CLI JSON 스키마 생성(`model_json_schema()`)에 공용 |

## 5. 저장소·이미지·설정

| 항목 | 결정 |
|---|---|
| DB | sqlite3(표준 라이브러리), 파일 `data/history.db`, 동기 호출을 `asyncio.to_thread`로 감쌈, WAL 모드 |
| 이미지 | Pillow. 캐시 `data/cache/<file_name>`, 축소본 `data/resized/<file_name>` |
| 설정 | `config.yaml` + pydantic `AppConfig`. 예시 파일 `config.example.yaml` 제공 |
| 프롬프트 | `prompts/judge_system.md`, `prompts/revise_system.md`(고정부), 가변부는 코드에서 조립 |

## 6. 테스트·품질·로깅

| 항목 | 결정 |
|---|---|
| 테스트 | pytest + pytest-asyncio. 픽스처: 2026-09-23 관찰 구조를 재현한 작업 화면 HTML 조각과 실제 초안 JSON. 모델 목은 `FakeModelClient` |
| 실브라우저 검증 | `docs/manual-checklist.md`: 로그인 → 1건 가져오기 → 승인 제출 → 작업내역 확인, 불가 제출 1건 |
| 린트 | ruff |
| 로깅 | logging + RotatingFileHandler(`logs/app.log`, 5MB x 5) + StreamHandler. INFO 기본, `--debug`로 DEBUG |

## 7. 디렉터리 구조 (Code Generation 입력)

```
C:\Users\sbahn\label_work\
  pyproject.toml
  run.bat
  config.example.yaml
  README.md
  src\labelon_reviewer\
    __main__.py          # uvicorn 기동 + Chrome 실행 + 브라우저 오픈
    config.py            # AppConfig (C-01)
    domain.py            # 엔티티 (pydantic)
    labelon\browser.py   # C-02
    labelon\parser.py    # C-03
    labelon\submitter.py # C-11
    images.py            # C-04
    rules.py             # C-05
    model\base.py        # C-06 Protocol + 재시도
    model\claude_cli.py  # ClaudeCliModelClient
    model\anthropic_sdk.py
    model\fake.py        # 테스트용
    judge.py             # C-07
    revise.py            # C-08
    diff.py              # C-09
    state.py             # C-10
    history.py           # C-12
    services.py          # S-01~S-07
    web\app.py           # C-13 FastAPI
    web\static\index.html, app.js, style.css   # C-14
    prompts\judge_system.md, revise_system.md
  tests\
  docs\manual-checklist.md
  data\ (gitignore)  logs\ (gitignore)  .profile\ (gitignore)  .venv\ (gitignore)
```
