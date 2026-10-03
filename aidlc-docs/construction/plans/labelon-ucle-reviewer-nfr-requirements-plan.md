# NFR Requirements Plan - labelon-ucle-reviewer

입력: requirements.md(NFR-1~7), functional-design/*.md, application-design.md
환경 확인(2026-09-23): Windows 11, Python 3.12.9, Playwright 1.59(Chromium 번들 설치됨), Google Chrome 설치됨, Node 24.11, Claude Code CLI 2.1.280 설치·로그인 자격증명 파일 존재, anthropic/claude-agent-sdk/fastapi 미설치

---

## Part A. NFR 결정 질문

`[Answer]:` 태그에 선택 문자를 적어 주세요. 권장안대로 하시려면 "모두 권장안"이라고 답하셔도 됩니다.

## Question 1
도구 전용 브라우저는 무엇을 사용할까요?

A) 설치된 Google Chrome을 Playwright가 `channel="chrome"`으로 실행하고 전용 user-data-dir 사용 (권장. 실제 Chrome이라 로그인·보안 UX가 평소와 같고 LabelOn이 Chrome 권장)
B) Playwright 번들 Chromium + 전용 user-data-dir
C) Other (please describe after [Answer]: tag below)

[Answer]: A (사용자 답변: "모두 권장안")

## Question 2
로컬 웹 서버 프레임워크는 무엇으로 할까요?

A) FastAPI + uvicorn. asyncio 네이티브, SSE(StreamingResponse)와 pydantic 스키마 재사용 (권장)
B) aiohttp
C) Flask (동기. SSE와 백그라운드 태스크 구현이 번거로움)
D) Other (please describe after [Answer]: tag below)

[Answer]: A (사용자 답변: "모두 권장안")

## Question 3
모델 사고 깊이(effort) 설정은 어떻게 할까요?

A) judge(sonnet-5)는 medium, revise(fable-5-1)는 high (권장. 판정은 빠르게, 수정은 정확하게)
B) 둘 다 high
C) 둘 다 low (속도 우선)
D) Other (please describe after [Answer]: tag below)

[Answer]: A (사용자 답변: "모두 권장안")

## Question 4
모델 사용량 관리는 어떻게 할까요? (구독 계정은 토큰당 과금이 아니라 사용량 한도가 적용됨)

A) 건별·누적 토큰과 호출 수를 기록·표시만 하고 상한은 두지 않음 (권장)
B) 일일 처리 건수 상한을 설정에 두고 초과 시 가져오기 차단
C) Other (please describe after [Answer]: tag below)

[Answer]: A (사용자 답변: "모두 권장안")

## Question 5
로깅은 어떻게 할까요?

A) 회전 파일 로그(logs/app.log, 5MB x 5) + 콘솔, 기본 INFO, 모델 요청·응답 본문은 DEBUG에서만 (권장)
B) 콘솔만
C) Other (please describe after [Answer]: tag below)

[Answer]: A (사용자 답변: "모두 권장안")

## Question 6
테스트 전략은 어떻게 할까요?

A) pytest 단위 테스트(파서: 2026-09-23 페이지 HTML 픽스처, 규칙 검사기, 점수, 제약 강제, diff, 상태 기계, 저장소) + 모델 목(mock) 기반 서비스 테스트 + 실브라우저·실모델은 수동 체크리스트 (권장)
B) 단위 테스트만
C) Other (please describe after [Answer]: tag below)

[Answer]: A (사용자 답변: "모두 권장안")

## Question 7
패키징과 의존성 관리는 어떻게 할까요?

A) pyproject.toml + venv + pip (권장. 추가 도구 없음)
B) uv
C) requirements.txt만
D) Other (please describe after [Answer]: tag below)

[Answer]: A (사용자 답변: "모두 권장안")

## Question 8
실행 방식은 어떻게 할까요?

A) `run.bat` 하나로 venv 활성화 → 서버 시작 → 기본 브라우저로 http://127.0.0.1:8765 자동 오픈 (권장)
B) 수동 명령(`python -m labelon_reviewer`)만 제공
C) Other (please describe after [Answer]: tag below)

[Answer]: A (사용자 답변: "모두 권장안")

## Question 9
인증 경로(RK-1) 검증은 언제 수행할까요?

A) 지금 NFR 단계에서 claude-agent-sdk를 설치하고, 이 PC의 Claude Code 로그인으로 짧은 텍스트 호출 1회를 제가 실행해 확인 (권장. 결과를 tech-stack-decisions.md에 기록. 구독 사용량이 소량 소모됨)
B) Build and Test 단계에서 사용자가 직접 실행
C) Other (please describe after [Answer]: tag below)

[Answer]: A (사용자 답변: "모두 권장안")

---

## Part B. NFR 실행 체크리스트

### B-1. NFR 요구사항 정리 (nfr-requirements.md)
- [x] 성능: 건당 시간 예산, 이미지 축소 크기와 토큰 추정, 프롬프트 캐싱 구조
- [x] 신뢰성: 재시도·타임아웃 값, 실패 시 동작, 재시작 복구
- [x] 보안·개인정보: 자격증명 비저장, localhost 바인딩, 전송 대상 2곳 한정, 로그 마스킹
- [x] 가용성: 로컬 단일 사용자, 브라우저·서버 재시작 절차
- [x] 유지보수성: 설정 스키마, 모듈 격리, 로깅, 테스트 범위
- [x] 사용성: 한국어 UI, 단축키, 응답 시간 표시
- [x] 확장성: 다른 데이터셋·모델 백엔드 전환 방식

### B-2. 기술 스택 결정 (tech-stack-decisions.md)
- [x] 런타임·언어·패키징
- [x] 브라우저 자동화(채널, 프로필 위치)
- [x] 모델 백엔드(Agent SDK 조사 결과 반영: 설치, 인증, 이미지 전달, 모델 지정, JSON 출력, 사용량 필드)
- [x] 웹 서버·SSE
- [x] 저장소·이미지 처리·스키마 라이브러리
- [x] 테스트·로깅
- [x] 설정 파일 형식과 스키마
- [x] 인증 경로 검증 결과(Q9=A인 경우 실행 로그 요약)

### B-3. 완료
- [x] aidlc-state.md 갱신, audit.md 기록, 완료 메시지
