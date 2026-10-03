# Cycle 9 Build and Test Summary

작성일: 2026-10-03. **Build**: Success — 0.9.0, ruff 통과. **Unit**: 121 passed. 배포: git(push 는 사용자), 보조 zip.

## Pending (사용자, 실제 Chrome)
1. `run.bat` 재시작 → Chrome 창이 최대화되어 뜨는지. 크기를 고정하려면 `config.yaml` `chrome.window: "1600x1000"`
2. "다음 건 가져오기" → Chrome 에 이미지 탭이 열려 사진이 창에 맞춰 보이고(클릭으로 원본 크기 전환), 작업 탭이 뒤에 남아 있는지. 제출이 정상인지
3. 다음 건에서 같은 이미지 탭이 새 사진으로 바뀌는지
4. 끄려면 `chrome.image_tab: false`

## Hotfix 0.9.1 (2026-10-03)
- **증상**: 이미지 탭은 정상이나 Chrome 창(페이지 영역)이 제한된 크기
- **원인**: `launch_persistent_context(viewport=None)` 은 Playwright Python 에서 "기본 1280x720 에뮬레이션". OS 창은 최대화되어도 페이지는 1280x720 으로 그려짐(사이클 1부터 존재, 창 최대화 요청으로 드러남)
- **수정**: `no_viewport=True`. 임시 프로필 실험으로 innerWidth 1280 → 2560 확인
- **확인**: `run.bat` 재시작 후 Chrome 페이지가 창 전체를 채우는지
