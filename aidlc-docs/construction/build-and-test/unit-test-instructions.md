# Unit Test Execution

## Run Unit Tests

### 1. Execute All Unit Tests
```bat
cd C:\Users\sbahn\label_work
.venv\Scripts\python -m pytest -q
```
커버리지 포함:
```bat
.venv\Scripts\python -m pytest -q --cov=labelon_reviewer --cov-report=term-missing:skip-covered
```

### 2. Review Test Results
- **Expected**: 70 tests pass, 0 failures (2026-09-23 실행: `70 passed in 1.07s`)
- **Test Coverage**: 전체 71%. 순수 로직 모듈 85~99%. 0% 모듈은 실브라우저·실CLI·진입점(`labelon/browser.py`, `labelon/submitter.py`, `model/anthropic_sdk.py`, `__main__.py`)으로 수동 체크리스트에서 검증
- **Test Report Location**: 콘솔 출력. HTML 리포트가 필요하면 `--cov-report=html` → `htmlcov/index.html`

### 3. 테스트 구성
| 파일 | 검증 대상 |
|---|---|
| test_config.py | 설정 로드, 항목명 포함 오류, 범위·템플릿 검증 |
| test_domain.py | Draft JSON 왕복, facts 5개 패딩, 필드 주소 체계 |
| test_rules.py | 템플릿 일치(실제 초안), 조사·공백 허용, 불일치·미지 아키타입·페르소나 불일치 |
| test_diff.py | 문장 분할, 팩트 치환, 삽입·삭제 세그먼트 |
| test_state.py | 정상 경로, 수정 생략 경로, SKIP→READY, 불법 전이, 실패·만료, 구독자 통지 |
| test_history.py | 저장·조회 왕복, 요약, 미완료 |
| test_images.py | 축소 크기, 캐시 재사용, 보관 일수 정리 |
| test_model_cli.py | CLI 인자 프로필 3종, 환경변수 정리, 출력 파싱·오류, 재시도 3회, Fake |
| test_judge.py | 점수 산식(79점 예시), 수정 필요 조건, 불가 후보 시 수정 생략, 누락 보정 |
| test_revise.py | 수정 생략, 제약 강제(instruction·context·user·턴 수·facts), 빈 턴 유지 |
| test_parser.py | 실제 구조 픽스처 파싱, 시간대 보정, csrf, page_kind(JOB/HOME/LOGIN/access/OTHER) |
| test_services.py | 전 흐름(수정 없음/있음), 모델 실패 폴백, 작업 없음, 로그인 만료, 제출 전제, 만료 차단, skip·불가, 제출 실패 복귀, 마감 tick, 중복 가져오기 |
| test_web.py | 상태·설정, Origin 403, 상태 위반 409, 편집·되돌리기, 빈 사유 422, 만료 410, 404 |

### 4. Fix Failing Tests
1. 실패 테스트 이름과 assertion 메시지 확인
2. 픽스처 구조가 바뀐 경우 `tests/fixtures/make_job_page_sample.py` 를 수정 후 재생성: `.venv\Scripts\python tests\fixtures\make_job_page_sample.py`
3. 코드 수정 후 `pytest -q` 재실행, `ruff check` 통과 확인
