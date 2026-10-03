# Requirements Verification Questions

LabelOn UC-LE 어노테이터 작업 자동화 도구의 요구사항을 확정하기 위한 질문입니다.
각 질문의 `[Answer]:` 태그 뒤에 선택한 문자(A, B, C ...)를 적어 주세요. 제시된 선택지에 맞는 것이 없으면 마지막 "Other"를 선택하고 설명을 덧붙여 주세요.

## 이미 확정된 사항 (답변 불필요)
- 어노테이터 역할: 서버 초안을 검토·수정하여 제출. 이미지와 내용이 전혀 다르면 불가로 제출
- 비전 모델: Claude API
- 제출 방식: 사람이 확인한 뒤 제출
- 실행 환경: 사용자 PC의 로그인된 Chrome 세션 이용
- 대상 데이터셋: 688 [업사이클링] 거주환경 (어린이3)

---

## Question 1
688 데이터셋에서 이 도구로 처리할 예상 물량은 어느 정도인가요?

A) 100건 미만 (소량, 단순 스크립트로 충분)
B) 100건 이상 1,000건 미만
C) 1,000건 이상
D) 정확히 모름, 진행중인 작업이 없어질 때까지 계속 처리
E) Other (please describe after [Answer]: tag below)

[Answer]: C

## Question 2
검수자가 사용하는 작업 가이드나 품질 기준(반려 사유) 문서가 있나요?

A) 있음. 문서(파일 또는 텍스트)를 제공할 예정
B) 없음. 작업 화면에 보이는 정보(Instruction, priority 문구 등)만으로 판단
C) 문서는 없지만 과거 반려 사례나 승인 사례를 몇 건 제공 가능
D) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 3
"이미지와 내용이 전혀 다르다"의 판단 기준은 무엇으로 할까요? (불가 제출 조건)

A) 장면 자체가 다름. 초안의 Scene이 묘사하는 장소나 핵심 사물이 이미지에 존재하지 않을 때
B) Facts 5개 중 과반(3개 이상)이 이미지에서 확인되지 않을 때
C) 모델이 정합성 점수를 매기고 임계값 이하면 불가 후보로 표시, 최종 판단은 사람이 검토 화면에서
D) Other (please describe after [Answer]: tag below)

[Answer]: C

## Question 4
검토 규칙(domain-rules.md R1~R3)에 따라 모델이 수정할 수 있는 범위는 어디까지인가요?

A) 모델이 필요한 모든 필드를 수정 (Instruction의 task 오류, Scene, Facts, CoT, QA 포함). 사람은 결과만 확인
B) Scene, Facts, CoT, QA는 모델이 수정하고, Instruction(archetype/persona/task) 불일치는 모델이 표시만 하고 사람이 결정
C) 모델은 거짓 팩트와 이미지 불일치 문장만 최소 수정. 페르소나-태스크 불일치로 CoT/QA를 다시 써야 하는 건은 사람이 처리
D) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 5
초안의 최종 답변 대화가 3턴만 채워져 있고 4~6턴은 비어 있습니다. 비어 있는 턴은 어떻게 처리할까요?

A) 비어 있는 채로 제출 (초안이 3턴이면 3턴으로 끝)
B) 모델이 페르소나에 맞게 4~6턴을 추가 생성
C) 상황에 따라 모델이 필요하다고 판단하면 추가, 아니면 유지
D) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 6
"사람 확인 후 제출"에서 확인 화면은 어떤 형태가 좋을까요?

A) 로컬 웹 페이지. 이미지, 초안과 수정안의 차이(diff), 불가 판정 근거를 보여주고 승인/수정/불가 버튼 제공
B) LabelOn 작업 화면에 수정값을 미리 채워 두고, 사용자가 화면을 보고 직접 제출 버튼만 클릭
C) 터미널(CLI)에서 건별로 텍스트 출력 후 y/n 입력
D) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 7
도구의 실행 단위는 어떻게 할까요? (LabelOn은 3건 세션, 건당 60분 제한시간)

A) 사용자가 명령을 실행하면 1세션(3건)을 분석해 검토 대기열에 올리고, 승인된 건을 제출한 뒤 종료
B) 사용자가 지정한 건수(예: 30건)를 연속 분석해 대기열에 쌓고, 사용자가 일괄 검토·제출
C) 1건씩 분석·검토·제출을 반복하는 대화형 흐름
D) Other (please describe after [Answer]: tag below)

[Answer]: C

## Question 8
Claude 모델은 어떤 구성으로 사용할까요?

A) claude-sonnet-5 단일 사용 (비용 효율)
B) claude-fable-5-1 단일 사용 (최고 품질)
C) 2단계: sonnet-5로 정합성 판정, 수정이 필요한 건만 fable-5-1로 수정 생성
D) Other (please describe after [Answer]: tag below)

[Answer]: C

## Question 9
Anthropic API 키는 어떻게 관리할까요?

A) 환경변수 ANTHROPIC_API_KEY (이미 키 보유)
B) 프로젝트의 .env 파일 (git 제외), 키는 이미 보유
C) 아직 키가 없음. 발급 후 진행
D) Other (please describe after [Answer]: tag below)

[Answer]: AUTH 인증방식

## Question 10
구현 언어와 브라우저 자동화 라이브러리는 무엇으로 할까요?

A) Python + Playwright (권장. 기존 파이프라인 디렉터리가 Python 기반)
B) Node.js(TypeScript) + Playwright
C) Python + Selenium
D) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 11
로그인된 Chrome 세션에 도구를 연결하는 방식은 무엇으로 할까요?

A) Chrome을 원격 디버깅 포트(--remote-debugging-port)로 실행하고 Playwright가 연결. 평소 쓰는 Chrome 프로필과 세션 공유
B) 도구 전용 Chrome 프로필을 Playwright가 띄우고, 사용자가 그 창에서 한 번 직접 로그인. 이후 프로필에 세션 유지
C) 사용자가 브라우저 쿠키 값을 복사해 도구에 넘김 (브라우저 UI 없이 HTTP 직접 호출)
D) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 12: Security Extensions
이 프로젝트에 보안 확장 규칙(Security Baseline)을 적용할까요?

A) 예. 모든 SECURITY 규칙을 차단 조건으로 적용 (운영급 애플리케이션에 권장)
B) 아니요. SECURITY 규칙 생략 (PoC, 프로토타입, 실험 프로젝트에 적합)
C) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 13: Property-Based Testing Extension
이 프로젝트에 속성 기반 테스트(PBT) 규칙을 적용할까요?

A) 예. 모든 PBT 규칙을 차단 조건으로 적용 (비즈니스 로직, 데이터 변환, 직렬화, 상태 컴포넌트가 있는 프로젝트에 권장)
B) 부분 적용. 순수 함수와 직렬화 왕복(round-trip)에만 PBT 적용 (알고리즘 복잡도가 낮은 프로젝트에 적합)
C) 아니요. PBT 규칙 생략 (단순 CRUD, UI 전용, 얇은 통합 계층 프로젝트에 적합)
D) Other (please describe after [Answer]: tag below)

[Answer]: C
