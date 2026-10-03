# Cycle 6 Requirements: QA 질문 편집 · 편집 반영 지연

작성일: 2026-10-01. 깊이: Minimal. 실행 계획(Workflow Planning) 포함.

## 1. Intent Analysis
| 항목 | 내용 |
|---|---|
| User Request | (1) 대화의 user 발화(QA 질문)도 화면에서 직접 수정 가능하게. (2) 직접 수정 시 반영이 너무 빨라 입력 중 편집이 끊김 → 반영 시간 조정 |
| Request Type | Enhancement + UX 결함 수정 (Brownfield) |
| Scope | domain(필드 주소), diff, services(검증), 설정, 프론트엔드(편집 UX) |
| Complexity | Low |

## 2. 현상 분석 (2)
- 화면은 입력 400ms 뒤 `PUT /draft` 를 보내고, 서버가 상태를 SSE 로 다시 보내면 초안 패널 전체를 다시 그린다(`innerHTML`). 편집 중 textarea 값·커서는 복원하지만 **DOM 교체 자체가 한글 IME 조합을 끊어** 글자가 깨지거나 입력이 사라진다
- 따라서 지연만 늘려서는 부족하고, **편집 중에는 초안 패널을 다시 그리지 않아야** 한다

## 3. 기능 요구사항
### FR-C6-1. user 발화 편집
- 필드 주소 `turn_N_user` 추가(get/set/editable_fields). diff 에 `turn_N_user` 포함. 화면에서 user 를 textarea 로 편집(라벨 "대화 N턴 user(질문)"), 변경 시 diff 표시
- 제출기는 이미 최종안의 user 로 question textarea 를 채우므로 변경 없음(검증 테스트 추가)
- 모델(revise)은 계속 user 를 바꾸지 않는다(BR-21 유지). 사람 편집만 허용
- 검증: assistant 가 있는데 user 가 비면 승인 차단 문구 추가

### FR-C6-2. 편집 반영 지연·입력 보호
- `config.yaml` `ui.edit_delay_ms`(기본 1500) 로 저장 지연 조정. `/config` 로 화면에 전달
- 한글 IME 조합 중(compositionstart~compositionend)에는 저장하지 않고, 조합이 끝나면 지연 후 저장. textarea 를 벗어나면(blur) 즉시 저장
- textarea 편집 중(focus)에는 SSE 갱신으로 초안 패널을 다시 그리지 않는다(마지막 상태만 보관). blur 또는 저장 완료 후 한 번 다시 그린다. 헤더·판정·경고 패널은 계속 갱신

## 4. 실행 계획 (Workflow Planning)
- Code Generation → Build and Test 만 실행. 설계 결정은 코드 생성 계획에 명시. 위험 Low(화면 로직, 데이터 모델은 필드 주소 추가뿐)

## 5. 인수 기준
- AC-C6-1 `PUT /draft {field: turn_1_user}` 가 최종안 user 를 바꾸고 diff 에 `turn_1_user` 변경이 표시된다. 제출 payload 의 `turn_1_user` 가 수정값이다
- AC-C6-2 `/config` 에 `edit_delay_ms` 가 있고 기본 1500
- AC-C6-3 (사용자 확인) 한글을 빠르게 입력해도 글자가 깨지지 않고, 입력을 멈추면 1.5초 뒤 "변경됨" 태그·diff 가 나타난다
- AC-C6-4 기존 114개 테스트 유지
