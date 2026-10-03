# Component Dependency

## 의존 행렬

행이 열에 의존한다(호출한다). `o` = 의존.

| 의존 → | C-01 Config | C-02 Browser | C-03 Parser | C-04 Image | C-05 Rule | C-06 Model | C-07 Judge | C-08 Revise | C-09 Diff | C-10 State | C-11 Submit | C-12 History |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C-02 BrowserSession | o | | | | | | | | | | | |
| C-03 PageParser | | | | | | | | | | | | |
| C-04 ImageService | o | | | | | | | | | | | |
| C-05 RuleChecker | o | | | | | | | | | | | |
| C-06 ModelClient | o | | | | | | | | | | | |
| C-07 JudgeStage | o | | | | o | o | | | | | | |
| C-08 ReviseStage | o | | | | | o | | | | | | |
| C-09 DiffService | | | | | | | | | | | | |
| C-10 StateMachine | | | | | | | | | | | | |
| C-11 Submitter | | | o | | | | | | | | | |
| C-12 HistoryRepo | o | | | | | | | | | | | |
| C-13 ReviewWebApp | o | | | | | | | | o | o | | o |
| S-01 SessionService | | o | | | | | | | | o | | |
| S-02 FetchAndAnalyze | o | o | o | o | | | o | o | o | o | | o |
| S-03 EditService | | | | | | | | | o | o | | o |
| S-04 SubmitService | | o | o | | | | | | | o | o | o |
| S-05 DeadlineService | | | | | | | | | | o | | o |
| S-06 HistoryService | | | | o | | | | | | o | | o |

- 컴포넌트(C-xx)는 다른 컴포넌트에 최소로 의존하고, 조합은 서비스(S-xx)가 담당한다.
- C-03 PageParser, C-09 DiffService, C-10 StateMachine은 순수 계층(외부 의존 없음)이라 단위 테스트가 쉽다.
- 순환 의존 없음. 방향은 항상 "서비스 → 컴포넌트", "컴포넌트 → 설정/하위 컴포넌트".

## 통신 패턴

| 구간 | 패턴 |
|---|---|
| Frontend ↔ ReviewWebApp | HTTP POST/PUT/GET(동작·조회), SSE(상태 푸시). 모두 localhost |
| ReviewWebApp → 서비스 | 동일 프로세스 비동기 호출. fetch는 백그라운드 태스크로 실행하고 202 즉시 반환 |
| 서비스 → StateMachine | 동기 transition 호출. StateMachine → 구독자(ReviewWebApp SSE 브로드캐스터, HistoryService)에 이벤트 콜백 |
| BrowserSession → LabelOn | Playwright(Chromium) 페이지 조작, 페이지 컨텍스트 JS |
| ImageService → images.labelon.kr | 브라우저 컨텍스트의 request API(쿠키 공유) |
| ModelClient → Claude | Agent SDK 또는 Anthropic SDK. 이미지 + 텍스트 → JSON |
| HistoryRepository → SQLite | 로컬 파일 DB, 단일 커넥션(asyncio 환경에서는 스레드 실행기로 위임) |

## 데이터 흐름

```
+-------------------+        +-------------------+        +---------------------+
|  LabelOn 작업화면  | -----> | C-03 PageParser   | -----> | SourceItem + Draft  |
|  (C-02 Browser)   |        +-------------------+        +----------+----------+
+---------+---------+                                                |
          |  image url (cookies)                                     |
          v                                                          v
+-------------------+        +-------------------+        +---------------------+
| C-04 ImageService | -----> | resized.jpg       | -----> | C-07 JudgeStage     |
+-------------------+        +-------------------+        |  + C-05 RuleChecker |
                                                          |  + C-06 Model.judge |
                                                          +----------+----------+
                                                                     | JudgeResult
                                                                     v
                                                          +---------------------+
                                                          | C-08 ReviseStage    |
                                                          |  + C-06 Model.revise|
                                                          +----------+----------+
                                                                     | RevisedDraft
                                                                     v
+-------------------+        +-------------------+        +---------------------+
| C-14 Frontend     | <----- | C-13 ReviewWebApp | <----- | C-10 StateMachine   |
|  (diff, edit,     |  SSE   |  + C-09 Diff      |        |  ReviewItem(REVIEW) |
|   approve/불가)   | -----> |                   | -----> |                     |
+-------------------+  POST  +-------------------+        +----------+----------+
                                                                     | FinalDraft
                                                                     v
+-------------------+        +-------------------+        +---------------------+
|  LabelOn 작업화면  | <----- | C-11 Submitter    | <----- | S-04 SubmitService  |
|  textarea/버튼    |        |  (UI 조작 제출)    |        +---------------------+
+-------------------+        +-------------------+                   |
                                                                     v
                                                          +---------------------+
                                                          | C-12 HistoryRepo    |
                                                          |  (SQLite)           |
                                                          +---------------------+
```

흐름 설명: 브라우저가 연 작업 화면에서 파서가 원천 데이터와 초안을 뽑고, 이미지 서비스가 축소 이미지를 만든다. 판정 단계가 규칙 검사와 모델 판정을 합쳐 JudgeResult를 내고, 필요하면 수정 단계가 RevisedDraft를 만든다. 상태 기계가 REVIEW 상태의 ReviewItem을 보유하고 웹앱이 SSE로 프론트엔드에 전달한다. 사용자의 승인 동작이 SubmitService를 거쳐 Submitter가 같은 작업 화면의 입력란과 버튼을 조작해 제출한다. 모든 단계의 결과는 이력 저장소에 기록된다.

## 외부 의존과 격리 지점

| 외부 요소 | 격리 컴포넌트 | 변경 시 수정 범위 |
|---|---|---|
| LabelOn 페이지 구조(스크립트 변수명, textarea 순서, 모달) | C-03 PageParser(파싱·locator), C-11 Submitter(조작 절차) | 두 컴포넌트만 |
| LabelOn 엔드포인트(반환 요청) | C-11 Submitter.release | 한 메서드 |
| Claude 인증·SDK | C-06 구현체 | 구현체 교체, 설정 1줄 |
| Chrome 실행·프로필 | C-02 BrowserSession | 한 컴포넌트 |
