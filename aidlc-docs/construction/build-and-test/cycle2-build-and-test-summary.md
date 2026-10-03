# Cycle 2 Build and Test Summary - 프로젝트(데이터셋) 선택 기능

작성일: 2026-09-28. 기존 지침(build/unit/integration/performance/e2e-test-instructions.md)은 그대로 유효하며 이 문서는 사이클 2 추가분만 기록한다.

## Build Status
- **Build Tool**: pip editable install
- **Build Status**: Success — `labelon-reviewer 0.2.0` (버전 0.1.0 → 0.2.0)
- **Lint**: ruff `All checks passed!`

## Test Execution Summary

### Unit Tests
- **Total Tests**: 84 (사이클 1: 74, +10)
- **Passed**: 84, **Failed**: 0
- **Coverage**: 73%
- **신규**: 목록 파싱(6개 추출·미지원 제외·패널 없음), 규칙(다른 페르소나 무경고, 빈 페르소나), DatasetService(초기 선택·저장 복원·검토 중 409·목록 없음 폴백), 로그인 후 자동 갱신, 이력 by_dataset·마이그레이션, API(목록·선택·409·422, 가져오기가 선택 데이터셋 사용)

### Integration Tests
| 시나리오 | 결과 |
|---|---|
| 실제 프로젝트 홈 카드 마크업(로그인된 브라우저 탭에서 읽기 전용 추출, 6개 카드 구조 확인)으로 파서 실행 | Pass — 688 / 450 / 고급자 / UpcyclingLE 정확히 추출. 6개 카드 모두 픽스처와 동일 구조 |
| 서버 스모크(`--no-chrome`): `GET /datasets`(목록 없음 → 설정 기본값 688), `PUT /datasets/selected` 목록 없는 id 422 / 설정 기본값 200, `/state` 에 selected_dataset_* 포함, `data/ui-state.json` 저장 | Pass |
| 기존 서비스·API 흐름(pytest) | Pass |
| 실제 로그인 → 드롭다운 6개 → 다른 데이터셋 가져오기 → 제출 | Pending (사용자 수행) |

### Performance / Security
- 목록 조회는 요청 API 1회(HTML 약 100KB 미만), 페이지 이동 없음. 추가 모델 호출 없음
- 새 엔드포인트도 Origin 검사 미들웨어 적용(POST/PUT)

## Overall Status
- **Build**: Success / **All Tests**: Pass (자동 범위) / **Ready for Operations**: Yes

## 사용자 확인 절차 (E2E)
1. `run.bat` 재시작 → Chrome 창 로그인 → 헤더 드롭다운에 진행중 데이터셋 6개가 보이는지 (AC-C2-1)
2. "시각장애3" 선택 → 다음 건 가져오기 → 메타 패널 데이터셋 배지와 Chrome 작업 화면의 데이터셋이 일치하는지, Instruction 에 페르소나 경고가 없는지 (AC-C2-2, AC-C2-5)
3. 검토 대기 상태에서 드롭다운이 비활성인지 (AC-C2-3)
4. 서버 재시작 후 같은 데이터셋이 선택되어 있는지 (AC-C2-4)
5. 이력 탭에 데이터셋 열과 데이터셋별 카드가 보이는지 (AC-C2-6)
6. 다른 데이터셋 건에서 승인 또는 불가 제출 1건 → "저장되었습니다" 기록 확인 (작업 화면 구조 동일성)
