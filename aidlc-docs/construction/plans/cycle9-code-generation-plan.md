# Cycle 9 Code Generation Plan - Chrome 창 크기 · 이미지 전용 탭

## 설계 결정
- D1 `ChromeConfig.window`("maximized" | "WxH", 검증) + `window_size()`, `ChromeConfig.image_tab`(기본 true)
- D2 `BrowserSession.start`: 지정 크기면 `--window-size`, 아니면 `--start-maximized`; 시작 후 `_apply_window()` 가 CDP `Browser.setWindowBounds` 로 최대화/크기 적용(실패 시 경고)
- D3 `BrowserSession.show_image(url, caption)`: 이미지 전용 탭을 한 번 만들어 재사용, `set_content` 로 창 맞춤 뷰어(클릭 시 원본 크기 전환), `bring_to_front`. 작업 탭은 유지
- D4 `_analyze` 에서 이미지 캐시 후 `show_image` 호출(설정 true 일 때, 실패해도 계속). 다시 판독에도 적용
- D5 README 설정 표, 테스트(설정 검증, FakeBrowser.show_image 호출 확인)

## 생성 단계
- [x] Step 1 config/yaml/browser
- [x] Step 2 services/BrowserLike/tests/README
