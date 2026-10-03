# Functional Design Plan - labelon-ucle-reviewer

유닛 정의: Units Generation을 건너뛰었으므로 유닛 범위는 `aidlc-docs/inception/application-design/application-design.md` 전체(컴포넌트 C-01~C-14, 서비스 S-01~S-07), 스토리 US-1~US-9.
입력: requirements.md, domain-rules.md, stories.md, application-design/*.md

---

## Part A. 비즈니스 로직 결정 질문

`[Answer]:` 태그에 선택 문자를 적어 주세요. 권장안대로 하시려면 "모두 권장안"이라고 답하셔도 됩니다.

## Question 1
정합성 점수(consistency_score, 0~100) 산식은 무엇으로 할까요?

A) 가중 합. Facts 참 비율 60점 + Scene 정합 20점 + CoT·대화 정합 20점. 각 항목은 모델 판정에서 결정론적으로 계산 (권장. 재현 가능하고 임계값 조정이 직관적)
B) 모델이 종합 판단으로 0~100을 직접 채점
C) A와 B의 평균
D) Other (please describe after [Answer]: tag below)

[Answer]: A (사용자 답변: "모두 권장안")

## Question 2
팩트 판정이 "판단불가(UNKNOWN)"인 경우 점수에는 어떻게 반영할까요?

A) 참의 절반으로 계산 (예: 팩트 1개당 12점 만점이면 6점) (권장)
B) 참으로 간주
C) 거짓으로 간주
D) Other (please describe after [Answer]: tag below)

[Answer]: A (사용자 답변: "모두 권장안")

## Question 3
2단계 수정(needs_revision)을 실행하는 조건은 무엇으로 할까요?

A) 거짓 팩트 1개 이상 또는 불일치 필드(Scene, CoT, 대화 턴) 1개 이상이면 실행. 단 불가 후보(점수 ≤ 임계값)면 수정을 생략하고 사람 판단으로 넘김 (권장. 전혀 다른 이미지에 억지 수정안을 만들지 않음)
B) 위와 같되 불가 후보여도 수정안을 생성
C) 점수가 임계값 초과이고 100 미만이면 항상 실행
D) Other (please describe after [Answer]: tag below)

[Answer]: A (사용자 답변: "모두 권장안")

## Question 4
거짓으로 판정된 팩트는 어떻게 수정할까요? (Facts는 항상 5개 유지)

A) 최소 편집 우선. 방향·위치·개수 같은 틀린 부분만 고쳐 참 문장으로 만들고, 그것이 불가능하면 이미지에서 확인되는 다른 사실로 교체 (권장. 검수자가 초안과의 연속성을 인식하기 쉬움)
B) 항상 이미지 기반의 새 참 문장으로 교체
C) Other (please describe after [Answer]: tag below)

[Answer]: A (사용자 답변: "모두 권장안")

## Question 5
대화 턴 수정 범위는 어디까지인가요?

A) assistant 발화만 수정. user 발화는 초안 유지 (권장. user 발화는 시나리오 설정이므로 보존)
B) user와 assistant 모두 수정 가능
C) Other (please describe after [Answer]: tag below)

[Answer]: A (사용자 답변: "모두 권장안")

## Question 6
RuleChecker의 task 템플릿 비교는 어느 정도 허용 오차를 둘까요?

A) 페르소나 치환 후, 공백 차이와 조사 변화(가/이, 은/는, 을/를)만 허용. 그 외 글자가 다르면 불일치 (권장)
B) 완전 일치만 허용
C) 문자 유사도 95% 이상이면 일치
D) Other (please describe after [Answer]: tag below)

[Answer]: A (사용자 답변: "모두 권장안")

## Question 7
검토 화면 배치는 어떤 형태로 할까요?

A) 3열. 왼쪽 이미지(확대 가능) + 메타·연관 QA, 가운데 초안/수정안 필드별 diff와 편집란, 오른쪽 판정 요약(점수, 팩트 배지, 경고)과 동작 버튼·카운트다운 (권장. LabelOn 작업 화면과 유사한 배치라 익숙함)
B) 2열. 왼쪽 이미지, 오른쪽에 판정·편집·버튼을 세로로
C) Other (please describe after [Answer]: tag below)

[Answer]: A (사용자 답변: "모두 권장안")

## Question 8
이력의 텍스트 데이터 보관 기간은 어떻게 할까요? (이미지 캐시는 7일로 확정)

A) 무기한 보관. 용량이 작고(건당 수 KB) 반려 대응에 필요 (권장)
B) 90일 후 자동 삭제
C) Other (please describe after [Answer]: tag below)

[Answer]: A (사용자 답변: "모두 권장안")

---

## Part B. 설계 실행 체크리스트

### B-1. 도메인 엔티티 (domain-entities.md)
- [x] SourceItem, Instruction, Dialogue, Draft, InstructionCheck, FactVerdict, FieldVerdict, JudgeResult, RevisedDraft, FinalDraft, SubmissionRecord, ReviewItem, ModelUsage 필드·타입·제약 정의
- [x] 엔티티 관계도(ASCII)
- [x] SQLite 테이블 DDL(items, judge_results, revisions, final_drafts, submissions, model_usage)
- [x] LabelOn 원본 필드 ↔ 엔티티 매핑표(직렬화·역직렬화 규칙 포함)

### B-2. 비즈니스 로직 모델 (business-logic-model.md)
- [x] 판정 파이프라인 알고리즘(RuleChecker → judge 프롬프트 → 스키마 검증 → 점수 → needs_revision)
- [x] 수정 파이프라인 알고리즘(revise 프롬프트 → 제약 강제 → change_notes)
- [x] judge 출력 JSON 스키마, revise 출력 JSON 스키마
- [x] judge·revise 프롬프트 구조(고정부/가변부 분리, 캐싱 친화)
- [x] 상태 기계 전이표(상태 x 이벤트)
- [x] 제출 절차(UI 조작 단계, 대기 조건, 결과 판정)
- [x] 반환(release) 절차
- [x] Diff 알고리즘(문장 분할 규칙, 매칭)

### B-3. 비즈니스 규칙 (business-rules.md)
- [x] R1~R3 상세화(허용 오차, 판정 기준)
- [x] 점수 산식과 임계값 규칙
- [x] 수정 제약 규칙(instruction 불변, 턴 수 불변, context 불변, facts 5개, user 발화 불변, 문체 유지)
- [x] 제출 가능 조건(상태, 마감, 필수 입력)
- [x] 불가 제출 조건(사유 필수)
- [x] 오류·재시도 규칙
- [x] 이력 보관 규칙

### B-4. 프론트엔드 컴포넌트 (frontend-components.md)
- [x] 화면 레이아웃(ASCII 와이어프레임)
- [x] 컴포넌트 계층(순수 JS 모듈 단위)과 각 컴포넌트의 상태·입력
- [x] 상태별 버튼 활성화 규칙과 단축키
- [x] 편집·diff 갱신 흐름, 되돌리기
- [x] API 연동표(컴포넌트 → 엔드포인트)
- [x] 이력 탭 화면

### B-5. 검증
- [x] 모든 US 인수 기준이 규칙 또는 로직에 대응
- [x] content-validation.md(ASCII 폭, 표) 검증

### B-6. 완료
- [x] aidlc-state.md 갱신, audit.md 기록, 완료 메시지
