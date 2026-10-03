# Cycle 3 Build and Test Summary - 검수 가이드 반영

작성일: 2026-09-28. 기존 지침(build/unit/integration/performance/e2e-test-instructions.md)과 `cycle2-build-and-test-summary.md` 는 그대로 유효하며 이 문서는 사이클 3 추가분만 기록한다.

## Build Status
- **Build Tool**: pip editable install
- **Build Status**: Success — `labelon-reviewer 0.3.0` (버전 0.2.0 → 0.3.0)
- **Lint**: ruff `All checks passed!` (초기 실행에서 B007 미사용 루프 변수 2건 검출 → `revise.py` 수정 후 통과), `node --check app.js` 통과
- **배포물**: `dist/labelon-reviewer-0.3.0.zip` (guide/ 제외, 사이클 2 와 동일 구성)

## Test Execution Summary

### Unit Tests
- **Total Tests**: 102 (사이클 2: 84, +18)
- **Passed**: 102, **Failed**: 0
- **Coverage**: 78% (사이클 2: 73%)
- **신규**: 규칙(조사 선택·Task 생성·아키타입 정정·전화번호 검출/제거), 판정(불가 규칙 3종, 수정 필요 조건 4종, 누락 보정), 수정(정정 적용·미적용, 턴 drop 첫 턴 보호·재번호·user 유지·증가 금지, 전화번호 제거), diff(instruction, 삭제 턴 DELETE), 서비스(제안 적용 흐름), 제출기(Fake page: Instruction 채움·삭제 턴 비우기·건 변경 중단·facts 부족)

### Integration Tests
| 시나리오 | 결과 |
|---|---|
| 서버 스모크(`--no-chrome --no-browser`): `/state` READY, `/config` 에 6종 archetypes·모델 설정, `/datasets` 목록 없음 → 설정 기본값 688 폴백, 타 Origin POST 403, `/actions/shutdown` 정상 종료 | Pass |
| Fake 모델 + Fake page 로 judge → revise → approve 전체 흐름(pytest) | Pass |
| 실제 모델이 새 스키마 필드(`appliance_controls_visible` null, `drop`, `archetype_suggestion`)를 채우는지 | Pending (사용자 E2E) |
| 실제 화면에서 Instruction textarea fill 이 제출 본문에 반영되는지 | Pending (사용자 E2E) |

### Performance / Security
- 판정·수정 모델 호출 횟수 변화 없음(각 1회, refusal 시 폴백 1회). 프롬프트가 길어져 호출당 입력 토큰 소폭 증가
- 전화번호 검출·아키타입 정정은 로컬 정규식·문자열 치환으로 추가 비용 없음
- 새 엔드포인트 없음. Origin 검사 유지

## Overall Status
- **Build**: Success / **All Tests**: Pass (자동 범위) / **Ready for Operations**: Yes

## 사용자 확인 절차 (E2E)
1. `run.bat` 재시작(또는 zip 을 다른 PC 에 풀고 `setup.bat`) → 헤더에 버전 0.3.0, Chrome 창 로그인
2. 다음 건 가져오기 → 판정 패널에 새 항목(아키타입 제안, QA↔CoT3, 불가 사유 목록, 전화번호 경고)이 표시되는지 (AC-C3-6)
3. 아키타입 제안이 있는 건: Instruction 패널에 "수정안" 배지와 이전→이후 task 가 보이고, 되돌리기로 원본 복원되는지. 승인 제출 후 LabelOn 화면(또는 이력 payload)의 archetype/task 가 정정본인지 (AC-C3-1)
4. 턴 삭제가 있는 건: "삭제됨" 배지·취소선, 승인 다이얼로그 안내 문구, 제출 후 해당 턴 textarea 가 비었는지 (AC-C3-4)
5. Task·QA 방향 불일치 또는 거짓 팩트 3개 이상인 건: 불가 후보 배지와 사유 목록, 불가 사유 제안이 채워지는지. 불가 제출 1건 → "저장되었습니다" (AC-C3-2, AC-C3-3)
6. 전화번호가 포함된 초안이 나오면 경고와 수정안에서 제거 확인 (AC-C3-5). 해당 건이 없으면 생략
