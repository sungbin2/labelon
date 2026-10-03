# Cycle 3 Requirements Verification Questions - 검수 가이드 반영

요청: "가이드 폴더 진행". 가이드 정리: `cycle3-guide-notes.md`.
`[Answer]:` 태그에 선택 문자를 적어 주세요. 권장안대로 하시려면 "모두 권장안"이라고 답하셔도 됩니다.

## Question 1
가이드(스크린샷 1)는 Archetype 이 잘못된 경우 Archetype 과 Task 를 고치라고 합니다. 현재 도구는 Instruction 을 모델이 수정하지 않고 경고만 합니다. 어떻게 할까요?

A) 모델이 QA·CoT 내용과 사진으로 판단해 올바른 아키타입을 제안하면, 도구가 해당 아키타입 템플릿에 페르소나를 넣어 Task 를 자동 생성하고 수정안에 반영. 사람이 diff 로 확인 후 승인 (권장. 템플릿 문구는 항상 정확하게 생성됨)
B) 경고와 제안 아키타입만 표시하고 Instruction 은 사람이 직접 편집(Instruction 필드를 편집 가능하게)
C) 현재대로 경고만
D) Other (please describe after [Answer]: tag below)

[Answer]: A (사용자 답변: "모두 권장안")

## Question 2
불가 후보 조건을 규칙으로 확장할까요? (가이드 B-2, C, D)

A) 점수 임계값에 더해 3가지를 불가 후보로 표시: (1) Task 방향과 QA 방향 불일치(모델 판정), (2) 가전조작 아키타입인데 조작부가 보이지 않음(모델 판정), (3) 수정량 과다 = 거짓 팩트 3개 이상 또는 불일치 필드 4개 이상(설정 가능). 각 사유를 불가 사유 제안에 넣음 (권장)
B) (1)(2)만 추가, 수정량 과다는 사람이 판단
C) 현재대로 점수만
D) Other (please describe after [Answer]: tag below)

[Answer]: A (사용자 답변: "모두 권장안")

## Question 3
QA 멀티턴 정리(가이드 E): CoT 3단계 범위를 벗어난 턴(사진에 없는 인물·상황 추론)을 어떻게 할까요?

A) 모델이 해당 턴을 삭제하고 앞 턴 답변에 합치는 수정안을 제안 허용. 턴 수 감소만 허용, 증가는 금지. 삭제된 턴은 diff 에 표시 (권장. 가이드 예시와 동일)
B) 턴 수 불변 유지, 문제 턴은 경고만
C) Other (please describe after [Answer]: tag below)

[Answer]: A (사용자 답변: "모두 권장안")

## Question 4
텍스트 정리 규칙(가이드 F)은 어떻게 반영할까요?

A) revise 프롬프트에 "문맥에 맞지 않는 단어 삭제, 전화번호 삭제, 어린이 데이터셋은 부드러운 말투" 규칙 추가 + 전화번호는 정규식으로 결정론 검사해 판정 화면에 경고·자동 삭제 제안 (권장)
B) 프롬프트 규칙만 추가
C) Other (please describe after [Answer]: tag below)

[Answer]: A (사용자 답변: "모두 권장안")

## Question 5
CoT 단계 정의(가이드 A: 1단계 장소·상황, 2단계 위험·주의점, 3단계 행동·답변 정리)와 "QA 는 CoT 3단계와 맞아야 함"을 판정 기준에 넣을까요?

A) judge 에 cot 단계별 역할 적합성과 QA↔CoT3 일치 판정 항목을 추가하고, 불일치는 수정 필요 조건에 포함 (권장)
B) 프롬프트 설명만 추가, 판정 항목은 그대로
C) Other (please describe after [Answer]: tag below)

[Answer]: A (사용자 답변: "모두 권장안")

## Question 6
가이드 PDF 가 DRM 형식으로 바뀌어 이미지 슬라이드(오류·불가 예시 12쪽)를 읽지 못했습니다. 어떻게 할까요?

A) 지금 확보한 자료(guide.md, 스크린샷 2장, PDF 텍스트 추출본)로 진행하고, 나중에 일반 PDF 나 스크린샷을 주시면 불가 예시를 추가 반영 (권장)
B) 일반 PDF 를 다시 넣을 때까지 이 사이클을 보류
C) Other (please describe after [Answer]: tag below)

[Answer]: A (사용자 답변: "모두 권장안")
