# Cycle 2 Code Generation Plan - 프로젝트(데이터셋) 선택 기능

단일 진실. Part 2 는 이 순서대로 실행하고 완료 즉시 [x] 표시. Brownfield: 기존 파일은 제자리 수정(복사본 생성 금지).

## 유닛 컨텍스트
- 워크스페이스: `C:\Users\sbahn\label_work`, 유닛 labelon-ucle-reviewer
- 요구사항: `aidlc-docs/inception/requirements/cycle2-requirements.md` (FR-C2-1~5, AC-C2-1~6)
- 관찰한 LabelOn 프로젝트 홈 구조(2026-09-28):
  - 탭 패널 `div.v-ctn-sec#v-tab-01`(신청가능) / `#v-tab-02`(진행중) / `#v-tab-03`(신청중)
  - 카드 `div.project-box > a[onclick="jobPage('annotator', 'AH25','688')"]` 안에 `p.project-tit`(프로젝트명 "업사이클링"), `span`(코드 "UpcyclingLE"), `p.program-txt`(데이터셋명 "[업사이클링] 거주환경 (어린이3)"), 크레딧 `span.title-r-13` 숫자, 등급 "고급자"

## 설계 결정 (Functional Design 대체)
- **DatasetInfo**(domain): dataset_id, job_type(AH25 등), project_name, project_code, dataset_name, credit, grade, supported(job_type == "AH25")
- **DatasetState**(services): datasets: list[DatasetInfo], selected_id: int|None, updated_at, error: str|None. `data/ui-state.json` 에 `{"selected_dataset_id": N}` 저장
- **선택 규칙**: 상태가 READY/DONE/ERROR/EXPIRED 일 때만 변경 허용, 아니면 IllegalTransition(409). 목록에 없는 id 는 422
- **초기 선택**: ui-state 저장값 ∈ 목록 → 그것; 아니면 config.dataset_id ∈ 목록 → 그것; 아니면 목록 첫 항목; 목록이 비면 config.dataset_id(폴백, 이름 "설정 기본값")
- **가져오기 대상**: `DatasetState.effective_id()` (선택값 또는 config.dataset_id)
- **페르소나**: RuleChecker 는 archetype·template 만 검사. `persona_matches_config` 는 True 고정(하위 호환). 프롬프트의 페르소나는 `draft.instruction.persona`(비어 있으면 config.persona)
- **목록 파싱**: `#v-tab-02` 패널 HTML 만 대상. 앵커 정규식 `jobPage\('annotator',\s*'([A-Za-z0-9]+)',\s*'(\d+)'\)` + 카드 내부 `program-txt`, `project-tit`, 크레딧·등급 텍스트. supported 가 아닌 항목은 제외하고 로그
- **목록 갱신 시점**: 로그인 확인 직후 1회, `POST /datasets/refresh`, 로그인 만료 후 재로그인 시

## 생성 단계

### Step 1. 도메인·설정·규칙·프롬프트
- [x] `src/labelon_reviewer/domain.py`: `DatasetInfo` 추가
- [x] `src/labelon_reviewer/config.py`: `persona` 를 선택값(기본 "")으로, 설명 주석. `dataset_id` 는 기본·폴백으로 유지
- [x] `src/labelon_reviewer/rules.py`: 설정 페르소나 비교 제거(`persona_matches_config=True`), mismatch_details 는 archetype·task 만
- [x] `src/labelon_reviewer/prompts/__init__.py`: 메타 블록 "이 건의 페르소나" = instruction.persona (빈 값이면 config.persona)
- [x] `config.example.yaml`, `config.yaml`: persona 주석 갱신(선택, 폴백)
- [x] `tests/test_rules.py`: 페르소나 불일치 테스트를 "경고 없음"으로 변경

### Step 2. 파서: 진행중 데이터셋 목록
- [x] `src/labelon_reviewer/labelon/parser.py`: `parse_dataset_list(html) -> list[DatasetInfo]`, `IN_PROGRESS_PANEL_ID = "v-tab-02"`
- [x] `tests/fixtures/make_project_home_sample.py` + `project_home_sample.html`: 탭 3개(신청가능 1개 카드, 진행중 6개 카드 실제 이름, 신청중 0개), 미지원 타입 카드 1개 포함
- [x] `tests/test_parser.py`: 6개 추출·순서·필드, 미지원 제외, 패널 없음 → PageStructureError

### Step 3. 브라우저: 프로젝트 홈 조회
- [x] `src/labelon_reviewer/labelon/browser.py`: `fetch_project_home() -> str` (요청 API, 미로그인 리다이렉트 시 LoginRequired)
- [x] `services.BrowserLike` 프로토콜에 메서드 추가, 테스트 FakeBrowser 에 구현

### Step 4. 서비스: DatasetService
- [x] `src/labelon_reviewer/services.py`: `DatasetState`, `DatasetService(load_state/save_state/refresh/select/effective_id/snapshot)`, `AppContext.datasets`
- [x] `FetchAndAnalyzeService.run`: `cfg.dataset_id` → `ctx.datasets.effective_id()`; 상태 스냅샷에 데이터셋 이름 포함되도록 `ReviewItem` 에 `dataset_name` 세팅(source.dataset_name 사용)
- [x] `SessionService.ensure_login`: 로그인 확인 후 `DatasetService.refresh()` (실패해도 진행)
- [x] `HistoryRepository.summary`: `by_dataset` (dataset_id → {name, total, APPROVE, IMPOSSIBLE, SKIP}) 추가; `list_recent` 에 dataset_id·dataset_name(items 테이블에 dataset_name 열 없음 → items 에 `dataset_name` 열 추가: `ALTER TABLE ... ADD COLUMN` 마이그레이션, 없으면 id 표시)
- [x] `tests/test_services.py`: 선택 규칙(REVIEW 중 409), 초기 선택 우선순위, 저장·복원, refresh 실패 폴백, fetch 가 선택 id 사용
- [x] `tests/test_history.py`: by_dataset 집계, dataset_name 열 마이그레이션

### Step 5. 웹 API
- [x] `src/labelon_reviewer/web/app.py`: `GET /datasets`, `POST /datasets/refresh`, `PUT /datasets/selected {dataset_id}`; `snapshot_payload` 에 `datasets`, `selected_dataset_id`, `selected_dataset_name`, `datasets_error`; 데이터셋 변경 시 SSE 브로드캐스트
- [x] `tests/test_web.py`: 목록·선택·409·422, 스냅샷 필드

### Step 6. 프론트엔드
- [x] `index.html`: 헤더에 `<select id="dataset-select" data-testid="dataset-select">` + 새로고침 버튼 `data-testid="dataset-refresh-button"`, 건 데이터셋 배지
- [x] `app.js`: 목록 렌더·선택 변경(PUT)·새로고침(POST), 상태별 활성화(검토 중 비활성), 건의 데이터셋 이름 표시, 이력 목록 데이터셋 열, 요약 카드 데이터셋별 건수
- [x] `style.css`: select 스타일, 배지

### Step 7. 문서·요약
- [x] `README.md`: 데이터셋 선택 사용법, persona 설정 의미 변경
- [x] `aidlc-docs/construction/labelon-ucle-reviewer/code/cycle2-code-summary.md`: 변경 파일, 테스트, 미검증 항목
- [x] `aidlc-docs/inception/application-design/components.md` C-03/C-02 책임 한 줄 보강, `functional-design/business-rules.md` BR-02 개정 메모

## 스토리·인수 기준 추적
| AC | 단계 |
|---|---|
| AC-C2-1 목록 표시 | 2, 3, 4, 5, 6 |
| AC-C2-2 선택 데이터셋으로 가져오기 | 4, 6 |
| AC-C2-3 검토 중 전환 불가 | 4, 5, 6 |
| AC-C2-4 재시작 후 복원 | 4 |
| AC-C2-5 페르소나 경고 없음 | 1 |
| AC-C2-6 이력 데이터셋 열·집계 | 4, 6 |
