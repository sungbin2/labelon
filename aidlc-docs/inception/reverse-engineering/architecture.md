# Architecture (Reverse Engineering, 2026-09-28)

단일 Python 프로세스(uvicorn + asyncio). 상세: `aidlc-docs/inception/application-design/application-design.md`, `aidlc-docs/construction/labelon-ucle-reviewer/nfr-design/logical-components.md`.

```
+---------------------------------------------------------------------------+
| labelon-reviewer (python -m labelon_reviewer, 127.0.0.1:8765)             |
|  web/app.py FastAPI + SSE  <->  services.py (Session/Fetch/Edit/Submit/   |
|  web/static (index.html, app.js)     Deadline/History/Config)             |
|        |                                  |                               |
|  state.py ReviewStateMachine        judge.py / revise.py / rules.py       |
|  history.py SQLite                  model/claude_cli.py (claude -p)       |
|  images.py Pillow                   labelon/{browser,parser,submitter}.py |
+---------------------------------------------------------------------------+
        |  Playwright (channel=chrome, .profile/chrome)        | subprocess
        v                                                      v
   LabelOn (labelon.kr)                                   claude.exe (Read 도구만)
```

## 계층
| 계층 | 모듈 | 비고 |
|---|---|---|
| 프레젠테이션 | web/app.py, web/static/* | Origin 검사, SSE 브로드캐스트, 엔드포인트 17개 |
| 서비스 | services.py | AppContext 가 모든 컴포넌트를 보유. 상태 전이는 ReviewStateMachine 만 수행 |
| 도메인 | domain.py, rules.py, judge.py, revise.py, diff.py, schemas.py, prompts/ | 순수 로직. Facts 는 가변 길이(2026-09-23 개정) |
| 연동 | labelon/*.py, model/*.py, images.py, history.py | 외부 시스템 격리. LabelOn 구조 지식은 parser.py·submitter.py 에만 |
| 설정·진입 | config.py, __main__.py, run.bat, setup.bat | config.yaml 1개 |

## 설계 원칙 (코드에서 확인)
- 제출·반환은 사용자 HTTP 요청(POST /actions/*)으로만 시작 (BR-31)
- 동시에 1건만 보유 (ReviewStateMachine 단일 ReviewItem)
- 자격증명 비저장 (Chrome 프로필·Claude Code 저장소에만 존재)
