# Requirements: LabelOn UC-LE 어노테이터 초안 검토 자동화 도구

작성일: 2026-09-23
깊이: Standard
관련 문서: `domain-rules.md`(검토 규칙), `requirement-verification-questions.md`, `requirement-clarification-questions.md`

---

## 1. Intent Analysis

| 항목 | 내용 |
|---|---|
| User Request | LabelOn(labelon.kr) 진행중인 작업 중 UC-LE 데이터셋 688의 어노테이터 작업을 자동화. 서버가 미리 채운 초안을 이미지와 대조해 검토·수정하고, 사람이 확인한 뒤 제출 |
| Request Type | New Project (Greenfield) |
| Scope Estimate | Multiple Components: 브라우저 연동, 페이지 데이터 파싱, 비전 모델 분석 파이프라인, 검토 웹 UI, 제출, 이력 저장 |
| Complexity Estimate | Moderate |
| Request Clarity | Clear (질문 13개 + 명확화 2개로 확정) |

## 2. Background: 대상 시스템 구조 (2026-09-23 분석)

- 작업 화면 URL: `https://www.labelon.kr/job/ucle/annotator?datasetId=688`. 프로젝트 타입 AH25, 도구 모드 "UC-LE".
- 페이지 인라인 스크립트에 두 JSON 배열이 포함된다.
  - `vqaCotList`: 원천 데이터. 이미지 URL(images.labelon.kr, 4000x3000), orgFileName, category, weather, detectedObject, 연관 QA 목록(qaList), jobStatus, jobDate, id, fileId, jobVqaId, annotatorId, deIdentificationStatus.
  - `vqaCotResultList`: 서버 초안. instruction(JSON 문자열: archetype/persona/task), scene, facts(JSON 배열 문자열, 5개), cot1~cot3, finalAnswer(JSON 문자열: context{user_type, situation, priority}, dialogue[{turn, user, assistant}]).
- 화면 필드: Instruction 3개, Scene 1개, Facts 5개, CoT 3단계, 최종 답변 QA 6쌍(초안은 3턴만 채워짐), 이미지 작업 가능 여부(가능/불가), 제출 버튼.
- 제출: `POST /job/ucle/annotator/set` (JSON). 헤더 `X-CSRF-TOKEN` = `#csrf` hidden input 값. 본문 result{instruction, scene, facts, spatialContext, stateAnalysis, actionPlan, finalAnswer}, datasetId, id, fileId, deIdentificationStatus, workText, jobStatus, jobDate, inspectionDate, visionFilterOptions, impossibleMsg, isDataUpdate. 불가 제출은 jobStatus "AK04" + impossibleMsg.
- 페이지를 열면 해당 건이 이 계정에 할당되고 60분 제한시간이 시작된다. 시간 초과 시 클라이언트가 `POST /job/ucle/annotator/resetData`를 호출해 반환한다. 1분마다 `POST /job/ucle/refreshSession`으로 로그인 세션을 유지한다. 세션 단위 작업량은 3건(allWorkCount=3).
- 제출 후 클라이언트는 같은 URL로 재이동하며 다음 건이 열린다.

## 3. Functional Requirements

### FR-1. 브라우저 세션
- FR-1.1 도구 전용 Chrome 프로필을 Playwright(Python)가 실행한다. 프로필 디렉터리는 로컬에 유지되어 로그인 세션이 보존된다.
- FR-1.2 로그인이 필요하면 도구는 LabelOn 로그인 페이지를 띄우고 사용자가 직접 로그인할 때까지 대기한다. 도구는 비밀번호를 저장하거나 입력하지 않는다.
- FR-1.3 작업 화면이 열려 있는 동안 LabelOn의 세션 갱신이 정상 동작하도록 페이지를 유지한다.

### FR-2. 작업 건 가져오기
- FR-2.1 사용자가 검토 화면에서 "다음 건 가져오기"를 누르면 도구가 `datasetId=688` 작업 화면을 열고 `vqaCotList`, `vqaCotResultList`, 이미지 URL, CSRF 토큰을 파싱한다.
- FR-2.2 이미지를 내려받아 로컬에 캐시하고, 모델 입력용으로 축소본(긴 변 1568px 이하)을 만든다.
- FR-2.3 남은 작업이 없거나 페이지가 작업 화면이 아니면(예: 프로젝트 홈으로 리다이렉트) 사용자에게 사유를 표시한다.
- FR-2.4 한 번에 1건만 할당된 상태를 유지한다(완전 순차). 다음 건은 현재 건을 제출하거나 반환한 뒤에만 가져온다.

### FR-3. 초안 분석 (2단계 모델 파이프라인)
- FR-3.1 1단계(판정, claude-sonnet-5): 이미지, 초안 전체, 연관 QA 목록, domain-rules.md의 규칙을 입력으로 다음을 산출한다.
  - Facts 각 문장의 참/거짓/판단불가와 근거
  - Scene, CoT 1~3, 대화 각 턴의 이미지 정합성 판정
  - Instruction 정합성: task가 archetype 템플릿과 일치하는지, persona가 데이터셋 페르소나와 일치하는지, CoT/QA가 persona·task에 맞는지 (R1)
  - 이미지 정합성 점수 0~100과 "불가 후보" 여부
- FR-3.2 2단계(수정, claude-fable-5-1): 1단계에서 수정이 필요하다고 판정된 건에 대해 Scene, Facts, CoT 1~3, 대화 턴을 수정한 안을 생성한다. 수정은 이미지에 근거한 사실로만 하고, 문체(아이에게 말하는 반말 등 finalAnswer.context.priority 문구)와 구조를 유지한다.
- FR-3.3 Instruction(archetype, persona, task)은 모델이 수정하지 않는다. 불일치가 감지되면 검토 화면에 경고로 표시하고 사람이 결정한다.
- FR-3.4 비어 있는 대화 턴(4~6)은 추가 생성하지 않고 비운 채 유지한다.
- FR-3.5 1단계 판정 결과 수정 불필요이면 2단계를 생략한다.
- FR-3.6 모델 출력은 구조화된 JSON 스키마로 받는다(structured outputs 또는 동등 수단).

### FR-4. 불가 판정
- FR-4.1 정합성 점수가 임계값(기본 40, 설정 가능) 이하이면 불가 후보로 표시한다.
- FR-4.2 불가 후보의 근거(어떤 사물·장면이 이미지에 없는지)와 제안 불가 사유 문구를 함께 표시한다.
- FR-4.3 최종 불가 여부는 사람이 검토 화면에서 결정한다. 불가 제출 시 jobStatus "AK04", impossibleMsg에 사유를 담아 제출한다.

### FR-5. 검토 화면 (로컬 웹 페이지)
- FR-5.1 로컬 웹 서버가 브라우저에서 열리는 단일 페이지를 제공한다.
- FR-5.2 표시 요소: 원본 이미지(확대 가능), 메타데이터, 연관 QA 목록, Instruction, 초안과 수정안의 필드별 diff, Facts별 판정과 근거, 정합성 점수, 불가 후보 경고, Instruction 불일치 경고, 잔여 제한시간.
- FR-5.3 사용자는 수정안의 모든 텍스트 필드를 직접 편집할 수 있다.
- FR-5.4 동작 버튼: 다음 건 가져오기, 승인·제출(수정안 그대로 제출), 불가 제출(사유 입력), 초안 원본으로 되돌리기, 이 건 건너뛰기(반환).
- FR-5.5 분석 진행 상태(가져오는 중, 1단계 분석 중, 2단계 수정 중, 검토 대기)를 표시한다.

### FR-6. 제출
- FR-6.1 승인 시 검토 화면의 최종 값으로 제출 본문을 구성한다. facts는 JSON 배열 문자열, finalAnswer는 초안과 같은 구조(context 유지, dialogue의 user/assistant만 갱신)의 JSON 문자열로 직렬화한다.
- FR-6.2 제출은 열려 있는 작업 화면 컨텍스트에서 수행한다(같은 세션 쿠키와 CSRF 토큰 사용). UI 폼에 값을 채워 제출 버튼을 누르는 방식과 페이지 컨텍스트에서 fetch로 `/job/ucle/annotator/set`을 호출하는 방식 중 설계 단계에서 하나를 확정한다.
- FR-6.3 제출 응답(result, message)을 확인해 성공/실패를 검토 화면에 표시한다. 실패 시 재시도 여부를 사용자가 선택한다.
- FR-6.4 정상 제출 시 사용할 jobStatus 값과 deIdentificationStatus, visionFilterOptions 기본값은 실제 UI 제출을 1회 관찰해 확정한다(설계 단계 조사 항목).

### FR-7. 이력 저장
- FR-7.1 건별로 원천 데이터, 초안, 1단계 판정, 2단계 수정안, 사용자 최종 편집값, 제출 본문, 제출 응답, 타임스탬프, 모델 사용 토큰을 로컬 SQLite에 저장한다.
- FR-7.2 검토 화면에서 최근 처리 이력 목록과 건별 상세를 조회할 수 있다.
- FR-7.3 이미지 원본 캐시는 설정한 보관 일수 후 삭제한다(기본 7일).

### FR-8. 시간 제한 처리
- FR-8.1 건을 가져온 시점부터 60분 제한시간을 추적해 검토 화면에 표시하고, 10분 미만이면 경고한다.
- FR-8.2 제한시간이 초과되면 LabelOn이 건을 반환하므로, 도구는 현재 건을 "만료"로 기록하고 사용자에게 다시 가져오기를 안내한다.

## 4. Non-Functional Requirements

### NFR-1. 인증과 자격증명
- NFR-1.1 LabelOn 로그인: 사용자가 도구 전용 Chrome 프로필에서 직접 수행. 도구는 자격증명을 저장하지 않는다.
- NFR-1.2 Claude 호출 인증: Claude 구독 계정의 로그인 자격증명을 재사용한다. API 키를 발급·저장하지 않는다.
  - 1순위: Claude Agent SDK(Python `claude-agent-sdk`). Claude Code 로그인 자격증명을 그대로 사용하며 이미지 입력과 모델 지정을 지원한다.
  - 대안: Anthropic CLI `ant auth login`으로 OAuth 프로파일을 만들고 Anthropic Python SDK가 자동으로 읽게 한다(Console 조직 계정 필요, 현재 PC에 ant 미설치).
  - 설계 단계(NFR Requirements)에서 사용자 계정 유형을 확인해 경로를 확정한다.

### NFR-2. 개인정보와 데이터 취급
- NFR-2.1 거주환경 사진과 초안 텍스트가 Anthropic API로 전송된다. 사용자가 이를 인지하고 승인했다(질문 답변).
- NFR-2.2 모든 이력과 이미지 캐시는 사용자 PC 로컬에만 저장한다. 외부 서버 전송은 LabelOn과 Anthropic 두 곳으로 한정한다.
- NFR-2.3 검토 화면 웹 서버는 localhost에만 바인딩한다.

### NFR-3. 성능
- NFR-3.1 건당 처리 시간(가져오기 + 1단계 + 2단계) 목표 90초 이내, 최대 3분. 60분 제한시간 대비 충분한 검토 여유를 확보한다.
- NFR-3.2 1,000건 이상 처리를 전제로 하므로 모델 프롬프트의 고정 부분(규칙, 템플릿, 출력 스키마)은 프롬프트 캐싱이 가능한 구조로 앞에 배치한다.

### NFR-4. 신뢰성
- NFR-4.1 모델 호출 실패(네트워크, 속도 제한, refusal)는 최대 2회 재시도 후 사용자에게 표시한다. 실패해도 현재 건은 초안 그대로 검토·제출할 수 있어야 한다.
- NFR-4.2 도구가 비정상 종료되어도 할당된 건은 LabelOn의 60분 만료로 자동 반환된다. 재시작 시 이력 DB에서 미완료 건을 표시한다.
- NFR-4.3 제출은 사용자의 명시적 클릭 없이는 절대 발생하지 않는다.

### NFR-5. 사용성
- NFR-5.1 한국어 UI.
- NFR-5.2 diff는 문장 단위로 추가·삭제·변경을 색으로 구분한다.
- NFR-5.3 키보드 단축키(승인, 불가, 다음)를 제공한다.

### NFR-6. 유지보수성
- NFR-6.1 아키타입 템플릿, 페르소나, 임계값, 모델 ID, 데이터셋 ID는 설정 파일로 분리한다.
- NFR-6.2 LabelOn 페이지 구조(스크립트 변수명, 엔드포인트)는 한 모듈에 격리해 변경 시 수정 범위를 제한한다.

### NFR-7. 비용
- NFR-7.1 건별 토큰 사용량을 기록하고 검토 화면에서 누적 사용량을 볼 수 있다.
- NFR-7.2 2단계(fable-5-1)는 수정 필요 건에만 호출한다.

## 5. Constraints and Assumptions

- 대상은 데이터셋 688 한 곳. 다른 UC-LE 데이터셋(687, 682)은 설정으로 확장 가능하게 하되 이번 범위에서 검증하지 않는다.
- 데이터셋 688의 페르소나는 "장난기가 많은 어린아이"로 가정한다. 설정 파일에 두어 변경 가능하게 한다.
- 품질 기준 문서는 없다. 판단 근거는 domain-rules.md와 화면의 Instruction, finalAnswer.context.priority 문구다.
- 확장 규칙: Security Baseline 미적용, Property-Based Testing 미적용.
- 실행 환경: Windows 11, Python 3.12, Playwright 1.59(설치됨), Chrome.

## 6. Out of Scope

- 검수자(리뷰어) 작업 자동화
- 비어 있는 대화 턴의 신규 생성
- Instruction 필드의 자동 수정
- 사람 확인 없는 완전 자동 제출
- 서버 헤드리스 운영, 다중 사용자

## 7. Risks

| ID | 리스크 | 영향 | 대응 |
|---|---|---|---|
| RK-1 | 구독 계정 자격증명의 프로그램적 재사용 경로(Claude Agent SDK)가 계정 유형이나 정책에 따라 제한될 수 있음 | 모델 호출 불가 | NFR 단계에서 실제 계정으로 1회 호출 검증. 대안(ant OAuth 프로파일) 준비 |
| RK-2 | LabelOn 페이지 구조 변경 | 파싱·제출 실패 | 파서 모듈 격리, 구조 검증 실패 시 즉시 중단·알림 |
| RK-3 | 모델이 이미지에 없는 내용을 "수정안"으로 생성(환각) | 검수 반려 | Facts별 근거 요구, 사람 확인 필수, 수정 최소화 지시 |
| RK-4 | 정상 제출 jobStatus 등 미확인 필드 값 | 잘못된 상태로 제출 | 설계 단계에서 실제 UI 제출 1회 관찰 후 확정 |
| RK-5 | 60분 제한시간 내 검토 미완료 | 건 반환, 작업 손실 | 잔여 시간 표시·경고, 만료 기록 |

## 8. Acceptance Criteria

- AC-1 사용자가 "다음 건 가져오기"를 누르면 3분 이내에 이미지, 초안, 판정, 수정안이 검토 화면에 표시된다.
- AC-2 Facts 5개 각각에 참/거짓/판단불가 판정과 근거가 표시된다.
- AC-3 archetype 템플릿과 task 문구가 불일치하는 초안을 넣으면 Instruction 경고가 표시된다.
- AC-4 이미지와 무관한 초안(테스트용 조합)을 넣으면 정합성 점수가 임계값 이하로 표시되고 불가 후보로 표시된다.
- AC-5 승인 버튼을 누르기 전에는 LabelOn에 어떤 제출 요청도 발생하지 않는다.
- AC-6 승인 제출 후 LabelOn 작업내역에 해당 건이 반영되고, 이력 DB에 제출 본문과 응답이 저장된다.
- AC-7 불가 제출 시 jobStatus AK04와 사유가 전송된다.
- AC-8 도구에 LabelOn 비밀번호나 Anthropic API 키가 저장된 파일이 존재하지 않는다.

## 9. Traceability (질문 답변 → 요구사항)

| 출처 | 답변 | 반영 |
|---|---|---|
| 사전 Q1 | 초안 검토·수정, 전혀 다르면 불가 | FR-3, FR-4 |
| 사전 Q2 | Claude API | FR-3, NFR-1.2 |
| 사전 Q3 | 사람 확인 후 제출 | FR-5, FR-6, NFR-4.3 |
| 사전 Q4 | 내 PC Chrome 세션 | FR-1, NFR-1.1 |
| 사전 Q5 | 데이터셋 688 | 제약 |
| Q1=C | 1,000건 이상 | NFR-3.2, FR-7 |
| Q2=B | 가이드 문서 없음 | 제약, domain-rules.md |
| Q3=C | 점수+임계값, 사람 판단 | FR-4 |
| Q4=B | Instruction은 표시만 | FR-3.3 |
| Q5=A | 빈 턴 유지 | FR-3.4 |
| Q6=A | 로컬 웹 페이지 | FR-5 |
| Q7=C, 명확화2=A | 1건씩 완전 순차 | FR-2.4 |
| Q8=C | sonnet 판정 + fable 수정 | FR-3.1, FR-3.2, NFR-7.2 |
| Q9, 명확화1=A | 구독 계정 OAuth 재사용 | NFR-1.2, RK-1 |
| Q10=A | Python + Playwright | 제약 |
| Q11=B | 전용 Chrome 프로필, 직접 로그인 | FR-1.1, FR-1.2 |
| Q12=B, Q13=C | 확장 미적용 | 제약 |
| 도메인 규칙 | 아키타입 템플릿, R1~R3 | FR-3.1, domain-rules.md |
