# Cycle 2 Requirements: 프로젝트(데이터셋) 선택 기능

작성일: 2026-09-28. 깊이: Standard. 기반: 사이클 1 requirements.md, reverse-engineering/*.md

## 1. Intent Analysis
| 항목 | 내용 |
|---|---|
| User Request | LabelOn 에 진행중인 여러 프로젝트(데이터셋)가 있으므로 도구에서 선택해 작업할 수 있게 한다 |
| Request Type | Enhancement (Brownfield) |
| Scope Estimate | Multiple Components: 설정, 파서, 브라우저, 규칙 검사, 서비스, 웹 API, 프론트엔드, 이력 |
| Complexity Estimate | Simple~Moderate |
| Request Clarity | Clear (질문 6개 확정) |

## 2. 기능 요구사항

### FR-C2-1. 진행중 데이터셋 목록 조회
- LabelOn `/project/home` HTML 을 요청 API(쿠키 공유, 페이지 이동 없음)로 받아 "진행중인 작업" 카드의 `jobPage('annotator', '<type>','<id>')` 앵커와 카드 텍스트에서 (id, type, 프로젝트명, 데이터셋명, 크레딧, 등급)을 추출한다
- UC-LE 타입(`AH25`)만 목록에 포함한다. 다른 타입은 로그에만 남긴다
- 목록은 앱 시작 시(로그인 확인 후)와 사용자가 "새로고침"을 누를 때 갱신한다. 실패하면 마지막 성공 목록 또는 config 기본값 1개를 표시하고 경고한다
- 파싱 실패(구조 변경)는 PageStructureError 로 표시한다

### FR-C2-2. 데이터셋 선택
- 검토 화면 헤더에 데이터셋 드롭다운과 새로고침 버튼을 둔다
- 선택은 READY/DONE/ERROR/EXPIRED 상태에서만 허용한다. FETCHING~SUBMITTING 상태에서는 드롭다운을 비활성화하고 서버도 409 로 거부한다
- 선택된 데이터셋 id 가 `POST /actions/fetch` 의 대상이 된다(설정 `dataset_id` 대신)
- 선택값은 `data/ui-state.json` 에 저장하고 시작 시 복원한다. 저장값이 목록에 없으면 목록의 첫 항목(또는 config.dataset_id 가 목록에 있으면 그것)을 선택한다

### FR-C2-3. 페르소나 기준 변경
- 규칙 검사(BR-02)에서 `config.persona` 비교를 제거한다. `InstructionCheck.persona_matches_config` 는 항상 True 로 두거나 필드를 제거한다
- 아키타입 템플릿 일치 검사는 `instruction.persona` 를 치환 값으로 유지한다(변경 없음)
- 프롬프트의 "데이터셋 페르소나"는 `instruction.persona` 를 사용한다
- `config.persona` 는 삭제하지 않고 선택(optional)으로 두어 하위 호환한다(값이 있어도 비교에 쓰지 않음)

### FR-C2-4. 화면·이력 반영
- 헤더에 현재 선택 데이터셋 이름 표시. 검토 중인 건의 데이터셋(SourceItem.dataset_name)이 선택값과 다르면 배지로 표시
- 이력 목록에 데이터셋 이름 열 추가, 요약에 데이터셋별 처리 건수(제출·불가·건너뜀) 표시
- `GET /state` 스냅샷에 `datasets`(목록)와 `selected_dataset_id` 포함, `GET /config` 에 기본 dataset_id 유지

### FR-C2-5. API
| Method | Path | 동작 |
|---|---|---|
| GET | /datasets | 캐시된 목록 + 선택값 |
| POST | /datasets/refresh | LabelOn 에서 목록 재조회 |
| PUT | /datasets/selected {dataset_id} | 선택 변경(상태 검증, 저장) |

## 3. 비기능 요구사항
- 목록 조회는 페이지 이동 없이 요청 API 로 수행해 사용자의 Chrome 화면을 방해하지 않는다
- 목록 파싱 로직은 `labelon/parser.py` 에 두어 LabelOn 구조 지식 격리 원칙을 유지한다
- 기존 테스트 74개 유지 + 목록 파싱·선택 API·상태 검증 테스트 추가
- 설정 파일 하위 호환: 기존 config.yaml 그대로 동작(dataset_id 는 기본값·폴백)

## 4. 제약·가정
- 진행중 작업 카드 구조는 2026-09-28 관찰 기준. 픽스처 HTML 을 만들어 회귀 테스트한다
- 데이터셋마다 작업 화면 구조(UC-LE)가 같다고 가정한다. 다르면 기존 "화면 구조가 예상과 다릅니다" 오류로 드러난다

## 5. 인수 기준
- AC-C2-1 로그인 후 헤더 드롭다운에 진행중 UC-LE 데이터셋 6개가 이름과 함께 표시된다
- AC-C2-2 다른 데이터셋을 선택하고 가져오기를 누르면 그 데이터셋의 작업 화면이 열리고 헤더에 이름이 표시된다
- AC-C2-3 검토 대기 중에는 드롭다운이 비활성이고 PUT /datasets/selected 가 409 를 반환한다
- AC-C2-4 재시작 후 마지막 선택이 복원된다
- AC-C2-5 페르소나가 다른 데이터셋(예: 시각장애3)의 건에서 Instruction 경고가 페르소나 때문에 뜨지 않는다
- AC-C2-6 이력 목록에 데이터셋 이름이 보이고 요약에 데이터셋별 건수가 나온다

## 6. 추적
| 답변 | 반영 |
|---|---|
| Q1=A | FR-C2-1, FR-C2-2, FR-C2-5 |
| Q2=A | FR-C2-3, AC-C2-5 |
| Q3=A | FR-C2-1 |
| Q4=A | FR-C2-2, AC-C2-3 |
| Q5=A | FR-C2-2, AC-C2-4 |
| Q6=A | FR-C2-4, AC-C2-6 |
