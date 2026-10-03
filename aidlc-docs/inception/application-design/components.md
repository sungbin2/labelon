# Components

유닛: labelon-ucle-reviewer
설계 결정: 단일 Python 프로세스(asyncio), UI 조작 제출, ModelClient 인터페이스, SSE + HTTP POST, 단일 HTML UI, Repository 패턴

---

## 핵심 데이터 구조

| 이름 | 내용 | 출처 |
|---|---|---|
| `SourceItem` | job_id(id), dataset_id, file_id, job_vqa_id, annotator_id, image_url, org_file_name, file_name, category, weather, detected_object, related_qa[{question, answer}], job_date(할당 시각), de_identification_status | vqaCotList[0] |
| `Instruction` | archetype, persona, task | vqaCotResultList[0].instruction (JSON 문자열) |
| `Dialogue` | context{user_type, situation, priority}, turns[{turn, user, assistant}] (최대 6) | finalAnswer (JSON 문자열) |
| `Draft` | instruction: Instruction, scene, facts[5], cot1(spatialContext), cot2(stateAnalysis), cot3(actionPlan), dialogue: Dialogue | vqaCotResultList[0] |
| `InstructionCheck` | archetype_known, task_matches_template, persona_matches_config, mismatch_details[] | RuleChecker |
| `FactVerdict` | index, verdict(TRUE/FALSE/UNKNOWN), evidence | JudgeStage |
| `FieldVerdict` | field(scene/cot1/cot2/cot3/turn_n), consistent(bool), note | JudgeStage |
| `JudgeResult` | fact_verdicts[], field_verdicts[], consistency_score(0~100), impossible_candidate(bool), impossible_reason_suggestion, needs_revision(bool), instruction_check, model_usage | JudgeStage |
| `RevisedDraft` | Draft(instruction은 원본 그대로) + change_notes[] + model_usage | ReviseStage |
| `FinalDraft` | 사용자가 확정한 Draft | ReviewWebApp 편집 결과 |
| `SubmissionRecord` | kind(APPROVE/IMPOSSIBLE/SKIP), payload_snapshot, response_message, success, submitted_at | Submitter |
| `ReviewItem` | SourceItem + Draft + JudgeResult? + RevisedDraft? + FinalDraft? + state + deadline + SubmissionRecord? | ReviewStateMachine |

---

## C-01. ConfigLoader
- **목적**: 설정 파일을 읽어 검증된 설정 객체를 제공
- **책임**: dataset_id, persona, archetype 템플릿 6종, threshold(기본 40), judge_model(claude-sonnet-5), revise_model(claude-fable-5-1), model_backend(agent_sdk / anthropic_sdk), image_max_side(1568), cache_retention_days(7), ui_port, chrome_profile_dir, labelon_base_url, timeouts. 문법·값 오류 시 항목명을 포함한 오류로 종료(US-9)
- **인터페이스**: `load(path) -> AppConfig`

## C-02. BrowserSession
- **목적**: 도구 전용 Chrome 프로필로 LabelOn 페이지를 열고 유지
- **책임**: Playwright persistent context 시작·종료, 로그인 상태 판별, 로그인 대기, 작업 화면 열기, 현재 페이지 종류 판별(job/home/login/other), 페이지 객체 제공, 페이지 컨텍스트 JS 실행. 비밀번호를 다루지 않음(FR-1, NFR-1.1)
- **인터페이스**: `start()`, `is_logged_in()`, `wait_for_login()`, `open_job_page(dataset_id)`, `fetch_project_home()` (사이클 2), `current_page_kind()`, `evaluate(js)`, `page`, `close()`

## C-03. LabelOnPageParser
- **목적**: 작업 화면에서 원천 데이터와 초안, CSRF를 구조화
- **책임**: 인라인 스크립트의 `vqaCotList`, `vqaCotResultList` 추출(페이지 컨텍스트 evaluate 또는 스크립트 텍스트 정규식), instruction/facts/finalAnswer JSON 문자열 파싱, 필드 누락·형식 오류 감지, 화면 textarea 순서와 Draft 필드 매핑표 제공(Submitter가 사용). LabelOn 구조 지식은 이 컴포넌트에만 둔다(NFR-6.2)
- **인터페이스**: `parse(page) -> (SourceItem, Draft)`, `csrf_token(page) -> str`, `field_locators() -> FieldLocatorMap`, `parse_dataset_list(html) -> list[DatasetInfo]` (사이클 2: 프로젝트 홈 진행중 목록)

## C-04. ImageService
- **목적**: 이미지 확보와 모델 입력용 변환
- **책임**: 브라우저 컨텍스트 쿠키로 원본 다운로드, 로컬 캐시 저장(파일명 = file_name), 긴 변 image_max_side로 축소한 JPEG 생성, 보관 일수 경과 파일 삭제(FR-2.2, FR-7.3)
- **인터페이스**: `fetch(item) -> ImagePaths(original, resized)`, `cleanup(retention_days)`

## C-05. RuleChecker
- **목적**: 모델 없이 결정론적으로 검증 가능한 규칙(R1) 처리
- **책임**: task 문구가 archetype 템플릿에 persona를 치환한 형태와 일치하는지(공백·조사 허용 규칙은 Functional Design), persona가 설정 페르소나와 일치하는지, archetype이 6종 중 하나인지 판정(FR-3.1, domain-rules R1)
- **인터페이스**: `check(instruction, config) -> InstructionCheck`

## C-06. ModelClient (인터페이스)
- **목적**: 비전 모델 호출을 추상화해 백엔드 교체 가능
- **책임**: judge, revise 두 연산. 이미지 파일과 구조화 입력을 받아 JSON 스키마에 맞는 출력을 반환. 재시도·타임아웃은 구현체 공통 기반 클래스에서 처리(NFR-4.1)
- **구현체**: `ClaudeCliModelClient`(Claude Code CLI headless 서브프로세스, 기존 로그인 자격증명. NFR 단계에서 검증·확정), `AnthropicSdkModelClient`(Anthropic SDK, API 키 또는 ant OAuth 프로파일). 선택은 config.model_backend. (초기 안의 Python Agent SDK 구현체는 NFR 단계에서 CLI 서브프로세스로 대체)
- **인터페이스**: `judge(image_path, item, draft, rules) -> JudgeRaw`, `revise(image_path, item, draft, judge) -> ReviseRaw`

## C-07. JudgeStage
- **목적**: 1단계 판정 오케스트레이션
- **책임**: 판정 프롬프트 구성(고정 규칙 부분을 앞에 두어 캐싱 친화), ModelClient.judge 호출, 출력 스키마 검증, RuleChecker 결과 병합, consistency_score와 impossible_candidate(threshold 비교), needs_revision 결정(FR-3.1, FR-4.1, FR-4.2)
- **인터페이스**: `run(image_paths, item, draft) -> JudgeResult`

## C-08. ReviseStage
- **목적**: 2단계 수정안 생성
- **책임**: 수정 프롬프트 구성(거짓 팩트, 불일치 필드, 문체 유지 지시), ModelClient.revise 호출, 제약 강제(instruction 원본 복원, 새 턴 추가 금지, context 원본 유지, facts 5개 유지), 변경 노트 생성(FR-3.2~3.5)
- **인터페이스**: `run(image_paths, item, draft, judge) -> RevisedDraft`

## C-09. DiffService
- **목적**: 초안과 수정안(또는 사용자 편집값)의 문장 단위 차이 계산
- **책임**: 필드별 문장 분할, 추가·삭제·변경 구분, UI 표시용 구조 반환(NFR-5.2)
- **인터페이스**: `diff(draft, other) -> FieldDiff[]`

## C-10. ReviewStateMachine
- **목적**: 현재 건의 상태와 전이를 단일 진실로 관리
- **책임**: 상태 READY, FETCHING, JUDGING, REVISING, REVIEW, SUBMITTING, DONE, ERROR, EXPIRED. 전이 규칙 검증(예: REVIEW가 아니면 approve 불가), 마감 시각(job_date + 60분) 추적, 상태 변화 이벤트 발행(구독자: ReviewWebApp SSE, HistoryService). 동시에 1건만 보유(FR-2.4, FR-8)
- **인터페이스**: `current() -> ReviewItem | None`, `transition(event, payload)`, `subscribe(callback)`, `remaining_seconds()`

## C-11. Submitter
- **목적**: 사용자가 확정한 결과를 LabelOn 작업 화면 UI 조작으로 제출
- **책임**: FinalDraft를 FieldLocatorMap에 따라 textarea에 입력(React 상태 갱신 보장), 가능/불가 라디오 선택, 불가 사유 입력, 제출 버튼 클릭, 확인 모달 클릭, 결과 모달 메시지 읽기, 후속 이동 감지. 건너뛰기는 페이지가 만료 시 사용하는 것과 같은 반환 요청을 페이지 컨텍스트에서 수행. 사용자 명시 호출 없이는 어떤 메서드도 호출되지 않음(NFR-4.3)
- **인터페이스**: `approve(page, final) -> SubmissionRecord`, `impossible(page, reason) -> SubmissionRecord`, `release(page, item) -> SubmissionRecord`

## C-12. HistoryRepository
- **목적**: SQLite 이력 저장·조회 격리
- **책임**: 테이블 items, judge_results, revisions, final_drafts, submissions, model_usage. 저장 메서드와 조회(최근 목록, 상세, 요약 통계, 미완료 건). 메모리 DB로 교체 가능(FR-7)
- **인터페이스**: `save_item`, `save_judge`, `save_revision`, `save_final`, `save_submission`, `mark_state`, `list_recent(limit)`, `get_detail(item_id)`, `summary()`, `find_unfinished()`

## C-13. ReviewWebApp
- **목적**: 로컬 검토 화면 제공과 사용자 동작 수신
- **책임**: localhost 바인딩 HTTP 서버(NFR-2.3), 정적 index.html 제공, SSE 스트림(/events), 동작 엔드포인트(fetch, approve, impossible, skip, revert, draft 편집 저장), 이력 조회 엔드포인트, 이미지 제공. 단축키·diff 표시·카운트다운은 프론트엔드 JS(FR-5)
- **인터페이스**: HTTP API (services.md 참조)

## C-14. Frontend (index.html)
- **목적**: 사용자 대면 화면
- **책임**: 상태 표시, 이미지 뷰어(확대), 초안·수정안 diff 렌더링, 편집 가능한 필드, Facts 판정 배지, 점수·경고 배너, 카운트다운, 버튼·단축키, 이력 탭. 순수 JS, 빌드 없음
- **인터페이스**: ReviewWebApp HTTP API 소비

---

## 요구사항 배정

| FR | 컴포넌트 |
|---|---|
| FR-1 브라우저 세션 | C-02 |
| FR-2 작업 건 가져오기 | C-02, C-03, C-04, C-10 |
| FR-3 초안 분석 | C-05, C-06, C-07, C-08 |
| FR-4 불가 판정 | C-07, C-11, C-14 |
| FR-5 검토 화면 | C-09, C-13, C-14 |
| FR-6 제출 | C-11, C-03(locator) |
| FR-7 이력 저장 | C-12, C-04(cleanup) |
| FR-8 시간 제한 처리 | C-10, C-14 |
| NFR-6 설정 분리 | C-01 |
