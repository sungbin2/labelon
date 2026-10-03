# Cycle 2 Requirements Verification Questions - 프로젝트(데이터셋) 선택 기능

요청: "현재 라벨온 사이트에 다른 프로젝트들도 있는데 선택해서 프로젝트를 진행할수 있도록 해주세요."

`[Answer]:` 태그에 선택 문자를 적어 주세요. 권장안대로 하시려면 "모두 권장안"이라고 답하셔도 됩니다.

## Question 1
데이터셋(프로젝트) 선택은 어디에서 하나요?

A) 검토 화면 헤더의 드롭다운. 도구가 LabelOn 프로젝트 홈의 "진행중인 작업" 목록을 자동으로 읽어 채우고, 선택한 데이터셋으로 "다음 건 가져오기"가 동작 (권장. 설정 파일 수정 없이 사이트 상태를 그대로 반영)
B) config.yaml 에 데이터셋 목록을 직접 나열하고 화면에서 그중 선택
C) 실행 시 명령행 인자로 지정(화면 선택 없음)
D) Other (please describe after [Answer]: tag below)

[Answer]: A (사용자 답변: "모두 권장안")

## Question 2
데이터셋마다 페르소나가 다릅니다(어린이3, 어린이보호자3, 거동불편3, 시각장애3, 고령3, 시각장애2-1). 페르소나 기준은 무엇으로 할까요?

A) 초안의 instruction.persona 값을 그 건의 기준 페르소나로 사용. 설정 페르소나와의 비교(BR-02 일부)는 제거하고, 아키타입 템플릿 일치 검사와 CoT·대화의 페르소나 적합성 판정은 유지 (권장. 데이터셋 추가 시 설정 변경 불필요)
B) 데이터셋 이름의 괄호 안 문구(예: "어린이3" → 어린이)로 기대 페르소나를 추정해 초안과 비교, 다르면 경고
C) config.yaml 에 데이터셋 id별 기대 페르소나를 사용자가 직접 입력하고 비교
D) Other (please describe after [Answer]: tag below)

[Answer]: A (사용자 답변: "모두 권장안")

## Question 3
목록에 어떤 작업을 보여 줄까요?

A) 진행중 작업 중 UC-LE 타입(AH25)만 (권장. 이 도구는 UC-LE 화면 구조만 지원)
B) 진행중 작업 전부 표시하되 미지원 타입은 선택 불가로 표시
C) Other (please describe after [Answer]: tag below)

[Answer]: A (사용자 답변: "모두 권장안")

## Question 4
데이터셋 전환은 언제 허용할까요?

A) 검토 중인 건이 없을 때만(준비됨/완료/오류/만료 상태). 검토 대기 중이면 먼저 제출·불가·건너뛰기로 정리해야 전환 가능 (권장. 화면의 건과 선택 데이터셋이 어긋나지 않음)
B) 언제든 전환 가능. 검토 중인 건은 자동으로 반환(건너뛰기)
C) Other (please describe after [Answer]: tag below)

[Answer]: A (사용자 답변: "모두 권장안")

## Question 5
마지막 선택을 기억할까요?

A) 마지막으로 선택한 데이터셋을 로컬 상태 파일(data/ui-state.json)에 저장해 다음 실행 시 자동 선택. config.yaml 의 dataset_id 는 목록을 못 읽을 때의 기본값으로만 사용 (권장)
B) 저장하지 않고 실행할 때마다 선택
C) Other (please describe after [Answer]: tag below)

[Answer]: A (사용자 답변: "모두 권장안")

## Question 6
이력 화면에 데이터셋을 어떻게 반영할까요?

A) 목록에 데이터셋 이름 열 추가 + 헤더 요약에 데이터셋별 처리 건수 표시 (권장)
B) 목록에 데이터셋 이름 열만 추가
C) 변경 없음
D) Other (please describe after [Answer]: tag below)

[Answer]: A (사용자 답변: "모두 권장안")
