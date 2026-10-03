# Cycle 9 Code Summary - Chrome 창 크기 · 이미지 전용 탭

생성일: 2026-10-03. 계획: `cycle9-code-generation-plan.md`.

| 파일 | 변경 |
|---|---|
| `config.py`, `config.yaml`, `config.example.yaml` | `chrome.window`(maximized/가로x세로, 검증), `chrome.image_tab` |
| `labelon/browser.py` | 창 인자 선택, `_apply_window()`(CDP), `show_image()`(이미지 전용 탭 재사용, 창 맞춤 뷰어 HTML), `_image_page` |
| `services.py` | `BrowserLike.show_image`, `_analyze` 에서 이미지 탭 표시(설정·예외 보호) |
| `README.md` | 설정 표 2행 |
| `tests/` | test_config(window 형식·기본값), test_services(FakeBrowser.show_image, 가져오기 후 호출·설정 off 시 미호출) |

## 테스트
`pytest -q` → **121 passed** (사이클 8: 119). ruff 통과.

## 비고
- 사용자 답변이 B → A 로 바뀌어 B안(검토 화면 라이트박스 자동 열기) 패치는 적용 전 폐기
- 패치 실행 중 `self.page = None` 앵커가 2곳이라 중단 → 나머지를 분리 적용. 생성자에 `_image_page` 초기화 추가
- 미검증(실제 Chrome): CDP 최대화 적용, 이미지 탭이 작업 탭 앞으로 오는지, 사진이 쿠키 인증으로 로드되는지
