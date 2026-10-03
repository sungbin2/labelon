# Business Logic Model - labelon-ucle-reviewer

## 1. 판정 파이프라인 (JudgeStage.run)

```
입력: images(resized), item(SourceItem), draft(Draft), config
 1. ic = RuleChecker.check(draft.instruction, config)            # BR-01, BR-02
 2. raw, usage = ModelClient.judge(images.resized, item, draft, rules)
    - rules = {archetype 템플릿표, persona, R1~R3 요약, 출력 스키마}
    - 스키마 검증 실패 → 1회 재요청("스키마에 맞게 다시") → 실패 시 ModelCallError
 3. facts = raw.facts (길이 5 보정: 부족하면 UNKNOWN 채움)
 4. score = Score(facts, raw.scene, raw.cot, raw.dialogue_turns)   # BR-03
 5. impossible_candidate = score <= config.threshold               # BR-05
 6. needs_revision = not impossible_candidate and (
        any(f.verdict == FALSE) or any(not v.consistent for v in field_verdicts)
        or not raw.persona_task_fit.cot_fits or not raw.persona_task_fit.dialogue_fits)   # BR-04
 7. return JudgeResult(...)
```

### 1.1 judge 프롬프트 구조 (캐싱 친화: 고정부 → 가변부)
- **system(고정)**: 역할("이미지와 초안을 대조하는 검수자"), 판정 원칙(이미지에서 확인 가능한 것만 TRUE, 보이지 않으면 UNKNOWN, 이미지와 모순이면 FALSE), 방향 기준(이미지를 보는 사람 기준 좌우), R1~R3 요약, archetype 템플릿 6종, 출력 JSON 스키마 전문, 한국어 출력 지시
- **user(가변)**: [이미지 블록] + 텍스트: 데이터셋 페르소나, category/weather/detectedObject, 연관 QA 목록, 초안 전체(instruction, scene, facts 번호 붙여, cot1~3, dialogue 턴별)
- 가변부에 타임스탬프·ID를 넣지 않는다(캐시 무효화 방지)

### 1.2 judge 출력 스키마
```json
{
  "type": "object", "additionalProperties": false,
  "required": ["facts","scene","cot","dialogue_turns","persona_task_fit","missing_in_image","impossible_reason_suggestion"],
  "properties": {
    "facts": {"type":"array","minItems":5,"maxItems":5,"items":{"type":"object","additionalProperties":false,
      "required":["index","verdict","evidence"],
      "properties":{"index":{"type":"integer"},"verdict":{"enum":["TRUE","FALSE","UNKNOWN"]},"evidence":{"type":"string"}}}},
    "scene": {"type":"object","additionalProperties":false,"required":["consistent","note"],
      "properties":{"consistent":{"type":"boolean"},"note":{"type":"string"}}},
    "cot": {"type":"array","minItems":3,"maxItems":3,"items":{"type":"object","additionalProperties":false,
      "required":["field","consistent","note"],
      "properties":{"field":{"enum":["cot1","cot2","cot3"]},"consistent":{"type":"boolean"},"note":{"type":"string"}}}},
    "dialogue_turns": {"type":"array","items":{"type":"object","additionalProperties":false,
      "required":["turn","consistent","note"],
      "properties":{"turn":{"type":"integer"},"consistent":{"type":"boolean"},"note":{"type":"string"}}}},
    "persona_task_fit": {"type":"object","additionalProperties":false,"required":["cot_fits","dialogue_fits","note"],
      "properties":{"cot_fits":{"type":"boolean"},"dialogue_fits":{"type":"boolean"},"note":{"type":"string"}}},
    "missing_in_image": {"type":"array","items":{"type":"string"}},
    "impossible_reason_suggestion": {"type":"string"}
  }
}
```

## 2. 수정 파이프라인 (ReviseStage.run)

```
입력: images, item, draft, judge
 1. if not judge.needs_revision: return RevisedDraft(draft 복사, change_notes=[], skipped=True)
 2. raw, usage = ModelClient.revise(images.resized, item, draft, judge)
 3. proposed = Draft(instruction=draft.instruction,            # 불변
                     scene=raw.scene, facts=raw.facts, cot1..3=raw.cot*,
                     dialogue=Dialogue(context=draft.dialogue.context,   # 불변
                                       turns=[Turn(n, user=draft.turn[n].user, assistant=raw.assistant[n])]))
 4. proposed = enforce_constraints(draft, proposed)              # BR-06
 5. return RevisedDraft(proposed, raw.change_notes, skipped=False, usage)
```

### 2.1 revise 프롬프트 구조
- **system(고정)**: 역할("초안을 최소 수정하는 편집자"), 수정 원칙(BR-06 전문: 거짓 팩트는 틀린 부분만 고치기 우선, 불가능하면 이미지 기반 사실로 교체, facts 5개 유지, user 발화·instruction·context 불변, 문체 유지, 새 정보는 이미지에서 확인되는 것만), archetype 템플릿, 출력 스키마
- **user(가변)**: [이미지 블록] + 초안 전체 + 판정 결과(거짓 팩트 인덱스와 근거, 불일치 필드와 note, persona_task_fit note, missing_in_image) + 문체 참고(finalAnswer.context.priority 원문)

### 2.2 revise 출력 스키마
```json
{
  "type":"object","additionalProperties":false,
  "required":["scene","facts","cot1","cot2","cot3","dialogue_assistant","change_notes"],
  "properties":{
    "scene":{"type":"string"},
    "facts":{"type":"array","minItems":5,"maxItems":5,"items":{"type":"string"}},
    "cot1":{"type":"string"},"cot2":{"type":"string"},"cot3":{"type":"string"},
    "dialogue_assistant":{"type":"array","items":{"type":"object","additionalProperties":false,
      "required":["turn","assistant"],"properties":{"turn":{"type":"integer"},"assistant":{"type":"string"}}}},
    "change_notes":{"type":"array","items":{"type":"object","additionalProperties":false,
      "required":["field","reason"],"properties":{"field":{"type":"string"},"reason":{"type":"string"}}}}
  }
}
```

### 2.3 enforce_constraints(original, proposed)
1. instruction := original.instruction
2. dialogue.context := original.dialogue.context
3. 턴 수 := original 턴 수. proposed에 없는 턴은 original assistant 유지, 초과 턴은 버림
4. 각 턴 user := original user
5. facts 길이 != 5 → 부족분은 original 같은 인덱스로 채움, 초과분 버림. change_notes에 "constraint" 기록
6. 빈 문자열 필드는 original 값으로 복원

## 3. RuleChecker.check (R1 결정론)

```
normalize(s) = 공백 제거
template = config.archetype_templates.get(instruction.archetype)
archetype_known = template is not None
persona_matches_config = normalize(instruction.persona) == normalize(config.persona)
if archetype_known:
    body = template.replace("(Persona)", "")                     # 페르소나 뒤 본문
    expected_pattern = "^" + re.escape(normalize(instruction.persona)) + "(가|이|은|는|을|를)?" + re.escape(normalize(body)) + "$"
    task_matches_template = re.fullmatch(expected_pattern, normalize(instruction.task)) is not None
else:
    task_matches_template = False
mismatch_details: 어떤 항목이 왜 다른지 한 줄씩(예: "task가 '음식' 템플릿과 다름: ...")
```
페르소나 자체가 config와 달라도 task 비교는 instruction.persona 기준으로 수행한다(두 문제를 분리해 표시).

## 4. 점수 산식 (Score)

| 구성 | 배점 | 계산 |
|---|---|---|
| Facts | 60 | 팩트당 12점. TRUE 12, UNKNOWN 6, FALSE 0 |
| Scene | 20 | consistent이면 20, 아니면 0 |
| CoT·대화 | 20 | 대상 필드 = cot1, cot2, cot3 + 초안에 존재하는 턴(assistant 비어 있지 않은 턴). 20 × (consistent 필드 수 / 대상 필드 수), 반올림 |

score = 정수 반올림. impossible_candidate = score <= threshold(기본 40).

예: 팩트 3 TRUE, 1 UNKNOWN, 1 FALSE = 42. Scene 일치 20. CoT 3 + 턴 3 중 5 일치 = 16.7 → 17. 합 79.

## 5. 상태 기계 전이표

| 현재 상태 \ 이벤트 | FETCH_STARTED | PARSED | JUDGED | REVISED | REVIEW_READY | EDITED / REVERTED | SUBMIT_STARTED | SUBMITTED | SUBMIT_FAILED | RELEASED | EXPIRED | FAILED | RESET |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| READY | FETCHING | | | | | | | | | | | | READY |
| FETCHING | | JUDGING | | | REVIEW(모델 생략) | | | | | | | ERROR | |
| JUDGING | | | REVISING 또는 REVIEW | | REVIEW | | | | | | EXPIRED | ERROR | |
| REVISING | | | | REVIEW | REVIEW | | | | | | EXPIRED | ERROR | |
| REVIEW | | | | | | REVIEW | SUBMITTING | | | | EXPIRED | | |
| SUBMITTING | | | | | | | | DONE / READY(SKIP) | REVIEW | READY | EXPIRED | | |
| DONE | FETCHING | | | | | | | | | | | | READY |
| ERROR | | | | | | | | | | | | | READY |
| EXPIRED | | | | | | | | | | | | | READY |

- 빈 칸은 IllegalTransition. JUDGED에서 needs_revision이면 REVISING, 아니면 REVIEW로 바로 간다.
- DONE에서 FETCH_STARTED를 허용해 "다음 건 가져오기"가 한 클릭으로 이어진다.
- 상태 변화마다 구독자에게 ReviewItem 스냅샷을 전달한다.

## 6. 제출 절차 (Submitter.approve)

```
전제: page가 같은 job_id의 작업 화면임을 확인(parse된 id와 스크립트의 id 비교). 다르면 SubmitError("page changed")
 1. locators = Parser.field_locators(); 개수 검증(scene 1, facts 5, cot 3, QA 12, radio 2, submit 1)
 2. 각 필드에 대해: locator.fill(value)          # Playwright fill은 input 이벤트를 발생시켜 React 상태를 갱신
    - fill 후 locator.input_value() == value 확인, 불일치면 1회 재시도, 재실패 시 SubmitError
    - 대화 턴: 초안 턴 수만큼 question(user 원본)과 answer(final assistant) 채움. 비어 있는 턴은 건드리지 않음
    - instruction 3개는 건드리지 않음
 3. "가능" 라디오 check
 4. 제출 버튼 click
 5. 확인 모달 대기(텍스트 "해당 작업 내용을 제출하시겠습니까") → "확인" 버튼 click. 10초 내 미표시면 SubmitError
 6. 결과 모달 대기(ModalAlert) → 텍스트 읽기 → "확인" click
    - "저장되었습니다" 포함 → success=True
    - 그 외 텍스트 → success=False, response_message=텍스트
 7. 페이지 이동 대기(URL 동일 재로딩) 최대 15초. 실패해도 success 판정은 6단계 기준
 8. return SubmissionRecord(APPROVE, payload_snapshot={입력값들}, ...)
```

### 6.1 불가 제출 (Submitter.impossible)
1. "불가" 라디오 check → 사유 입력란(placeholder "작업 불가 사유를 입력하세요" 또는 라디오 아래 textarea) 대기
2. 사유 fill → 제출 click → 확인 모달(텍스트에 "[작업불가]" 포함) → 확인 → 결과 모달 → 기록
3. 본문 필드는 건드리지 않음

### 6.2 반환 (Submitter.release)
- 페이지 컨텍스트에서 페이지 자체가 만료 시 사용하는 jQuery 호출을 그대로 수행한다(CSRF 프리필터 재사용):
  `$.ajax({url:"/job/ucle/annotator/resetData", type:"post", contentType:"application/json", data: JSON.stringify({datasetId, id, fileId, annotatorId})})`
- 응답 성공 시 SubmissionRecord(SKIP, success=True). 이후 페이지를 프로젝트 홈으로 이동시켜 타이머를 정지.

## 7. Diff 알고리즘 (DiffService)

1. 문장 분할: 정규식 `(?<=[.!?。])\s+|\n+` 로 분할, 양끝 공백 제거, 빈 문장 제거
2. 필드별 처리:
   - scene, cot1~3, 각 assistant: 문장 리스트 간 difflib.SequenceMatcher(autojunk=False) → opcodes를 EQUAL/INSERT/DELETE/REPLACE 세그먼트로 변환
   - facts: 인덱스별 1:1 비교. 동일이면 EQUAL, 다르면 REPLACE(문장 내부 글자 diff는 프론트에서 선택적으로 표시)
3. 출력 FieldDiff{field, changed: bool, segments[{op, base_text, other_text}]}
4. 초안 vs 최종안을 항상 기준으로 계산(수정안 vs 최종안은 계산하지 않음)

## 8. 가져오기 서비스 시간 예산

| 단계 | 목표 |
|---|---|
| 페이지 열기·파싱 | 5초 |
| 이미지 다운로드·축소 | 5초 |
| judge | 30~45초 |
| revise | 30~60초 |
| 합계 | 90초 목표, 180초 초과 시 UI 경고 |
