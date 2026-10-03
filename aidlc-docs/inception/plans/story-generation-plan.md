# Story Generation Plan

프로젝트: LabelOn UC-LE 어노테이터 초안 검토 자동화 도구
역할: Product Owner
입력: `aidlc-docs/inception/requirements/requirements.md`, `domain-rules.md`

---

## Part A. 스토리 작성 방법 결정 질문

아래 질문의 `[Answer]:` 태그에 선택 문자를 적어 주세요. 맞는 선택지가 없으면 마지막 "Other"를 고르고 설명을 덧붙여 주세요.

## Question 1
페르소나는 어떻게 정의할까요?

A) 어노테이터 1명만. 사용자 본인이 도구 운영과 검토를 모두 수행 (권장. 단일 사용자 도구)
B) 어노테이터와 도구 관리자를 분리. 관리자는 설정(임계값, 모델, 데이터셋) 변경 담당
C) 어노테이터 + 도구 관리자 + LabelOn 검수자(결과물 소비자, 간접 페르소나)
D) Other (please describe after [Answer]: tag below)

[Answer]: A (사용자 답변: "모두 권장안")

## Question 2
스토리 분류 방식은 무엇으로 할까요?

A) User Journey 기반. "로그인 준비 → 건 가져오기 → 판정 확인 → 편집 → 제출/불가/건너뛰기 → 이력 확인" 흐름 순서로 정리 (권장. 검토 화면 상태 전이가 곧 사용자 여정)
B) Feature 기반. 브라우저 세션, 분석 파이프라인, 검토 UI, 제출, 이력 등 기능 묶음별로 정리
C) Epic 기반. "초안 검토 자동화" 에픽 아래 하위 스토리 계층 구조
D) Other (please describe after [Answer]: tag below)

[Answer]: A (사용자 답변: "모두 권장안")

## Question 3
스토리 크기(granularity)는 어느 정도로 할까요?

A) 화면 동작 단위. 버튼 하나, 표시 요소 묶음 하나가 스토리 하나 (약 12~16개)
B) 사용자 목표 단위. "건을 가져와 판정을 본다", "수정안을 편집해 제출한다"처럼 목표 하나가 스토리 하나 (약 7~9개) (권장)
C) Other (please describe after [Answer]: tag below)

[Answer]: B (사용자 답변: "모두 권장안")

## Question 4
인수 기준(acceptance criteria) 형식은 무엇으로 할까요?

A) Given / When / Then 형식 (테스트 시나리오로 바로 전환 가능) (권장)
B) 체크리스트 형식 (간결)
C) Other (please describe after [Answer]: tag below)

[Answer]: A (사용자 답변: "모두 권장안")

## Question 5
스토리 우선순위 표기는 어떻게 할까요?

A) MoSCoW (Must / Should / Could / Won't) (권장. 첫 구현 범위를 Must로 명확히)
B) 우선순위 표기 없음. 모두 이번 범위
C) Other (please describe after [Answer]: tag below)

[Answer]: A (사용자 답변: "모두 권장안")

---

## Part B. 분류 방식별 장단점 (참고)

| 방식 | 장점 | 단점 | 이 프로젝트 적합성 |
|---|---|---|---|
| User Journey 기반 | 검토 화면의 상태 흐름과 1:1 대응, 테스트 순서가 자연스러움 | 화면 밖 기능(설정, 이력 정리)이 여정 끝에 몰림 | 높음. 1건씩 순차 처리 흐름이 곧 여정 |
| Feature 기반 | 컴포넌트 설계와 매핑이 쉬움 | 사용자 가치가 흐려질 수 있음 | 중간 |
| Persona 기반 | 다중 사용자 유형에 유리 | 사용자가 1명이면 의미 없음 | 낮음 |
| Domain 기반 | 도메인이 여러 개일 때 유리 | 단일 도메인 | 낮음 |
| Epic 기반 | 대규모 백로그 관리에 유리 | 스토리 10개 내외에는 과함 | 낮음 |

하이브리드가 필요하면 Q2에서 Other를 선택하고 규칙을 적어 주세요(예: 여정 기반으로 정리하되 설정·이력은 Feature 묶음으로 분리).

---

## Part C. 스토리 생성 실행 체크리스트

### C-1. 준비
- [x] requirements.md의 FR-1~FR-8, NFR, AC-1~AC-8을 스토리 후보로 매핑
- [x] domain-rules.md의 R1~R3을 판정 관련 스토리의 인수 기준 소재로 정리
- [x] Part A 답변에 따라 페르소나 수, 분류 방식, 크기, 인수 기준 형식, 우선순위 표기 확정

### C-2. 페르소나 생성 (personas.md)
- [x] 각 페르소나의 역할, 목표, 어려움(pain points), 도구 사용 맥락, 성공 지표 작성
- [x] 페르소나별 관련 스토리 ID 매핑

### C-3. 스토리 생성 (stories.md)
- [x] 확정된 분류 방식으로 스토리 그룹 구성
- [x] 각 스토리를 "As a / I want / So that" 형식으로 작성
- [x] 각 스토리에 확정된 형식의 인수 기준 작성
- [x] 각 스토리에 우선순위(확정된 표기) 부여
- [x] 각 스토리에 관련 요구사항 ID(FR/NFR/AC) 연결
- [x] INVEST 검토: Independent, Negotiable, Valuable, Estimable, Small, Testable 각 항목 확인

### C-4. 검증
- [x] 모든 FR이 최소 1개 스토리에 연결되었는지 확인
- [x] 모든 AC가 최소 1개 인수 기준에 반영되었는지 확인
- [x] 범위 외 항목(Out of Scope)이 스토리에 포함되지 않았는지 확인
- [x] content-validation.md 규칙으로 마크다운·표 문법 검증

### C-5. 완료
- [x] aidlc-state.md 갱신
- [x] audit.md에 승인 프롬프트 기록 후 완료 메시지 제시
