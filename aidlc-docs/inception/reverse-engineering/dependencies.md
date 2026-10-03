# Dependencies (Reverse Engineering, 2026-09-28)

## 패키지 의존성 (pyproject.toml)
- 런타임: fastapi, uvicorn[standard], pydantic>=2, pillow, playwright, httpx, pyyaml
- 개발: pytest, pytest-asyncio, ruff (+ pytest-cov 설치됨)
- 선택: anthropic (model_backend=anthropic_sdk 전환 시)

## 모듈 간 의존 방향 (순환 없음)
```
__main__ → config, history, images, judge, revise, model, labelon.browser, labelon.submitter, services, web.app
web.app → services, domain
services → config, diff, domain, history, images, judge, labelon.parser, revise, state
judge → rules, config, domain, model.base
revise → config, domain, model.base
model.base → config, domain, prompts, schemas
model.claude_cli → config, domain, model.base
labelon.browser → config, domain, labelon.parser
labelon.submitter → domain, labelon.parser
labelon.parser → domain
prompts → config, domain
rules → config, domain
diff, state, history, images → domain
```

## 외부 의존
| 대상 | 격리 지점 | 변경 시 수정 범위 |
|---|---|---|
| LabelOn 페이지 구조·모달 | labelon/parser.py, labelon/submitter.py | 두 모듈 |
| Claude Code CLI 플래그·출력 형식 | model/claude_cli.py | 한 모듈 (+ config flags_profile) |
| Chrome/Playwright | labelon/browser.py | 한 모듈 |
