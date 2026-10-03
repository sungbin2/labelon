# labelon-reviewer

LabelOn UC-LE 데이터셋의 어노테이터 초안을 비전 모델로 검토·수정하고, **사람이 확인한 뒤** 제출하는 로컬 도구입니다.

- 서버 초안을 사진과 대조해 팩트별 참/거짓, 정합성 점수, 불가 후보를 판정합니다 (Claude Sonnet 5). 검수 가이드 규칙(Task·QA 방향, 가전조작 조작부, 수정량 과다, CoT 단계 역할, QA↔CoT3 일치, 전화번호, 아키타입 정정 제안)을 함께 적용합니다. 가이드 불가 예시(아키타입-환경 충돌, 오인식 전파, 페르소나가 할 수 없는 확인 요구, 위험 행위 권고)와 텍스트 오류(오탈자·추측·숫자 표기·두 방향 결합)도 판정합니다. 가전조작은 가구를 포함하고, 도움 요청은 사진에 그 사람이 보일 때만 허용합니다
- 수정이 필요한 건만 최소 편집 수정안을 만듭니다 (Claude Fable 5.1). 아키타입이 틀리면 템플릿으로 Task 를 정정하고, CoT 3단계를 넘는 대화 턴은 삭제·병합하며, 전화번호는 제거합니다. 모두 diff 로 표시되고 승인 전 되돌릴 수 있습니다
- 로컬 웹 화면에서 diff 를 보고 편집한 뒤 승인·불가·다시 판독·반환을 결정합니다. Instruction(아키타입·페르소나·태스크)과 대화의 질문·답변까지 모두 편집할 수 있고, 변경된 항목마다 "초안으로" 버튼으로 그 항목만 되돌릴 수 있습니다. 항목 삭제(빈 값)는 승인이 차단됩니다. **제출은 사용자의 클릭으로만** 일어납니다
- 모델 호출은 이 PC 의 Claude Code 로그인을 그대로 사용합니다. API 키·비밀번호를 저장하지 않습니다

## 요구 사항

- Windows 11, **64-bit Python 3.13** (`py -3.13`), Google Chrome
- Claude Code CLI 설치·로그인 (`claude --version` 이 동작하고 `claude -p "hi"` 가 응답하면 됩니다)
- LabelOn 계정 (로그인은 도구가 띄우는 Chrome 창에서 직접 합니다)

## 설치 (다른 PC 포함)

git 저장소를 받은 뒤 `setup.bat` 을 실행하면 venv 생성, 패키지 설치, `config.yaml` 생성, 테스트까지 한 번에 진행됩니다.

```bat
git clone https://github.com/sungbin2/labelon.git labelon-reviewer
cd labelon-reviewer
setup.bat
run.bat
```

`run.bat` 은 시작할 때 `git pull` 로 최신 버전을 받고(변경이 있으면 패키지 재설치) 실행합니다. 네트워크가 없거나 충돌이 있으면 경고만 내고 현재 버전으로 실행합니다. 업데이트를 건너뛰려면 `run.bat --no-update`. 실행 로직은 `scripts\start.bat` 에 있고 `run.bat` 은 업데이트만 담당하는 작은 파일이라, 업데이트 중에 바뀌어도 안전합니다. (`run.bat` 자체가 바뀐 버전을 받은 직후에는 한 번 더 실행하세요) `config.yaml` 은 PC 마다 로컬 파일이라 git 에 올라가지 않습니다. (zip 배포는 보조 수단으로 `dist/` 에 계속 생성)

사전 준비: 64-bit Python 3.13(python.org, `py -3.13` 으로 실행 가능해야 함), Google Chrome, Claude Code CLI 설치 후 터미널에서 `claude` 를 한 번 실행해 로그인.

수동 설치:

```bat
cd C:\Users\sbahn\label_work
py -3.13 -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -e ".[dev]"
copy config.example.yaml config.yaml
```

`config.yaml` 에서 확인할 항목:

| 키 | 설명 |
|---|---|
| `dataset_id` | 기본·폴백 데이터셋(목록을 못 읽을 때만 사용). 실제 대상은 화면 드롭다운에서 선택 |
| `persona` | 선택. 초안에 persona 가 비어 있을 때만 프롬프트에 사용. 데이터셋마다 페르소나가 달라 비교에는 쓰지 않음 |
| `threshold` | 정합성 점수가 이 값 이하이면 불가 후보 (기본 40) |
| `impossible_rules` | 거짓 팩트·불일치 필드가 이 개수 이상이면 불가 후보(수정량 과다). 기본 3 / 4 |
| `chrome.window` | Chrome 창 크기. `maximized`(기본) 또는 `1600x1000` 처럼 가로x세로. 시작 후 창 상태를 직접 적용 |
| `chrome.image_tab` | 건을 가져오면 Chrome 에 이미지 전용 탭을 열어 원본 사진을 창에 맞춰 표시(기본 true). 클릭으로 원본 크기 전환 |
| `revision_rules.revise_impossible` | 불가 후보 건에도 수정안을 만들어 diff 로 표시(기본 true). 고쳐서 승인하거나 불가로 제출 선택 가능 |
| `revision_rules.allow_turn_drop` | 모델이 대화 턴을 삭제·병합할 수 있는지. 기본 false(모든 턴 유지, 내용만 수정) |
| `ui.edit_delay_ms` | 화면에서 직접 수정할 때 입력이 멈춘 뒤 저장까지 지연(ms). 기본 1500. 한글 조합 중에는 저장하지 않고, 칸을 벗어나면 즉시 저장 |
| `text_rules.remove_phone_numbers` | 전화번호 검출·제거 (기본 true) |
| `cli.cwd` | Claude CLI 실행 디렉터리. **CLAUDE.md 가 조상 경로에 없는 곳**으로 두세요 (기본 `C:/labelon-reviewer-work`) |
| `cli.flags_profile` | `basic` / `system_prompt` / `minimal`. `scripts/bench_cli_context.py` 로 실측 후 조정 |
| `model_backend` | `claude_cli`(기본) / `anthropic_sdk`(API 키 또는 ant OAuth 프로파일) / `fake`(UI 테스트) |

## 실행

```bat
run.bat
```

1. 검토 화면이 기본 브라우저(http://127.0.0.1:8765)에 열리고, LabelOn 용 Chrome 창이 따로 뜹니다
2. Chrome 창에 로그인 페이지가 보이면 **직접 로그인**하세요. 완료되면 검토 화면이 "준비됨"으로 바뀝니다
3. 헤더의 **데이터셋 드롭다운**에서 작업할 프로젝트를 고릅니다. 목록은 LabelOn "진행중인 작업" 중 UC-LE 데이터셋을 자동으로 읽어 오며(새로고침 버튼으로 갱신), 마지막 선택은 `data/ui-state.json` 에 저장되어 다음 실행 때 복원됩니다. 검토 중인 건이 있을 때는 바꿀 수 없습니다
4. **다음 건 가져오기(Alt+N)** → 판정·수정이 끝나면 "검토 대기"
5. diff 와 팩트 판정을 보고 필요하면 텍스트를 편집(대화의 질문·답변 모두 편집 가능) → **승인·제출(Alt+A)**, 이미지와 전혀 다르면 **불가 제출(Alt+X)**, 모델 판정을 다시 받으려면 **다시 판독(Alt+S)**, 제출하지 않고 돌려보내려면 작은 **반환** 버튼
6. 이력 탭에서 처리 내역(데이터셋별 건수 포함)과 토큰 사용량을 확인합니다

단축키: Alt+N 가져오기, Alt+A 승인, Alt+X 불가, Alt+S 다시 판독, Alt+R 초안으로 되돌리기. 헤더의 오늘/누적 건수는 승인 제출만 센다(불가·반환 제외). 세션이 만료되면 Chrome 에서 다시 로그인만 하면 약 5초 안에 자동 복구된다.

## 테스트

```bat
.venv\Scripts\python -m pytest -q
.venv\Scripts\python -m ruff check src tests
```

실브라우저·실모델 검증은 `docs/manual-checklist.md` 를 따릅니다.

## 문제 해결

| 증상 | 조치 |
|---|---|
| 검토 화면에 "로그인을 완료해 주세요" | Chrome 창에서 LabelOn 로그인. 세션은 `.profile/chrome` 에 보존됩니다 |
| 판정 없이 "판정 모델 호출 실패" 경고 | `claude -p "hi"` 가 터미널에서 동작하는지 확인. 로그 `logs/app.log` 의 stderr 요약 확인 |
| 시작 로그에 `ANTHROPIC_API_KEY` 경고 | 환경변수가 있으면 Claude Code 가 로그인 대신 그 키를 씁니다. 의도가 아니면 변수를 제거하세요 |
| 포트 8765 사용 중 | `config.yaml` 의 `ui_port` 변경 |
| "화면 구조가 예상과 다릅니다" | LabelOn 화면이 바뀐 경우. `scripts/capture_job_page.py` 로 HTML 을 캡처해 `src/labelon_reviewer/labelon/parser.py` 의 locator 를 갱신 |
| 브라우저 창을 닫았음 | 검토 화면 오른쪽 위 "브라우저 다시 열기" |

## 구조

```
src/labelon_reviewer/
  config.py    domain.py    rules.py    diff.py    state.py    history.py    images.py
  judge.py     revise.py    schemas.py  services.py
  labelon/     browser.py(Chrome)  parser.py(페이지 파싱)  submitter.py(UI 조작 제출)
  model/       base.py  claude_cli.py(기본)  anthropic_sdk.py(대안)  fake.py
  prompts/     judge_system.md  revise_system.md
  web/         app.py(FastAPI+SSE)  static/index.html, app.js, style.css
tests/         단위·서비스·API 테스트, fixtures/job_page_sample.html
scripts/       bench_cli_context.py  capture_job_page.py
docs/          manual-checklist.md
```

설계 문서는 `aidlc-docs/` 에 있습니다.
