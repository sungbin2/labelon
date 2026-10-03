# Cycle 8 Requirements Verification Questions

`[Answer]:` 에 답해 주세요. Q1 은 원격 주소가 꼭 필요합니다(없으면 로컬 저장소까지만 만들고 push 는 보류).

## Question 1
어느 원격 저장소에 올릴까요? (private 권장. `gh` CLI 가 없어 저장소 생성은 사용자가 해야 합니다)

A) GitHub/GitLab 등에 **빈 private 저장소를 만들고 URL 을 알려 주시면** 제가 remote 로 등록하고 첫 push 까지 진행 (권장). 예: https://github.com/<계정>/labelon-reviewer.git
B) 로컬 git 저장소만 초기화하고 커밋. 원격 연결·push 는 나중에
C) Other (please describe after [Answer]: tag below)

[Answer]: A (https://github.com/sungbin2/labelon.git)

## Question 2
"각 항목은 삭제하지 말고 수정만"은 어떻게 반영할까요?

A) 모델의 대화 턴 삭제 기능을 끄고(설정 `allow_turn_drop: false` 기본), 사람 편집에서도 초안에 있던 항목을 빈 값으로 두면 승인 차단 (권장)
B) 모델 턴 삭제는 유지하고 사람 편집의 빈 값만 차단
C) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 3
자동 업데이트 방식은?

A) run.bat 시작 시 `git pull --ff-only` → 변경 있으면 패키지 재설치 → 실행. 실패해도 현재 버전으로 실행, `run.bat --no-update` 로 건너뛰기 (권장)
B) 별도 update.bat 을 두고 run.bat 은 실행만
C) Other (please describe after [Answer]: tag below)

[Answer]: A
