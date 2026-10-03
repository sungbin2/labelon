# Frontend Components - labelon-ucle-reviewer

단일 index.html + 순수 JavaScript(ES 모듈) + CSS. 빌드 없음. 한국어 UI.

## 1. 레이아웃 (3열)

```
+--------------------------------------------------------------------------------------------------+
| [검토] [이력]      상태: 검토 대기   파일: 20210211_084503.jpg   남은시간 48:12   토큰 누적 1.2M  |                   
+------------------------------+------------------------------------+----------------------------+  
| 이미지 (클릭 확대, 휠 줌)     | Instruction (읽기전용)  [경고배지]  | 정합성 점수   79 / 100     |                      
|                              |  archetype / persona / task        |  [불가 후보 아님]          |        
|                              +------------------------------------+----------------------------+  
|                              | Scene                    [변경됨]   | Facts 판정                 |      
|                              |  - 초안 문장 (삭제표시)             |  1 TRUE  근거...           |           
|                              |  + 수정 문장 (추가표시)             |  2 FALSE 근거...           |           
|                              |  [textarea 편집]                   |  3 TRUE                    |    
+------------------------------+------------------------------------+  4 UNKNOWN                 |  
| 메타                         | Facts 1~5 (각각 diff + textarea)   |  5 TRUE                    |      
|  category 음식  weather 그외 |                                    +----------------------------+      
|  detected 병,식탁            +------------------------------------+ 필드 정합                   |        
+------------------------------+ CoT 1~3 (diff + textarea)          |  scene O  cot1 O  cot2 X   |  
| 연관 QA                      +------------------------------------+  turn1 O turn2 O turn3 X   |    
|  Q ... / A ...               | 대화 턴 1~6                        +----------------------------+     
|  ...                         |  user (읽기전용)                    | 경고                        |      
|                              |  assistant (diff + textarea)       |  - Instruction 템플릿 불일치 |      
|                              |  (4~6 비어 있음 표시)               |  - 모델 오류: ...           |          
+------------------------------+------------------------------------+----------------------------+  
| [다음 건 가져오기 Alt+N]  [초안으로 되돌리기 Alt+R]  [건너뛰기 Alt+S]  [불가 제출 Alt+X]  [승인·제출 Alt+A] |                
+--------------------------------------------------------------------------------------------------+
```

## 2. 컴포넌트 계층 (JS 모듈)

```
app.js (루트)
 +- store.js            상태 저장소: reviewItem, uiState(tab, busy, toast), config
 +- sse.js              /events 구독 → store 갱신, 끊기면 3초 후 재연결
 +- api.js              fetch 래퍼 (POST /actions/*, PUT /draft, GET /history*)
 +- components/
     +- headerBar.js     탭, 상태 배지, 파일명, 카운트다운, 토큰 누적
     +- imagePanel.js    이미지 표시, 클릭 확대 모달, 휠 줌·드래그
     +- metaPanel.js     category/weather/detected_object, 연관 QA 목록
     +- instructionPanel.js  읽기전용 3필드 + InstructionCheck 경고 배지·상세
     +- draftField.js    (재사용) 필드 1개: 라벨, diff 렌더, textarea, 변경 배지
     +- draftPanel.js    scene, facts x5, cot x3, dialogue 턴 x6 을 draftField로 구성
     +- judgePanel.js    점수 게이지, 불가 후보 배너, 팩트 판정 리스트, 필드 정합 표, missing_in_image
     +- warningsPanel.js warnings, mismatch_details
     +- actionBar.js     버튼 5개 + 단축키 + 확인 다이얼로그(불가 사유 입력, 건너뛰기 확인)
     +- historyTab.js    요약 카드 + 목록 + 상세 드로어
     +- toast.js         결과·오류 알림
```

## 3. 컴포넌트별 상태와 입력

| 컴포넌트 | 입력(store에서) | 로컬 상태 | 출력(동작) |
|---|---|---|---|
| headerBar | item.state, source.org_file_name, deadline, summary.tokens | 1초 타이머 | 탭 전환 |
| imagePanel | image url(/images/{item_id}) | zoom, pan, modalOpen | 없음 |
| metaPanel | source | 없음 | 없음 |
| instructionPanel | draft.instruction, judge.instruction_check | 상세 펼침 | 없음 |
| draftField | field name, base(초안) 값, final 값, diff 세그먼트, readOnly | textarea 값(debounce 400ms) | onChange(field, value) → PUT /draft |
| draftPanel | draft, final, diffs | 없음 | draftField 이벤트 전달 |
| judgePanel | judge, config.threshold | 없음 | 팩트 클릭 시 해당 draftField로 스크롤 |
| warningsPanel | item.warnings, judge.instruction_check.mismatch_details | 없음 | 없음 |
| actionBar | item.state, remaining, final 유효성 | 다이얼로그 열림, 사유 텍스트 | POST /actions/fetch, approve, impossible, skip, revert |
| historyTab | /history, /history/summary, /history/{id} | 선택 id | GET 호출 |

## 4. 상태별 버튼 활성화

| 상태 | 가져오기 | 되돌리기 | 건너뛰기 | 불가 제출 | 승인·제출 | 편집 |
|---|---|---|---|---|---|---|
| (로그인 대기) | X | X | X | X | X | X |
| READY / DONE | O | X | X | X | X | X |
| FETCHING / JUDGING / REVISING | X (진행 표시) | X | X | X | X | X |
| REVIEW | X | O(편집·수정 있을 때) | O | O | O(유효성 통과 시) | O |
| SUBMITTING | X | X | X | X | X | X |
| ERROR | O(재시도 의미) | X | X | X | X | X |
| EXPIRED | O | X | X | X | X | X |

단축키: Alt+N 가져오기, Alt+A 승인, Alt+X 불가, Alt+S 건너뛰기, Alt+R 되돌리기. textarea 포커스 중에도 Alt 조합은 동작. 승인·불가·건너뛰기는 항상 확인 다이얼로그를 거친다.

## 5. 편집·diff 흐름

1. draftField textarea 입력 → 400ms debounce → `PUT /draft {field, value}` (턴은 `turn_n_assistant`)
2. 서버가 FinalDraft 갱신 + diff 재계산 → SSE로 ReviewItem 스냅샷 푸시
3. store 갱신 → draftField는 diff만 다시 그리고, 포커스 중인 textarea 값은 덮어쓰지 않음(로컬 우선)
4. 되돌리기 → 확인 → `POST /actions/revert` → 스냅샷으로 전체 재렌더
5. diff 표시: EQUAL 일반, DELETE 빨간 취소선(초안 문장), INSERT 초록 밑줄(최종 문장), REPLACE는 DELETE+INSERT 쌍. 변경 필드 라벨에 "변경됨" 배지
6. 승인 유효성(BR-33)은 프론트에서 먼저 검사해 버튼 비활성·툴팁, 서버에서 재검사

## 6. 카운트다운

- 스냅샷의 `deadline`(ISO)과 `server_now`를 받아 클라이언트 시계 오차를 보정한 뒤 1초 갱신
- 10분 미만: 헤더 배지 경고색 + "남은 시간 10분 미만" 토스트 1회
- 0: "제한시간 만료" 표시. 서버가 EXPIRED를 푸시하면 버튼 상태 갱신

## 7. API 연동표

| 컴포넌트 | 메서드 | 엔드포인트 | 시점 |
|---|---|---|---|
| app | GET | /state, /config | 초기 로드 |
| sse | GET(SSE) | /events | 상시 |
| actionBar | POST | /actions/fetch | 가져오기 |
| actionBar | POST | /actions/approve | 승인 확인 후 |
| actionBar | POST | /actions/impossible {reason} | 사유 입력 후 |
| actionBar | POST | /actions/skip | 건너뛰기 확인 후 |
| actionBar | POST | /actions/revert | 되돌리기 확인 후 |
| draftField | PUT | /draft {field, value} | 편집 debounce |
| imagePanel | GET | /images/{item_id} | 렌더 |
| historyTab | GET | /history, /history/summary, /history/{id} | 탭 열기·선택 |

## 8. 이력 탭

```
+--------------------------------------------------------------------------------------------------+
| 요약: 오늘 12건 (제출 9, 불가 2, 건너뜀 1)  누적 340건  토큰 누적 입력 2.1M / 출력 0.4M          |                       
+----------------------------------------------+---------------------------------------------------+
| 목록 (최근 50)                                | 상세                                              |     
|  시각      파일명           결과   점수       |  이미지(있으면) / 초안 / 판정 / 수정안 / 최종 /   |                       
|  10:41  20210211_0845.jpg  제출    79        |  제출 payload / LabelOn 응답 / 토큰                |       
|  10:33  20210211_0912.jpg  불가    22        |                                                   |  
|  ...                                         |                                                   |
+----------------------------------------------+---------------------------------------------------+
```

- 미완료 건(find_unfinished)은 목록 상단에 "미완료(만료 예정)" 배지로 표시(US-7 AC5)
- 상세는 탭 4개(판정, 수정안 diff, 최종·제출, 원본)로 나눠 표시
