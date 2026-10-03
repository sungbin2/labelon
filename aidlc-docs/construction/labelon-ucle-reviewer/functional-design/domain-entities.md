# Domain Entities - labelon-ucle-reviewer

## 1. 엔티티 정의

### SourceItem (LabelOn 원천 데이터, 불변)
| 필드 | 타입 | 제약 | 원본 |
|---|---|---|---|
| job_id | int | 필수 | vqaCotList[0].id |
| dataset_id | int | 필수 | datasetId |
| dataset_name | str | | datasetName |
| file_id | int | 필수 | fileId |
| job_vqa_id | int | | jobVqaId |
| annotator_id | int | 필수(release에 사용) | annotatorId |
| image_url | str | https | ucleObj.image (스크립트 상수) 또는 img.ucle_source_image src |
| org_file_name | str | | orgFileName |
| file_name | str | 캐시 파일명 | fileName |
| category | str | | category |
| weather | str | | weather |
| detected_object | str | 쉼표 구분 | detectedObject |
| related_qa | list[RelatedQA{question, answer, id}] | | qaList |
| job_date | datetime | 할당 시각(마감 계산 기준) | jobDate |
| job_status | str | 예: AK01 | jobStatus |
| de_identification_status | str | 예: AY01 | deIdentificationStatus |

### Instruction
| 필드 | 타입 | 제약 |
|---|---|---|
| archetype | str | 6종 중 하나여야 정상 |
| persona | str | |
| task | str | |

### DialogueTurn / Dialogue
| 필드 | 타입 | 제약 |
|---|---|---|
| turn | int | 1~6 |
| user | str | 수정 불가 |
| assistant | str | 수정 가능 |
| Dialogue.context | dict{user_type, situation, priority} | 수정 불가 |
| Dialogue.turns | list[DialogueTurn] | 길이 = 초안 턴 수(보통 3), 최대 6 |

### Draft (초안·수정안·최종안의 공통 형태)
| 필드 | 타입 | 제약 |
|---|---|---|
| instruction | Instruction | |
| scene | str | 비어 있지 않음 |
| facts | list[str] | 정확히 5개 |
| cot1 | str | spatialContext |
| cot2 | str | stateAnalysis |
| cot3 | str | actionPlan |
| dialogue | Dialogue | |

### InstructionCheck (RuleChecker 결과)
| 필드 | 타입 |
|---|---|
| archetype_known | bool |
| task_matches_template | bool |
| persona_matches_config | bool |
| mismatch_details | list[str] (사람이 읽는 설명) |
| ok | bool (세 값 모두 True) |

### FactVerdict
| 필드 | 타입 | 제약 |
|---|---|---|
| index | int | 0~4 |
| verdict | enum TRUE / FALSE / UNKNOWN | |
| evidence | str | 한 문장 |

### FieldVerdict
| 필드 | 타입 |
|---|---|
| field | enum scene / cot1 / cot2 / cot3 / turn_1 ... turn_6 |
| consistent | bool |
| note | str |

### JudgeResult
| 필드 | 타입 | 산출 |
|---|---|---|
| instruction_check | InstructionCheck | RuleChecker |
| fact_verdicts | list[FactVerdict] (5) | 모델 |
| field_verdicts | list[FieldVerdict] | 모델 |
| persona_task_fit | {cot_fits: bool, dialogue_fits: bool, note: str} | 모델 (R1 의미 적합성) |
| missing_in_image | list[str] | 모델 |
| impossible_reason_suggestion | str | 모델 |
| consistency_score | int 0~100 | JudgeStage 산식 |
| impossible_candidate | bool | score <= threshold |
| needs_revision | bool | business-rules BR-04 |
| model_usage | ModelUsage | |
| raw | dict | 모델 원본 출력(이력용) |

### RevisedDraft
| 필드 | 타입 |
|---|---|
| draft | Draft (제약 강제 후) |
| change_notes | list[{field, reason}] |
| skipped | bool (수정 생략 여부) |
| model_usage | ModelUsage \| None |

### FinalDraft
Draft + `edited_by_user: bool` + `updated_at`

### SubmissionRecord
| 필드 | 타입 |
|---|---|
| kind | enum APPROVE / IMPOSSIBLE / SKIP |
| payload_snapshot | dict (입력한 값 또는 사유) |
| response_message | str (LabelOn 결과 모달 텍스트) |
| success | bool |
| submitted_at | datetime |
| error | str \| None |

### ModelUsage
| 필드 | 타입 |
|---|---|
| stage | enum judge / revise |
| model | str |
| input_tokens, output_tokens, cache_read_tokens | int |
| latency_ms | int |

### ReviewItem (상태 기계가 보유하는 현재 건)
| 필드 | 타입 |
|---|---|
| item_id | int (이력 DB PK) |
| state | enum READY / FETCHING / JUDGING / REVISING / REVIEW / SUBMITTING / DONE / ERROR / EXPIRED |
| source | SourceItem |
| draft | Draft (서버 초안) |
| judge | JudgeResult \| None |
| revised | RevisedDraft \| None |
| final | FinalDraft |
| diffs | list[FieldDiff] (draft vs final) |
| deadline | datetime = job_date + 60분 |
| warnings | list[str] (모델 오류 등) |
| submission | SubmissionRecord \| None |
| image_paths | {original, resized} |

## 2. 관계도

```
+-------------+ 1     1 +-------------+ 1     0..1 +--------------+                            
| SourceItem  |---------|   Draft     |------------| JudgeResult  |                            
| (원천)      |         | (서버 초안) |            |              |                                  
+------+------+         +------+------+            +------+-------+                            
       |                       |                          |                                    
       | 1                     | 1                        | 0..1                               
       |                       v                          v                                    
       |                +-------------+           +--------------+                             
       |                | FinalDraft  |<----------| RevisedDraft |                             
       |                | (사용자확정)|  초기값   |              |                                     
       |                +------+------+           +--------------+                             
       |                       |                                                               
       | 1               0..n  v                                                               
       +----------------> +-------------+      +-------------+                                 
                          | Submission  |      | ModelUsage  | (JudgeResult, RevisedDraft에 각 1)
                          | Record      |      +-------------+                                 
                          +-------------+                                                      
```

## 3. SQLite DDL

```sql
CREATE TABLE items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  job_id INTEGER NOT NULL,
  dataset_id INTEGER NOT NULL,
  file_id INTEGER NOT NULL,
  job_vqa_id INTEGER,
  annotator_id INTEGER,
  org_file_name TEXT, file_name TEXT, image_url TEXT,
  category TEXT, weather TEXT, detected_object TEXT,
  related_qa_json TEXT NOT NULL,
  job_date TEXT NOT NULL,          -- ISO8601 UTC
  fetched_at TEXT NOT NULL,
  state TEXT NOT NULL,             -- ReviewItem.state 최종값
  state_note TEXT,
  draft_json TEXT NOT NULL         -- 서버 초안 Draft
);
CREATE INDEX idx_items_job ON items(job_id, fetched_at);

CREATE TABLE judge_results (
  item_id INTEGER PRIMARY KEY REFERENCES items(id),
  created_at TEXT NOT NULL,
  result_json TEXT NOT NULL,       -- JudgeResult 전체(raw 포함)
  score INTEGER NOT NULL,
  impossible_candidate INTEGER NOT NULL,
  needs_revision INTEGER NOT NULL,
  instruction_ok INTEGER NOT NULL
);

CREATE TABLE revisions (
  item_id INTEGER PRIMARY KEY REFERENCES items(id),
  created_at TEXT NOT NULL,
  skipped INTEGER NOT NULL,
  revised_json TEXT NOT NULL,
  change_notes_json TEXT NOT NULL
);

CREATE TABLE final_drafts (
  item_id INTEGER PRIMARY KEY REFERENCES items(id),
  updated_at TEXT NOT NULL,
  edited_by_user INTEGER NOT NULL,
  final_json TEXT NOT NULL
);

CREATE TABLE submissions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  item_id INTEGER NOT NULL REFERENCES items(id),
  kind TEXT NOT NULL,              -- APPROVE / IMPOSSIBLE / SKIP
  payload_json TEXT NOT NULL,
  response_message TEXT,
  success INTEGER NOT NULL,
  error TEXT,
  submitted_at TEXT NOT NULL
);

CREATE TABLE model_usage (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  item_id INTEGER NOT NULL REFERENCES items(id),
  stage TEXT NOT NULL, model TEXT NOT NULL,
  input_tokens INTEGER, output_tokens INTEGER, cache_read_tokens INTEGER,
  latency_ms INTEGER, created_at TEXT NOT NULL
);
```

## 4. LabelOn 원본 ↔ 엔티티 매핑과 직렬화

| LabelOn 필드 | 형식 | 엔티티 | 역직렬화 | 직렬화(제출 시 textarea 값) |
|---|---|---|---|---|
| vqaCotResultList[0].instruction | JSON 문자열 `{"archetype","persona","task"}` | Instruction | json.loads. 실패 시 `'`→`"` 치환 후 재시도(React 코드와 동일) | 수정하지 않으므로 textarea에 쓰지 않음 |
| .scene | 문자열 | Draft.scene | 그대로 | textarea[3] |
| .facts | JSON 문자열 배열 | Draft.facts | json.loads → list[str]. 5개 미만이면 빈 문자열 패딩 후 경고 | textarea[4..8] 각 1개 |
| .cot1 / cot2 / cot3 | 문자열 | Draft.cot1..3 | 그대로 | textarea[9..11] |
| .finalAnswer | JSON 문자열 `{"context":{...},"dialogue":[{turn,user,assistant}]}` | Dialogue | json.loads. dialogue 배열 또는 단일 객체 허용(React 코드와 동일) | 턴 n: question textarea[n], answer textarea[n]. user 값은 원본 그대로 다시 채움 |
| vqaCotList[0].qaList | 배열 | related_qa | 그대로 | 제출 무관 |
| vqaCotList[0].jobDate | ISO | job_date | 서버는 `moment(...).utc()`로 표기하므로 문자열 값을 그대로 UTC로 해석하지 말고, 페이지 카운트다운 요소(제한시간 텍스트)를 1회 읽어 남은 초를 보정한다 | 제출 무관 |

- 화면 textarea 인덱스는 2026-09-23 관찰 기준(instruction 3개 → scene 1 → facts 5 → cot 3, 그다음 최종 답변 QA 6쌍은 별도 클래스 `ucle_final_question_input`, `ucle_final_answer_input`). Parser.field_locators가 클래스 기반으로 재확인하고, 개수가 다르면 PageStructureError.
- 페이지가 제출 시 React 상태에서 본문을 만들기 때문에 도구는 JSON 직렬화를 직접 하지 않는다. 이력 저장용 payload_snapshot에는 textarea에 입력한 값들을 기록한다.
