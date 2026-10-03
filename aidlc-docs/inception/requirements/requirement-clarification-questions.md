# Requirements Clarification Questions

답변을 검토한 결과 모호한 항목 1개와 확인이 필요한 조합 1개가 있습니다.

## Ambiguity 1: Q9 "AUTH 인증방식"
Q9(Anthropic API 키 관리)에 "AUTH 인증방식"이라고 답하셨습니다. 이 표현은 여러 방식을 뜻할 수 있어 구현이 달라집니다.

### Clarification Question 1
Claude 모델 호출에 사용할 인증 방식은 무엇인가요?

A) Claude 구독 계정 로그인(OAuth). Claude Code나 Claude Agent SDK가 사용하는 로그인 토큰을 재사용. 별도 API 키 발급 없음
B) Anthropic Console API 키. 환경변수 ANTHROPIC_API_KEY 또는 .env 파일로 주입
C) AWS Bedrock의 Claude. IAM 자격증명(프로파일, 환경변수)으로 인증
D) Google Vertex AI의 Claude. 서비스 계정 또는 gcloud 인증
E) Other (please describe after [Answer]: tag below)

[Answer]: A (사용자 채팅 답변: "Claude 구독 계정의 OAuth 로그인 토큰 재사용")

## Ambiguity 2: Q7(1건씩 대화형) 과 Q6(로컬 웹 페이지) 조합
Q7에서 "1건씩 분석·검토·제출을 반복하는 대화형 흐름"(C)을, Q6에서 "로컬 웹 페이지 검토 화면"(A)을 선택하셨습니다. 두 답변은 양립하지만 화면 흐름을 확정해야 합니다.

### Clarification Question 2
로컬 웹 페이지에서 1건씩 처리하는 흐름은 어떤 형태가 맞나요?

A) 페이지에 "다음 건 가져오기" 버튼. 누르면 LabelOn에서 1건을 열어 모델 분석 후 결과 표시. 승인/수정/불가 선택 시 제출하고 다음 건으로 이동 (완전 순차)
B) 현재 건을 사람이 검토하는 동안 백그라운드에서 다음 1건을 미리 분석해 대기 (대기 시간 단축, 동시에 최대 2건 할당)
C) Other (please describe after [Answer]: tag below)

[Answer]: A
