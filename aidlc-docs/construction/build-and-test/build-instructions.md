# Build Instructions

## Prerequisites
- **Build Tool**: Python 3.13 (64-bit) + pip, setuptools(pyproject 빌드 백엔드). 별도 빌드 도구 없음
- **Dependencies**: fastapi, uvicorn[standard], pydantic>=2, pillow, playwright, httpx, pyyaml. 개발: pytest, pytest-asyncio, pytest-cov, ruff
- **External Tools**: Google Chrome(설치됨), Claude Code CLI 2.1.280 이상(`claude` 가 PATH 에 있고 로그인되어 있어야 함)
- **Environment Variables**: 필요 없음. `ANTHROPIC_API_KEY` 가 있으면 Claude Code 가 로그인 대신 그 키를 사용하므로 의도가 아니면 제거
- **System Requirements**: Windows 11, 디스크 약 500MB(venv + Chrome 프로필), 네트워크(labelon.kr, images.labelon.kr, Anthropic)

## Build Steps

### 1. Install Dependencies
```bat
cd C:\Users\sbahn\label_work
py -3.13 -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -e ".[dev]"
```
주의: 32-bit Python(기본 `python`)으로 만든 venv 에서는 네이티브 휠 빌드가 실패한다. 반드시 `py -3.13`(64-bit) 사용.

### 2. Configure Environment
```bat
copy config.example.yaml config.yaml
mkdir C:\labelon-reviewer-work
```
`config.yaml` 확인: `dataset_id: 688`, `persona`, `cli.flags_profile: minimal`(벤치 결과), `cli.cwd`(CLAUDE.md 가 없는 디렉터리).

### 3. Build All Units
소스 배포형 Python 패키지라 별도 컴파일 없음. editable 설치가 빌드에 해당한다.
```bat
.venv\Scripts\python -c "import labelon_reviewer, importlib.metadata as m; print(m.version('labelon-reviewer'))"
.venv\Scripts\labelon-reviewer --version
.venv\Scripts\python -m ruff check src tests scripts
```

### 4. Verify Build Success
- **Expected Output**: 버전 `0.1.0` 두 번 출력, ruff `All checks passed!`
- **Build Artifacts**: `.venv\Lib\site-packages\labelon_reviewer-0.1.0.dist-info`(editable 링크), 콘솔 스크립트 `.venv\Scripts\labelon-reviewer.exe`
- **Common Warnings**: pip 의 setuptools 편집 설치 경고, starlette testclient 의 httpx deprecation 경고(테스트 시)는 무시 가능

### 5. 실행 확인 (2026-09-23 수행)
```bat
.venv\Scripts\python -m labelon_reviewer --config config.yaml --no-chrome --no-browser
```
- `GET /state` 200, `/`·`/static/app.js`·`/static/style.css` 200, 잘못된 Origin 의 POST 403, `/events` SSE 첫 이벤트 수신, `POST /actions/shutdown` 후 서버 종료 — 모두 확인됨

## Troubleshooting

### Build Fails with Dependency Errors
- **Cause**: 32-bit Python 으로 venv 생성 → cryptography 등 네이티브 휠 없음 → Rust 빌드 시도 후 실패
- **Solution**: `.venv` 삭제 후 `py -3.13 -m venv .venv` 로 재생성(`py -0p` 로 64-bit 3.13 존재 확인)

### `claude` 실행 파일을 찾을 수 없음
- **Cause**: Claude Code 미설치 또는 PATH 미등록
- **Solution**: `claude --version` 확인. 다른 경로면 `config.yaml` 의 `cli.path` 에 절대 경로 지정

### Chrome 이 뜨지 않음
- **Cause**: Chrome 미설치 또는 채널 이름 불일치
- **Solution**: `config.yaml` `chrome.channel` 을 `chromium` 으로 바꾸고 `.venv\Scripts\python -m playwright install chromium`
