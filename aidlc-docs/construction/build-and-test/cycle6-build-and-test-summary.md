# Cycle 6 Build and Test Summary - QA 질문 편집 · 편집 반영 지연

작성일: 2026-10-01.

## Build Status
- **Build**: Success — `labelon-reviewer 0.6.0`. ruff·node check 통과. 배포물 `dist/labelon-reviewer-0.6.0.zip`

## Test Execution Summary
- **Unit**: 114 passed, 커버리지 79%. 추가 검증: user 필드 주소·diff·검증, 제출 payload·question textarea 반영, PUT /draft turn_1_user, /config edit_delay_ms
- **Integration**: 서버 스모크(`--no-chrome`) `/config` edit_delay_ms 1500, 타 Origin 403, shutdown → Pass
- **Pending (사용자)**: 한글 입력 UX, 질문 편집 제출 1건

## Overall Status
- **Build**: Success / **All Tests**: Pass (자동 범위) / **Ready for Operations**: Yes

## 사용자 확인 절차
1. `run.bat` 재시작 → 버전 0.6.0
2. 대화 턴 카드에 "대화 N턴 user (질문)" textarea 가 보이고 편집되는지
3. 답변 칸에 한글을 빠르게 입력 → 글자가 깨지지 않고, 멈춘 뒤 약 1.5초 후 "변경됨" 태그와 diff 가 나타나는지. 다른 칸으로 이동하면 즉시 반영되는지
4. 질문을 고친 건을 승인 제출 → 이력 payload 의 `turn_N_user` 가 수정값인지
5. 지연이 길거나 짧으면 `config.yaml` 의 `ui.edit_delay_ms` 조정 후 재시작

## Hotfix 0.6.1 (2026-10-01)
- **증상**: 0.6.0 에서도 지연이 0.5초로 체감
- **원인(추정)**: 정적 파일에 캐시 헤더가 없어 브라우저가 옛 app.js(400ms 디바운스 + 편집 중 재렌더)를 재사용
- **수정**: `/` 가 index.html 을 읽어 `app.js?v=버전`·`style.css?v=버전` 으로 치환, `/`·`/static/*` 에 `Cache-Control: no-cache`. `test_index_busts_static_cache` 추가
- **확인**: `run.bat` 재시작 후 브라우저 새로고침(한 번은 Ctrl+F5 권장). 개발자 도구 Network 에서 `app.js?v=0.6.1` 이 보이면 새 코드

## Hotfix 0.6.2 (2026-10-01)
- **증상**: 질문 textarea 가 보이지 않음
- **진단**: 실행 중인 서버에 새 탭으로 접속하니 질문 textarea 3개가 정상 표시 → 사용자의 기존 탭이 서버 재시작 전 화면 코드를 유지(페이지 미새로고침)
- **수정**: 상태 페이로드에 `server_version`, 화면이 버전 변경을 감지하면 자동 새로고침(편집 중이면 blur 후). 이후 서버를 재시작하면 열려 있던 화면도 스스로 갱신됨
