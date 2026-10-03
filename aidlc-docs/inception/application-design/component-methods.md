# Component Methods

표기: Python 타입 힌트. 비동기 I/O(브라우저, 모델, HTTP)는 `async`. 상세 비즈니스 규칙(점수 산식, 템플릿 비교 허용 오차, 프롬프트 본문, 스키마 필드 상세)은 Functional Design에서 정의한다.

## 실패 처리 규약
- 외부 시스템 실패는 도메인 예외로 변환한다: `LoginRequired`, `PageStructureError`, `NoJobAvailable`, `ModelCallError`, `SubmitError`, `ItemExpired`.
- 서비스 계층이 예외를 받아 상태 기계를 ERROR 또는 EXPIRED로 전이하고 UI에 사유를 전달한다.
- 컴포넌트는 예외를 삼키지 않는다. 재시도는 ModelClient 기반 클래스와 Submitter에만 둔다.

---

## C-01 ConfigLoader
```python
def load(path: Path) -> AppConfig
    # 파일 읽기 + 스키마 검증. 실패 시 ConfigError(field, reason)
```

## C-02 BrowserSession
```python
async def start() -> None                      # persistent context 시작, 기존 세션 재사용
async def is_logged_in() -> bool               # 홈 접속 후 로그아웃 링크 존재 여부
async def wait_for_login(timeout_s: int) -> None   # 로그인 페이지 표시, 사용자가 로그인할 때까지 대기. 초과 시 LoginRequired
async def open_job_page(dataset_id: int) -> PageKind   # /job/ucle/annotator?datasetId=N 이동 후 종류 반환
async def current_page_kind() -> PageKind      # JOB / HOME / LOGIN / OTHER
async def evaluate(js: str) -> Any             # 페이지 컨텍스트 JS 실행
async def close() -> None
page: Page                                     # 현재 Playwright Page
```

## C-03 LabelOnPageParser
```python
async def parse(page: Page) -> tuple[SourceItem, Draft]
    # vqaCotList[0], vqaCotResultList[0] 추출·파싱. 구조 불일치 시 PageStructureError
async def csrf_token(page: Page) -> str
def field_locators() -> FieldLocatorMap
    # Draft 필드 → CSS/순서 기반 locator (instruction 3, scene 1, facts 5, cot 3, dialogue 6x2, 가능/불가 radio, 제출 버튼, 모달 버튼)
```

## C-04 ImageService
```python
async def fetch(context: BrowserContext, item: SourceItem) -> ImagePaths
    # 쿠키 포함 다운로드 → cache/{file_name}, resized/{file_name}
def cleanup(retention_days: int) -> int        # 삭제 개수 반환
```

## C-05 RuleChecker
```python
def check(instruction: Instruction, config: AppConfig) -> InstructionCheck
```

## C-06 ModelClient (Protocol)
```python
class ModelClient(Protocol):
    async def judge(self, image: Path, item: SourceItem, draft: Draft, rules: RuleBundle) -> JudgeRaw
    async def revise(self, image: Path, item: SourceItem, draft: Draft, judge: JudgeResult) -> ReviseRaw

class BaseModelClient:                          # 공통: 재시도(최대 2회), 타임아웃, 토큰 사용량 수집, JSON 스키마 검증
    async def _call(self, model: str, system: str, user_blocks: list, schema: dict) -> tuple[dict, ModelUsage]

class ClaudeCliModelClient(BaseModelClient)     # Claude Code CLI(-p) 서브프로세스. 이미지는 파일 경로 + Read 도구, --json-schema
class AnthropicSdkModelClient(BaseModelClient)  # Anthropic SDK. 이미지는 base64 블록, structured outputs
```

## C-07 JudgeStage
```python
async def run(images: ImagePaths, item: SourceItem, draft: Draft) -> JudgeResult
    # RuleChecker.check → ModelClient.judge → 스키마 검증 → 점수·불가 후보·needs_revision 계산
```

## C-08 ReviseStage
```python
async def run(images: ImagePaths, item: SourceItem, draft: Draft, judge: JudgeResult) -> RevisedDraft
    # needs_revision False면 draft 복사 + change_notes=[] 반환(모델 호출 없음)
def enforce_constraints(original: Draft, proposed: Draft) -> Draft
    # instruction 복원, dialogue.context 복원, 턴 수 = 원본 턴 수, facts 길이 5 보정
```

## C-09 DiffService
```python
def diff(base: Draft, other: Draft) -> list[FieldDiff]
    # FieldDiff(field, segments[{op: EQUAL|INSERT|DELETE|REPLACE, base_text, other_text}])
```

## C-10 ReviewStateMachine
```python
def current() -> ReviewItem | None
def transition(event: ReviewEvent, payload: dict | None = None) -> ReviewItem
    # 이벤트: FETCH_STARTED, PARSED, JUDGED, REVISED, REVIEW_READY, EDITED, REVERTED,
    #         SUBMIT_STARTED, SUBMITTED, SUBMIT_FAILED, RELEASED, EXPIRED, FAILED, RESET
    # 허용되지 않는 전이면 IllegalTransition
def subscribe(callback: Callable[[ReviewItem], Awaitable[None]]) -> None
def remaining_seconds() -> int | None          # job_date + 60분 - now
```

## C-11 Submitter
```python
async def approve(page: Page, final: FinalDraft, locators: FieldLocatorMap) -> SubmissionRecord
    # textarea 입력(fill) → 가능 radio → 제출 클릭 → 확인 모달 클릭 → 결과 모달 텍스트 → 페이지 이동 대기
async def impossible(page: Page, reason: str, locators: FieldLocatorMap) -> SubmissionRecord
    # 불가 radio → 사유 입력 → 제출 → 확인 → 결과
async def release(page: Page, item: SourceItem, csrf: str) -> SubmissionRecord
    # 페이지가 만료 시 호출하는 반환 요청을 페이지 컨텍스트에서 수행
```

## C-12 HistoryRepository
```python
def save_item(item: SourceItem, draft: Draft) -> int            # item_id
def save_judge(item_id: int, judge: JudgeResult) -> None
def save_revision(item_id: int, revised: RevisedDraft) -> None
def save_final(item_id: int, final: FinalDraft) -> None
def save_submission(item_id: int, rec: SubmissionRecord) -> None
def mark_state(item_id: int, state: str, note: str | None = None) -> None
def list_recent(limit: int = 50) -> list[HistoryRow]
def get_detail(item_id: int) -> HistoryDetail
def summary() -> HistorySummary                                 # 오늘/누적 건수, 결과별 건수, 토큰 합계
def find_unfinished() -> list[HistoryRow]
```

## C-13 ReviewWebApp (HTTP API)
| Method | Path | 설명 |
|---|---|---|
| GET | `/` | index.html |
| GET | `/events` | SSE. ReviewItem 상태 스냅샷을 상태 변화마다 전송. 30초마다 heartbeat |
| GET | `/state` | 현재 ReviewItem 스냅샷 (초기 로드용) |
| POST | `/actions/fetch` | FetchAndAnalyzeService.run 시작 (비동기, 즉시 202) |
| PUT | `/draft` | 사용자 편집값(FinalDraft 부분) 저장, diff 재계산 |
| POST | `/actions/revert` | FinalDraft를 서버 초안으로 되돌림 |
| POST | `/actions/approve` | SubmitService.approve |
| POST | `/actions/impossible` | body {reason}. SubmitService.impossible |
| POST | `/actions/skip` | SubmitService.release |
| GET | `/history` | list_recent |
| GET | `/history/{item_id}` | get_detail |
| GET | `/history/summary` | summary |
| GET | `/images/{item_id}` | 캐시 이미지 |
| GET | `/config` | UI에 필요한 설정 일부(threshold, 데이터셋, 페르소나) |

## C-14 Frontend
- 상태별 버튼 활성화 규칙, diff 렌더링, 편집 debounce 후 PUT /draft, 카운트다운(remaining_seconds 기준 로컬 계산), 단축키(A 승인, X 불가, N 다음, R 되돌리기). 상세는 Functional Design UI 절.
