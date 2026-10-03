# Application Design Plan

프로젝트: LabelOn UC-LE 어노테이터 초안 검토 자동화 도구
유닛: labelon-ucle-reviewer (단일)
입력: requirements.md, domain-rules.md, stories.md, personas.md, execution-plan.md

---

## Part A. 설계 결정 질문

아래 질문의 `[Answer]:` 태그에 선택 문자를 적어 주세요. 맞는 선택지가 없으면 마지막 "Other"를 고르고 설명을 덧붙여 주세요. 권장안대로 하시려면 "모두 권장안"이라고 답하셔도 됩니다.

## Question 1
프로세스 구조는 어떻게 할까요?

A) 단일 Python 프로세스. 로컬 웹 서버, Playwright 브라우저 제어, 모델 호출을 하나의 asyncio 이벤트 루프에서 운용 (권장. 실행이 명령 하나로 끝나고 상태 공유가 단순)
B) 두 프로세스 분리. 백엔드(Playwright + 모델)와 UI 서버를 따로 띄우고 로컬 HTTP로 통신
C) Other (please describe after [Answer]: tag below)

[Answer]: A (사용자 답변: "모두 권장안")

## Question 2
LabelOn 제출은 어떤 경로로 수행할까요? (요구사항 FR-6.2에서 설계 단계 확정 항목)

A) UI 조작 경로. 열려 있는 작업 화면의 textarea에 최종 값을 채우고 실제 "제출" 버튼과 확인 모달을 클릭 (권장. 플랫폼의 jobStatus 결정·검증·후처리를 그대로 따르므로 RK-4가 자연히 해소되고 서버 관점에서 사람 제출과 구별되지 않음)
B) 직접 호출 경로. 페이지 컨텍스트에서 fetch로 `/job/ucle/annotator/set`에 JSON 본문을 전송 (빠르고 UI 변경에 덜 민감하지만 jobStatus 등 본문 값을 도구가 직접 결정해야 함)
C) 기본은 A, A가 실패하면 B로 대체
D) Other (please describe after [Answer]: tag below)

[Answer]: A (사용자 답변: "모두 권장안")

## Question 3
모델 호출 계층은 어떻게 구성할까요?

A) 모델 클라이언트 인터페이스(judge, revise 두 연산)를 두고 구현체를 교체 가능하게 설계. 1차 구현은 Claude Agent SDK, 대안 구현은 Anthropic SDK(OAuth 프로파일) (권장. RK-1 결과에 따라 코드 변경 없이 전환)
B) Claude Agent SDK를 직접 호출. 추상화 없음
C) Other (please describe after [Answer]: tag below)

[Answer]: A (사용자 답변: "모두 권장안")

## Question 4
검토 화면과 백엔드 사이의 진행 상태 전달 방식은 무엇으로 할까요?

A) Server-Sent Events(SSE)로 상태 변화를 서버가 푸시하고, 동작(가져오기, 승인 등)은 일반 HTTP POST (권장. 단방향 푸시로 충분하고 구현이 단순)
B) WebSocket 양방향
C) 클라이언트 주기 폴링(1~2초)
D) Other (please describe after [Answer]: tag below)

[Answer]: A (사용자 답변: "모두 권장안")

## Question 5
검토 화면 프론트엔드는 어떻게 만들까요?

A) 단일 HTML 파일 + 순수 JavaScript + CSS. 빌드 도구 없음 (권장. 화면이 1개이고 배포·유지가 가장 단순)
B) React 또는 Vue + Vite 빌드
C) Other (please describe after [Answer]: tag below)

[Answer]: A (사용자 답변: "모두 권장안")

## Question 6
이력 저장소 접근 방식은 어떻게 할까요?

A) Repository 패턴. 저장·조회 메서드를 한 클래스에 모아 SQLite 접근을 격리 (권장. 테스트에서 메모리 DB로 교체 가능)
B) 각 컴포넌트가 sqlite3를 직접 사용
C) Other (please describe after [Answer]: tag below)

[Answer]: A (사용자 답변: "모두 권장안")

---

## Part B. 설계 실행 체크리스트

### B-1. 컨텍스트 분석
- [x] requirements.md의 FR/NFR과 stories.md의 US-1~9를 기능 영역으로 묶기
- [x] 2026-09-23 LabelOn 페이지 분석 결과(스크립트 변수, 엔드포인트, 필드 구조)를 파서·제출기 설계 입력으로 정리
- [x] Part A 답변 반영

### B-2. components.md
- [x] 컴포넌트 정의: 이름, 목적, 책임, 인터페이스(외부에 노출하는 연산)
- [x] 후보: BrowserSession, LabelOnPageParser, ImageService, ModelClient(인터페이스), JudgeStage, ReviseStage, RuleChecker(R1 템플릿 검사), ReviewStateMachine, Submitter, HistoryRepository, ConfigLoader, ReviewWebApp(UI 서버)
- [x] 각 컴포넌트가 다루는 핵심 데이터 구조(원천 데이터, 초안, 판정 결과, 수정안, 제출 본문) 정의

### B-3. component-methods.md
- [x] 컴포넌트별 메서드 시그니처(입력·출력 타입, 목적 한 줄)
- [x] 예외·실패 반환 방식 통일
- [x] 상세 비즈니스 규칙은 Functional Design으로 위임 표기

### B-4. services.md
- [x] 오케스트레이션 서비스 정의: FetchAndAnalyzeService(가져오기 → 파싱 → 이미지 → 판정 → 수정), SubmitService(승인/불가/건너뛰기), SessionService(로그인 상태·세션 유지), HistoryService
- [x] 서비스 간 호출 순서와 상태 전이 연결

### B-5. component-dependency.md
- [x] 의존 행렬(컴포넌트 x 컴포넌트)
- [x] 통신 패턴(동기 호출, 이벤트, SSE)
- [x] 데이터 흐름 다이어그램(ASCII, ascii-diagram-standards.md 준수)

### B-6. application-design.md (통합 문서)
- [x] 위 4개 문서 요약 통합
- [x] 스토리 → 서비스 → 컴포넌트 추적표

### B-7. 검증
- [x] 모든 FR이 최소 1개 컴포넌트에 배정
- [x] 모든 US가 최소 1개 서비스에 연결
- [x] 순환 의존 없음
- [x] content-validation.md 규칙(ASCII 폭, 마크다운 표) 검증

### B-8. 완료
- [x] aidlc-state.md 갱신
- [x] audit.md 승인 프롬프트 기록 후 완료 메시지
