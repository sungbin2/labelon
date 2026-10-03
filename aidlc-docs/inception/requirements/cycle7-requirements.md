# Cycle 7 Requirements: Instruction 편집 · 건수 집계 · 재로그인 복구 · 다시 판독

작성일: 2026-10-02. 깊이: Minimal. 실행 계획 포함(Code Generation → Build and Test).

## 1. Intent Analysis
| 항목 | 내용 |
|---|---|
| User Request | (1) 아키타입·페르소나·태스크 편집 (2) 건수는 제출마다 갱신, 불가는 제외 (3) 만료·세션 로그아웃 후 재로그인해도 버튼이 안 눌림 (4) 건너뛰기 → 다시 판독 |
| Request Type | Enhancement 2건 + 결함 2건 (Brownfield) |
| Scope | domain(필드 주소), services(세션 감시·재판독), state(전이), history(집계), web/app.py(SSE 집계), 프론트엔드 |
| Complexity | Moderate |

## 2. 원인 분석
- **(2) 건수 미갱신**: 상태 전이 때 보내는 SSE 페이로드에 집계(summary)가 빠져 있어(`on_state` 가 summary=None) 헤더가 마지막으로 받은 값을 유지한다. `/state` 와 SSE 최초 1회만 집계를 포함
- **(3) 버튼 비활성**: 가져오기 중 로그인 페이지를 만나면 `login_required=True` 로 두고 ERROR 로 가는데, 이 플래그를 다시 끄는 코드는 **시작 시 ensure_login 뿐**이다. 사용자가 Chrome 에서 재로그인해도 플래그가 남아 "다음 건 가져오기"(사용자가 말한 재시작 버튼)와 데이터셋 선택이 계속 비활성이다

## 3. 기능 요구사항
### FR-C7-1. Instruction 편집
- 최종안의 archetype / persona / task 를 화면에서 편집: archetype 은 6종 선택(select, 현재 값이 6종 밖이면 그 값도 항목에 포함), persona 입력칸, task textarea
- "템플릿으로 Task 채우기" 버튼: 선택한 archetype 템플릿에 persona + 조사(받침 → 이, 없음 → 가)를 넣어 task 를 채움. 템플릿은 `/config` 의 `archetype_templates` 로 전달
- 필드 주소 `archetype`/`persona`/`task` 를 `set_field` 에 추가(get 은 이미 있음). diff 에 `persona` 추가. 승인 전 검증: 세 값이 비면 차단
- 제출은 이미 최종안 Instruction 으로 textarea 3개를 채운다(변경 없음). 되돌리기는 Instruction 도 원복(이미 전체 원복)
- 아키타입 자동 정정(사이클 3)과 공존: 정정안 위에 사람이 다시 고칠 수 있음

### FR-C7-2. 건수 집계
- 오늘/누적 = **승인 제출(APPROVE) 완료 건만**. 불가·건너뜀은 보조 문구로만 표시
- 상태 전이 SSE 페이로드에 집계 포함 → 제출 완료 즉시 헤더·이력 숫자 갱신

### FR-C7-3. 재로그인 복구
- `login_required` 가 켜지면 백그라운드 로그인 감시를 시작: 5초 간격으로 `is_logged_in()` 확인, 로그인되면 플래그 해제 + 데이터셋 목록 갱신 + 경고 "로그인이 확인되었습니다"
- "다음 건 가져오기" 는 login_required 여도 누를 수 있게 하고(서버가 로그인 페이지를 만나면 안내), EXPIRED/ERROR 에서도 가능(기존)
- 감시는 중복 시작하지 않고, 서버 종료 시 함께 종료

### FR-C7-4. 다시 판독
- 액션바의 "건너뛰기(Alt+S)" 를 **"다시 판독(Alt+S)"** 으로 교체. REVIEW 상태에서 현재 건의 사진·서버 초안으로 판정→수정을 다시 실행(같은 item_id·마감 유지, 모델 호출 2회 추가). 완료 후 최종안·diff 가 새 결과로 바뀜(사람 편집은 사라지므로 확인 다이얼로그)
- 상태 전이 `REVIEW --REANALYZE--> JUDGING` 추가. 진행 중에는 편집·제출 불가(기존 BUSY 처리)
- LabelOn 반환(건너뛰기)은 보조 버튼 "반환" 으로 남긴다(API `/actions/skip` 유지, 단축키 없음)

## 4. 인수 기준
- AC-C7-1 `PUT /draft {field: task}` 가 최종안 task 를 바꾸고 diff 에 표시된다. archetype/persona/task 가 비면 승인 차단
- AC-C7-2 승인 1건 후 SSE 페이로드의 summary.total_items 가 1 증가하고, 불가 1건은 total_items 를 바꾸지 않는다
- AC-C7-3 가져오기에서 LOGIN 을 만나 login_required=True 가 된 뒤 브라우저가 로그인 상태가 되면 5초 내 login_required=False 로 돌아온다
- AC-C7-4 REVIEW 에서 `/actions/reanalyze` → JUDGING → REVIEW 로 돌아오고 item_id 가 같다. READY 에서는 409
- AC-C7-5 기존 115개 테스트 유지
