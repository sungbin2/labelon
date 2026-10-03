# Cycle 4 Requirements Verification Questions - 검수 가이드 이미지 슬라이드 반영

요청: "...VQA_검수가이드_0911.pdf 이 파일로 확인해주세요." 가이드 정리: `cycle4-guide-notes.md` (N1~N8).
`[Answer]:` 태그에 선택 문자를 적어 주세요. 권장안대로 하시려면 "모두 권장안"이라고 답하셔도 됩니다.

## Question 1
아키타입이 **이미지 환경과 맞지 않는** 경우(N8: 실외 도로에 실내탐색·일상지원·음식)를 어떻게 할까요? 사이클 3 은 아키타입 불일치를 정정(템플릿 치환)으로 처리합니다.

A) 두 경우를 구분: 모델이 "아키타입이 사진 환경과 양립 불가"라고 판정하면 **불가 후보**(가이드대로, 사유: "아키타입이 이미지 환경과 맞지 않음"). QA·Scene 은 사진과 맞는데 라벨만 틀린 경우(음식 → 쇼핑)만 지금처럼 정정 제안 (권장. 환경 충돌 건은 CoT·QA 를 전부 다시 써야 해 수정량 과다)
B) 현재대로 모두 정정 제안(사람이 화면에서 불가로 바꿀 수 있음)
C) 모든 아키타입 불일치를 불가 후보로(사이클 3 정정 기능은 끔)
D) Other (please describe after [Answer]: tag below)

[Answer]: A (사용자 답변: "모두 권장안")

## Question 2
불가 예시 1~4 의 새 불가 사유 3종을 어떻게 반영할까요? (N4·N6 핵심 팩트 오인식이 CoT·QA 전체로 전파, N5 페르소나가 할 수 없는 확인 요구(시각장애인에게 "보이면"), N7 위험 행위 권고(무단횡단))

A) 3종 모두 모델 판정 필드로 추가하고 true 이면 **불가 후보** + 사유 목록에 표시 (권장. 가이드가 명시적으로 불가로 분류)
B) 전파(N4·N6)·위험 권고(N7)는 불가 후보, 페르소나 부적합 안내(N5)는 문장만 고치면 되므로 **수정 대상**으로
C) 3종 모두 경고만 표시하고 사람이 불가 여부 판단
D) Other (please describe after [Answer]: tag below)

[Answer]: A (사용자 답변: "모두 권장안")

## Question 3
오탈자·맞춤법(N1), 주관적 추측 문장(N2), 숫자 표기(N3)는 어떻게 반영할까요?

A) judge 가 `text_issues` 목록({field, wrong, correct, kind: typo|speculation|number})을 출력하고 하나라도 있으면 수정 필요. revise 프롬프트에 "맞춤법 수정, 이미지의 숫자는 숫자 그대로, 추측 문장 삭제·사실로 교체" 규칙 추가. 화면 판정 패널에 목록 표시 (권장)
B) revise 프롬프트 규칙만 추가(판정 항목 없음 → 다른 문제가 없으면 오탈자만 있는 초안은 그대로 승인됨)
C) Other (please describe after [Answer]: tag below)

[Answer]: A (사용자 답변: "모두 권장안")

## Question 4
가이드 5~7쪽 "QA 는 단순 설명형이 아닌 상황 맥락·Facts·CoT 기반 페르소나 맞춤형 멀티턴" 과 "기존(연관) QA 목록이 이미지와 일치하는지 간단히 확인" 은 어떻게 할까요?

A) judge 프롬프트에 판정 기준 문구로만 추가(persona_task_fit·qa_matches_cot3 판단에 반영). 연관 QA 는 지금처럼 참고용이며 도구가 검수하지 않음 (권장. 연관 QA 는 제출 대상이 아님)
B) 연관 QA 목록도 모델이 사진과 대조해 불일치를 경고로 표시(호출당 토큰 증가)
C) Other (please describe after [Answer]: tag below)

[Answer]: A (사용자 답변: "모두 권장안")

