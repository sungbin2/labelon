# Cycle 4 Build and Test Summary - 검수 가이드 이미지 슬라이드 반영

작성일: 2026-09-28. 기존 지침과 cycle2/cycle3 요약은 그대로 유효하며 이 문서는 사이클 4 추가분만 기록한다.

## Build Status
- **Build Tool**: pip editable install
- **Build Status**: Success — `labelon-reviewer 0.4.0` (0.3.0 → 0.4.0)
- **Lint**: ruff `All checks passed!`, `node --check app.js` 통과
- **배포물**: `dist/labelon-reviewer-0.4.0.zip` (125개 파일, guide/ 제외)

## Test Execution Summary

### Unit Tests
- **Total Tests**: 108 (사이클 3: 102, +6)
- **Passed**: 108, **Failed**: 0
- **Coverage**: 78%
- **신규**: 환경 충돌 → 불가·정정 미적용·경고, 불가 플래그 3종(파라미터) → 불가·사유 문구, text_issues 만 → 수정 필요·잘못된 kind 무시·revise 프롬프트 포함, 사이클 4 필드 누락 → 문제 없음

### Integration Tests
| 시나리오 | 결과 |
|---|---|
| 서버 스모크(`--no-chrome --no-browser`): `/state` READY, `/config`, `/datasets` 폴백 688, 타 Origin POST 403, shutdown | Pass |
| Fake 모델로 judge → revise 흐름(pytest, 사이클 3 테스트 전부 유지) | Pass |
| 실제 모델이 환경 충돌(불가)과 라벨 불일치(정정)를 구분하는지 | Pending (사용자 E2E) |
| 실제 모델이 text_issues 를 과잉 생성하지 않는지(오탈자 없는 초안에서 빈 배열) | Pending (사용자 E2E) |

### Performance / Security
- 모델 호출 수 불변. judge 시스템 프롬프트가 약 1.2KB 늘어 호출당 입력 토큰 소폭 증가
- 새 엔드포인트·설정 없음

## Overall Status
- **Build**: Success / **All Tests**: Pass (자동 범위) / **Ready for Operations**: Yes

## 사용자 확인 절차 (E2E)
1. `run.bat` 재시작 → 헤더 버전 0.4.0
2. 오탈자 없는 정상 건: 판정 패널에 텍스트 오류 목록이 없고 사이클 3 과 같은 결과인지 (과잉 판정 확인, AC-C4-4)
3. 오탈자·한글 수사 숫자가 있는 건이 나오면: 텍스트 오류 목록에 표시되고 수정안에 반영되는지 (AC-C4-3, AC-C4-5)
4. 실외 도로·인도 사진에 실내 아키타입인 건: "환경 부적합" 배지와 불가 사유, 아키타입 정정 제안이 적용되지 않았는지 (AC-C4-1)
5. 불가 사유(오인식 전파·시각적 확인 요구·위험 권고)가 뜬 건: 사유 문구를 읽고 모델 판정이 타당한지. 과잉이면 화면에서 편집·승인으로 넘어가고 사례를 알려 주세요 (AC-C4-2)

## Hotfix 0.4.1 (2026-09-29)
- **증상**: 로그인 후 데이터셋 드롭다운이 비고 로그에 `datasets refreshed: []`
- **원인**: 프로젝트 홈의 탭 버튼 `data-id="v-tab-02"` 가 파서의 `id="v-tab-02"` 검색에 먼저 걸려 카드 없는 구간을 잘라냄(픽스처에는 탭 버튼 data-id 가 없어 테스트가 통과했음)
- **수정**: `labelon/parser.py` `_panel` 속성 이름 정확 일치, 픽스처 생성기·회귀 테스트(`test_parse_dataset_list_ignores_tab_button_data_id`) 추가. 109 passed
- **확인**: 0.4.2 에서 사용자가 드롭다운 6개 표시 확인 (2026-09-29)

## Hotfix 0.4.2 (2026-09-29)
- **증상**: 0.4.1 에서도 `datasets refreshed: []`
- **원인**: 원본 HTML 의 onclick 이 `jobPage(&#39;annotator&#39;, …)` 로 엔티티 이스케이프. `_CARD_RE` 는 `'` 만 허용. DOM 추출 픽스처에서는 디코딩되어 있어 테스트 통과
- **수정**: 인용부호 대안 허용, 픽스처를 원본 형태로 재생성, 엔티티·평문 테스트(`test_parse_dataset_list_accepts_entity_and_plain_quotes`). 110 passed
- **교훈**: 프로젝트 홈·작업 화면 픽스처는 반드시 요청 API 로 받은 **원본 HTML** 로 만든다(`scripts/capture_job_page.py` 방식). DOM 추출본은 엔티티가 디코딩되고 탭 버튼 등 구조가 빠질 수 있다

## Hotfix 0.4.3 (2026-09-29)
- **증상**: 헤더·이력 탭의 오늘/누적 건수가 실제와 다름
- **원인**: '오늘' = 로컬 날짜 vs UTC 저장 시각 비교(KST 09:00 이전 제출 누락), '누적' = 가져온 건수(미완료·만료·중복 포함)
- **수정**: `history.py` summary — 승인·불가 제출 완료 건 기준(건마다 마지막 성공 제출 1건), 로컬 0시를 UTC 로 환산한 경계, `unfinished`/`fetched_items` 추가. 화면 누적 카드에 미완료·가져옴 표시. 테스트 추가(로컬 날짜 경계, 실패 후 재시도, 건너뜀 제외). 111 passed
- **확인 필요**: 이력 탭 새로고침 후 오늘/누적이 LabelOn 작업량과 맞는지
