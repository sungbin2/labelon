# NFR Design Patterns - labelon-ucle-reviewer

깊이: Minimal. 각 패턴은 적용 위치(컴포넌트)와 구현 요지만 기술한다.

## 1. 복원(Resilience)

| 패턴 | 적용 위치 | 구현 요지 |
|---|---|---|
| Retry with backoff | `model/base.py` `BaseModelClient._call` | 최대 2회 재시도, 대기 2초·4초. 재시도 대상: 비0 종료, `is_error`, `structured_output` 없음, 타임아웃, JSON 파싱 실패. 스키마 불일치는 1회 "스키마에 맞게 다시" 재요청 후 실패 처리 |
| Graceful degradation | `services.FetchAndAnalyzeService` | judge 실패 → judge=None, revised=None, final=draft, warnings 추가, REVIEW로 진행. revise 실패 → revised=None, final=draft, warnings 추가 |
| Timeout + kill tree | `model/claude_cli.py` | `asyncio.wait_for` 초과 시 Windows에서 `taskkill /PID <pid> /T /F`로 자식(claude.exe → node)까지 종료 |
| Deadline watchdog | `services.DeadlineService` | 1초 주기. 잔여 ≤ 0이면 EXPIRED 전이, 진행 중 태스크 취소 |
| Idempotent submit guard | `services.SubmitService` | 상태가 REVIEW가 아니면 즉시 거부. SUBMITTING 중 중복 요청은 409 |
| Page identity check | `labelon/submitter.py` | 제출 직전 페이지 스크립트의 job id를 다시 읽어 파싱 시 id와 비교. 다르면 SubmitError |
| Restart recovery | `services.HistoryService` | 시작 시 `find_unfinished()`로 REVIEW/SUBMITTING 상태로 끝난 건을 UI에 표시. 자동 재제출 없음 |
| Browser liveness | `labelon/browser.py` | `context.on("close")`와 5초 주기 `page.is_closed()` 확인. 닫혔으면 상태 기계에 warning, UI에 "브라우저 다시 열기" 버튼 |

## 2. 성능(Performance)

| 패턴 | 적용 위치 | 구현 요지 |
|---|---|---|
| Single background task | `services.FetchAndAnalyzeService` | `asyncio.create_task` 1개를 `current_task`에 보관. 새 fetch 요청은 진행 중이면 409. skip/종료 시 `task.cancel()` |
| Async subprocess | `model/claude_cli.py` | `asyncio.create_subprocess_exec(..., stdout=PIPE, stderr=PIPE)`, stdin 닫기. 이벤트 루프 비차단 |
| Off-loop I/O | `history.py`, `images.py` | sqlite3와 Pillow 처리는 `asyncio.to_thread` |
| Image downscale | `images.py` | 긴 변 1568px, JPEG q85, EXIF 회전 반영(`ImageOps.exif_transpose`) |
| Stable prefix | `prompts/*.md` + `judge.py`/`revise.py` | system prompt 파일은 불변. user 프롬프트는 [고정 지시문] → [초안·QA 텍스트] → [이미지 경로] 순서. 타임스탬프·ID 미포함 |
| Context trimming (벤치로 확정) | `scripts/bench_cli_context.py` | 조합 A: 기본 / B: `--system-prompt-file` / C: B + `--tools Read --disable-slash-commands --strict-mcp-config --mcp-config {}` + CLAUDE.md 없는 cwd. 각 1회 호출해 `usage` 합계와 `duration_api_ms` 기록, 최소 조합을 `config.cli.flags_profile` 기본값으로 |
| Debounced edits | `web/static/app.js` | 400ms debounce 후 PUT /draft. 서버는 마지막 값만 반영 |

## 3. 보안(Security)

| 패턴 | 적용 위치 | 구현 요지 |
|---|---|---|
| Credential boundary | 전체 | 도구 코드는 자격증명을 읽거나 쓰지 않는다. LabelOn 세션은 Chrome 프로필 디렉터리, Claude 인증은 Claude Code 저장소에만 존재. `ANTHROPIC_API_KEY`가 환경에 있으면 시작 시 경고 로그(우선 사용됨) |
| Loopback binding + Origin check | `web/app.py` 미들웨어 | `uvicorn host=127.0.0.1`. POST/PUT 요청의 `Origin`(있으면) 또는 `Host`가 `127.0.0.1:{port}` 또는 `localhost:{port}`가 아니면 403 |
| Least-privilege CLI | `model/claude_cli.py` | `--tools Read --allowedTools Read --permission-mode dontAsk --permission-prompts none --add-dir <resized_dir>`만. cwd는 빈 작업 디렉터리 |
| Path confinement | `web/app.py` `/images/{item_id}` | item_id로 DB에서 파일명을 조회해 `data/cache` 하위 실제 경로만 제공. 경로 문자열 입력 없음 |
| Log masking | `logging` 설정 | INFO: 건 id, 상태, 점수, 토큰. DEBUG: 프롬프트·응답 본문. 쿠키·헤더 값은 어떤 레벨에서도 기록하지 않음 |
| Local-only storage | `data/`, `.profile/`, `logs/` | `.gitignore` 포함. 외부 전송 코드 경로는 Playwright(LabelOn)와 CLI(Claude) 두 곳만 |

## 4. 관측(Observability)

| 패턴 | 구현 요지 |
|---|---|
| 구조화 로그 | `logging` + 포맷 `time level item_id state event msg`. 모델 호출은 `model stage duration_ms in out cache_read cache_create cost_est` |
| SSE heartbeat | 30초마다 `: ping` 코멘트 라인. 클라이언트는 45초 무수신 시 재연결 |
| Usage summary | `history.summary()`가 오늘·누적 토큰과 추정 비용을 집계. 20건마다 INFO 로그로 누적 사용량 출력(NFR C-5) |

## 5. 확장(Extensibility)

| 패턴 | 구현 요지 |
|---|---|
| Strategy: ModelClient | `model_backend` 설정으로 `ClaudeCliModelClient` / `AnthropicSdkModelClient` / `FakeModelClient` 선택. 팩토리 `model/__init__.py::make_client(config)` |
| Config injection | `AppConfig`를 앱 시작 시 1회 로드해 서비스·컴포넌트 생성자에 주입. 전역 접근 없음 |
| Anti-corruption layer | `labelon/parser.py`가 LabelOn 원본 JSON을 도메인 엔티티로 변환. 다른 모듈은 LabelOn 필드명을 모른다 |
