# Cycle 2 Code Summary - 프로젝트(데이터셋) 선택 기능

생성일: 2026-09-28. 계획: `aidlc-docs/construction/plans/cycle2-code-generation-plan.md` (7단계 전부 [x]).

## 변경 파일 (모두 제자리 수정, 복사본 없음)

| 파일 | 변경 |
|---|---|
| `src/labelon_reviewer/domain.py` | `DatasetInfo` 추가(dataset_id, job_type, project_name, project_code, dataset_name, credit, grade, supported) |
| `src/labelon_reviewer/config.py` | `persona` 선택값(기본 ""), `dataset_id` 는 기본·폴백 의미로 주석 |
| `src/labelon_reviewer/rules.py` | 설정 페르소나 비교 제거, 빈 persona 경고, `persona_matches_config` 항상 True |
| `src/labelon_reviewer/prompts/__init__.py` | 메타 블록에 데이터셋 이름과 "이 건의 페르소나(초안 기준)" |
| `src/labelon_reviewer/labelon/parser.py` | `parse_dataset_list(html)`: `#v-tab-02` 패널의 `jobPage('annotator','AH25','id')` 카드 파싱, 미지원 타입 제외 |
| `src/labelon_reviewer/labelon/browser.py` | `fetch_project_home()` 요청 API(페이지 이동 없음, 미로그인 → LoginRequired) |
| `src/labelon_reviewer/services.py` | `DatasetState`, `DatasetService`(load_saved/save/refresh/select/effective_id/selected_name/snapshot), `AppContext.datasets`, 가져오기 대상 = effective_id, 로그인 확인 후 자동 refresh |
| `src/labelon_reviewer/history.py` | items.dataset_name 열(마이그레이션), list_recent 에 dataset_id·dataset_name, summary.by_dataset |
| `src/labelon_reviewer/web/app.py` | `GET /datasets`, `POST /datasets/refresh`, `PUT /datasets/selected`(409/422), 스냅샷에 datasets/selected_dataset_id/selected_dataset_name/datasets_error |
| `src/labelon_reviewer/web/static/index.html, app.js, style.css` | 헤더 드롭다운·새로고침, 검토 중 비활성, 메타 패널 데이터셋 배지, 이력 데이터셋 열·데이터셋별 카드, 목록 오류 배너 |
| `config.example.yaml`, `config.yaml` | 주석 갱신 |
| `tests/fixtures/make_project_home_sample.py`, `project_home_sample.html` | 프로젝트 홈 픽스처(진행중 6 + 미지원 1 + 신청가능 1) |
| `tests/test_parser.py`, `test_rules.py`, `test_services.py`, `test_history.py`, `test_web.py` | 신규·개정 테스트 10개 |

## 테스트
`pytest -q` → **84 passed** (사이클 1: 74). ruff 통과.

## 인수 기준 대응
| AC | 자동 검증 | 수동 검증 |
|---|---|---|
| AC-C2-1 목록 표시 | test_parser(6개 추출), test_web(refresh) | 실제 사이트 목록 6개 확인 |
| AC-C2-2 선택 데이터셋으로 가져오기 | test_services(opened == [685]), test_web(opened == [684]) | 다른 데이터셋 건 가져오기 |
| AC-C2-3 검토 중 전환 불가 | test_services/test_web(409) | 드롭다운 비활성 확인 |
| AC-C2-4 재시작 후 복원 | test_services(persistence) | 재시작 확인 |
| AC-C2-5 페르소나 경고 없음 | test_rules | 시각장애3 등 건 확인 |
| AC-C2-6 이력 데이터셋 열·집계 | test_history(by_dataset) | 이력 탭 확인 |

## 미검증 (Build and Test 에서 확인)
- 실제 프로젝트 홈 HTML 로 `parse_dataset_list` 결과(픽스처는 관찰 구조 재현)
- 다른 데이터셋의 작업 화면 구조가 688 과 동일한지(Facts 개수·모달)
