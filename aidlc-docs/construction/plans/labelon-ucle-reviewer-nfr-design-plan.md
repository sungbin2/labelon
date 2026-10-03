# NFR Design Plan - labelon-ucle-reviewer

입력: nfr-requirements.md, tech-stack-decisions.md, application-design/*.md, functional-design/*.md
깊이: Minimal (로컬 단일 사용자 도구)

---

## Part A. 패턴 결정 질문

`[Answer]:` 태그에 선택 문자를 적어 주세요. 권장안대로 하시려면 "모두 권장안"이라고 답하셔도 됩니다.

## Question 1 (Resilience)
모델 호출 실패에 대한 복원 패턴은 어디까지 둘까요?

A) 단순 재시도(2회, 지수 백오프)만. 최종 실패 시 초안 그대로 검토 대기 (권장. 사람이 항상 개입하는 흐름이라 서킷 브레이커 불필요)
B) A + 연속 실패 3회 시 모델 호출을 자동 중단하고 UI에 "모델 오프라인" 배너, 사용자가 재활성화
C) Other (please describe after [Answer]: tag below)

[Answer]: A (사용자 답변: "모두 권장안")

## Question 2 (Performance)
가져오기·분석 백그라운드 작업은 어떻게 실행할까요?

A) asyncio.Task 1개. 진행 중 취소(건너뛰기·종료 시) 지원. 큐 없음 (권장. 완전 순차 처리라 큐가 필요 없음)
B) asyncio.Queue 기반 워커(향후 미리 분석 확장 대비)
C) Other (please describe after [Answer]: tag below)

[Answer]: A (사용자 답변: "모두 권장안")

## Question 3 (Performance)
CLI 서브프로세스 실행 방식은 무엇으로 할까요?

A) `asyncio.create_subprocess_exec`로 비동기 실행, 타임아웃 시 프로세스 트리 종료(Windows `taskkill /T`) (권장)
B) 스레드 풀에서 `subprocess.run`
C) Other (please describe after [Answer]: tag below)

[Answer]: A (사용자 답변: "모두 권장안")

## Question 4 (Performance / Cost)
호출당 기본 컨텍스트(4~5만 토큰) 절감은 어떻게 확정할까요?

A) Code Generation에 벤치 스크립트를 포함해 Build 단계에서 플래그 조합 3가지(기본 / system-prompt 대체 / 대체 + 도구·MCP·슬래시 비활성)를 실측하고 최소 조합을 config 기본값으로 채택 (권장)
B) 절감 시도 없이 기본 컨텍스트 사용
C) Other (please describe after [Answer]: tag below)

[Answer]: A (사용자 답변: "모두 권장안")

## Question 5 (Security)
로컬 검토 서버의 요청 위조 방어는 어떻게 할까요? (브라우저의 다른 사이트가 localhost로 POST를 보낼 가능성)

A) 127.0.0.1 바인딩 + 상태 변경 요청(POST/PUT)에 `Origin`/`Host` 헤더가 `127.0.0.1:8765`인지 검사 (권장. 구현 단순)
B) A + 서버 시작 시 랜덤 토큰을 생성해 페이지에 주입, 모든 POST에 헤더로 요구
C) 방어 없음
D) Other (please describe after [Answer]: tag below)

[Answer]: A (사용자 답변: "모두 권장안")

## Question 6 (Logical Components)
Chrome 전용 프로필 창의 생명주기는 어떻게 관리할까요?

A) 서버 프로세스가 Playwright로 Chrome을 실행·소유. 서버 종료(Ctrl+C, 종료 버튼) 시 함께 정리. 사용자가 Chrome 창을 닫으면 서버가 감지해 재실행 제안 (권장)
B) 사용자가 Chrome을 따로 실행하고 서버는 연결만
C) Other (please describe after [Answer]: tag below)

[Answer]: A (사용자 답변: "모두 권장안")

---

## Part B. 설계 실행 체크리스트

### B-1. nfr-design-patterns.md
- [x] 복원: 재시도 래퍼(모델), 실패 폴백(초안 그대로 REVIEW), 만료 감지, 재시작 복구
- [x] 성능: 단일 백그라운드 태스크, 비동기 서브프로세스, 이미지 축소, 프롬프트 고정부 캐싱, 컨텍스트 절감 벤치
- [x] 보안: 자격증명 경계, localhost + Origin 검사, CLI 도구 제한, 로그 마스킹
- [x] 관측: 구조화 로그 필드, 토큰·시간 기록, SSE 하트비트
- [x] 확장: 백엔드 전략 패턴, 설정 주입

### B-2. logical-components.md
- [x] 논리 컴포넌트 목록(프로세스, 브라우저, CLI 서브프로세스, SQLite, 파일 캐시, SSE 채널, 백그라운드 태스크)과 상호작용
- [x] 프로세스·스레드·태스크 모델 다이어그램(ASCII)
- [x] 자원 한도(동시 1건, 서브프로세스 1개, DB 커넥션 1개)
- [x] 시작·종료 시퀀스

### B-3. 완료
- [x] aidlc-state.md 갱신, audit.md 기록, 완료 메시지
