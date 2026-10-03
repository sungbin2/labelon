# Cycle 9 Requirements: Chrome 창 크기 · 가져오기 시 이미지 자동 표시

작성일: 2026-10-03. 깊이: Minimal. 실행 계획 포함(Code Generation → Build and Test).

## 1. Intent Analysis
| 항목 | 내용 |
|---|---|
| User Request | (1) 로그인하는 Chrome 창 크기가 제한됨 → 확장 가능하게 (2) 다음 건을 가져올 때 이미지만 자동으로 보이게 |
| Request Type | UX 개선 (Brownfield) |
| Scope | browser.py(창 크기·이미지 탭), config(chrome.window), services(가져오기 후 이미지 표시), 프론트엔드(선택) |
| Complexity | Low |

## 2. 현상 분석 (1)
- 현재 `--start-maximized` 를 넘기지만 Playwright 가 영구 프로필 Chrome 을 띄울 때 이 인자가 무시되거나 프로필의 마지막 창 크기가 복원될 수 있다. 시작 후 CDP(`Browser.setWindowBounds`)로 창 상태를 직접 지정하는 방식이 확실하다

## 3. 기능 요구사항
### FR-C9-1. Chrome 창 크기
- `config.yaml` `chrome.window`: `"maximized"`(기본) 또는 `"가로x세로"`(예: `1600x1000`). 시작 직후 CDP 로 최대화 또는 지정 크기를 적용하고, 실패하면 경고 로그만 남기고 계속 진행
- `--window-size` 인자도 지정 크기일 때 함께 전달. 사용자가 창을 드래그로 조절하는 것은 제한하지 않는다

### FR-C9-2. 가져오기 시 이미지 자동 표시 (Q1=A 확정: Chrome 이미지 전용 탭)
- A안(검토 화면): 건을 가져와 검토 대기가 되면 검토 화면에서 이미지 확대 보기(라이트박스)를 자동으로 연다. 클릭·ESC 로 닫으면 검토 진행. `ui.auto_open_image: true` 로 끄고 켤 수 있음
- B안(Chrome 이미지 탭): 건을 가져오면 Chrome 에 이미지 전용 탭을 열어(한 번 만들고 재사용) 원본 이미지를 창 크기에 맞춰 보여 준다. 작업 탭은 그대로 유지되어 제출에 영향 없음. 클릭 시 원본 크기 토글. `chrome.image_tab: true` 로 끄고 켤 수 있음
- C안: A + B

## 4. 인수 기준
- AC-C9-1 `chrome.window: maximized` 로 시작하면 Chrome 창이 최대화되고, `1600x1000` 이면 그 크기로 시작한다. CDP 실패 시에도 서버는 정상 시작
- AC-C9-2 가져오기(및 다시 판독) 시 Chrome 이미지 탭에 원본 URL 이 표시되고(`show_image` 호출), `chrome.image_tab: false` 면 호출되지 않는다
- AC-C9-3 기존 119개 테스트 유지
