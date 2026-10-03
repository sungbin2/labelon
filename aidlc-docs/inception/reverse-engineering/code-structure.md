# Code Structure (Reverse Engineering, 2026-09-28)

```
C:\Users\sbahn\label_work\
  pyproject.toml  run.bat  setup.bat  config.example.yaml  config.yaml(로컬)  README.md
  src\labelon_reviewer\
    __init__.py  __main__.py(진입점, 로깅, uvicorn)
    config.py(139)  domain.py(347)  rules.py  diff.py  state.py(134)  history.py(194)  images.py
    schemas.py  judge.py  revise.py  services.py(424)
    labelon\  browser.py(121)  parser.py(211)  submitter.py(181)
    model\    __init__.py(팩토리)  base.py  claude_cli.py(165)  anthropic_sdk.py  fake.py
    prompts\  __init__.py  judge_system.md  revise_system.md
    web\      app.py(290)  static\index.html  app.js(316)  style.css
  tests\ (13 파일, 74 tests)  fixtures\job_page_sample.html + make_job_page_sample.py
  scripts\ bench_cli_context.py  capture_job_page.py
  docs\ manual-checklist.md
  aidlc-docs\ (설계·감사)   data\ logs\ .profile\ .venv\ dist\ (로컬 전용)
```

## 변경 요청(프로젝트 선택)과 관련된 코드 지점
| 지점 | 현재 동작 |
|---|---|
| `config.AppConfig.dataset_id`, `persona` | 단일 값. `services.FetchAndAnalyzeService.run` 이 `cfg.dataset_id` 로 작업 화면을 연다 |
| `rules.check(instruction, config)` | `instruction.persona` 를 `config.persona` 와 비교 |
| `labelon/browser.BrowserSession.open_job_page(dataset_id)` | `/job/ucle/annotator?datasetId=N` 이동 |
| `labelon/parser.page_kind` | JOB/HOME/LOGIN/OTHER 판별. 프로젝트 홈 목록 파싱 기능 없음 |
| `web/app.py GET /config`, `services.ConfigService.public()` | UI 에 dataset_id·persona 노출 |
| `web/static/app.js` headerBar | 데이터셋 표시 없음 |
| `history.items.dataset_id` | 건별 데이터셋 id 저장됨(조회 UI 없음) |
| `prompts.build_judge_user` | `config.persona` 를 "데이터셋 페르소나"로 프롬프트에 포함 |

## LabelOn 프로젝트 홈 구조 (2026-09-28 관찰)
- `/project/home` HTML 에 세 탭(신청가능/진행중/신청중)의 카드가 모두 렌더링되어 있고 CSS 로 숨김
- 진행중 카드 앵커: `<a onclick="jobPage('annotator', 'AH25','688')">` 텍스트 "업사이클링 UpcyclingLE [업사이클링] 거주환경 (어린이3) 크레딧 450 등급 고급자 어노테이터"
- 진행중 6개: 688 어린이3, 687 어린이보호자3, 686 거동불편3, 685 시각장애3, 684 고령3, 682 시각장애2-1 (모두 AH25 = UC-LE)
