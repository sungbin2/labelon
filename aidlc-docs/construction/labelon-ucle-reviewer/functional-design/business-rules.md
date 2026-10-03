# Business Rules - labelon-ucle-reviewer

## A. 검토 규칙 (domain-rules R1~R3 상세)

| ID | 규칙 | 판정 주체 |
|---|---|---|
| BR-01 | archetype은 6종(일상지원, 보행안전, 쇼핑, 음식, 실내탐색, 가전조작) 중 하나여야 한다. 아니면 InstructionCheck.archetype_known=False | RuleChecker |
| BR-02 | task는 archetype 템플릿의 `(Persona)`를 instruction.persona로 치환한 문장과 일치해야 한다. 허용 오차: 공백 차이, 페르소나 직후 조사(가/이/은/는/을/를) 유무. persona 는 초안 값을 기준으로 하며 설정과 비교하지 않는다(사이클 2 개정 2026-09-28: 데이터셋마다 페르소나가 다름). 불일치는 경고로만 표시하고 값은 바꾸지 않는다 | RuleChecker |
| BR-03 | 팩트 판정: 이미지에서 확인되면 TRUE, 이미지와 모순되면 FALSE, 이미지로 확인할 수 없으면(가려짐, 화각 밖) UNKNOWN. 방향은 이미지를 보는 사람 기준 | 모델(judge) |
| BR-04 | 수정 필요(needs_revision) = 불가 후보가 아니고, (FALSE 팩트 ≥ 1 또는 불일치 필드 ≥ 1 또는 persona_task_fit 중 하나가 False) | JudgeStage |
| BR-05 | 불가 후보 = consistency_score ≤ threshold(기본 40) OR Task·QA 방향 불일치(아키타입 정정 불가 시) OR 가전조작+조작부 미가시 OR 거짓 팩트 ≥ impossible_rules.max_false_facts OR 불일치 필드 ≥ max_inconsistent_fields OR 아키타입-이미지 환경 충돌(archetype_fits_environment=false, 이때 아키타입 정정 미적용) OR 핵심 오인식 전파 OR 페르소나 불가 안내 OR 위험 행위 권고 (사이클 3·4 개정 2026-09-28, 검수 가이드. 사이클 5 2026-09-30: 일상지원은 실외에서도 환경 충돌 아님, 가전조작 조작부는 가구 포함). 불가 후보는 2단계 수정을 생략하고 사람이 결정한다 | JudgeStage |

## B. 점수 규칙

| ID | 규칙 |
|---|---|
| BR-10 | Facts 60점: 초안 Facts 개수 n 에 균등 배분(팩트당 60/n). TRUE 100% / UNKNOWN 50% / FALSE 0 (2026-09-23 운영 중 개정: n 은 5~6개 등 가변) |
| BR-11 | Scene 20점: consistent 20 / 아니면 0 |
| BR-12 | CoT·대화 20점: 대상 필드(cot1~3 + assistant가 비어 있지 않은 턴) 중 consistent 비율 × 20, 정수 반올림 |
| BR-13 | 모델 판정 누락 필드는 UNKNOWN(팩트) 또는 consistent=False(필드)로 채우고 warnings에 기록 |

## C. 수정 제약 규칙 (ReviseStage.enforce_constraints)

| ID | 규칙 |
|---|---|
| BR-20 | instruction 은 모델이 자유 서술로 바꾸지 않는다. 단 판정의 아키타입 제안이 유효하면 도구가 템플릿 치환으로 archetype·task 를 정정한다(persona 불변, 사이클 3). 사람이 되돌릴 수 있다 |
| BR-21 | dialogue.context(user_type, situation, priority)는 변경하지 않는다. user 발화는 모델이 바꾸지 않지만 사람은 화면에서 편집할 수 있다(사이클 6, 2026-10-01) |
| BR-22 | 대화 턴은 늘릴 수 없다. CoT 3단계 범위를 넘는 턴은 삭제·병합 가능(첫 턴 제외, 사이클 3). 삭제 후 1부터 재번호, 제출 시 빈 turn textarea 비움 |
| BR-23 | 각 턴의 user 발화는 변경하지 않는다. assistant만 수정 |
| BR-24 | facts 개수는 초안과 동일(가변). 거짓 팩트는 틀린 요소(방향, 위치, 개수, 색, 사물명)만 최소 편집해 참 문장으로 만들고, 불가능하면 이미지에서 확인되는 다른 사실로 교체 |
| BR-25 | 새로 추가되는 정보는 이미지에서 확인 가능한 것만. 추측·일반 상식 서술 금지 |
| BR-26 | 문체 유지: assistant는 context.priority가 지시하는 말투(예: 아이에게 하는 반말, 한마디 이유 붙임)를 유지. scene/facts/cot는 초안의 서술체(~다) 유지 |
| BR-27 | 수정 후 scene, cot1~3, assistant가 수정된 facts와 모순되지 않아야 한다(R3) |
| BR-28 | 빈 문자열로 돌아온 필드는 초안 값으로 복원 |

## D. 상태·제출 규칙

| ID | 규칙 |
|---|---|
| BR-30 | 동시에 보유하는 ReviewItem은 최대 1개. READY 또는 DONE 상태에서만 가져오기 가능. 가져오기 대상 데이터셋은 화면에서 선택한 값(저장·복원)이며 READY/DONE/ERROR/EXPIRED 에서만 변경 가능(사이클 2) |
| BR-31 | 승인·불가·건너뛰기는 REVIEW 상태에서만 가능하고, 반드시 사용자 HTTP 요청으로만 시작된다. 서버 내부에서 자동 호출하는 코드 경로는 존재하지 않는다 |
| BR-32 | 제출 시작 시 remaining_seconds ≤ 0이면 제출하지 않고 EXPIRED로 전이 |
| BR-33 | 승인 제출 전 유효성: scene 비어 있지 않음, facts 전부(초안 개수) 비어 있지 않음, cot1~3 비어 있지 않음, 초안에 있던 턴의 assistant 비어 있지 않음. 위반 시 제출 거부·사유 표시 |
| BR-34 | 불가 제출 사유는 선택(공백 허용, 2026-09-23 사용자 결정). 플랫폼이 사유를 요구해 거부하면 그 알림 문구를 실패 사유로 기록 |
| BR-35 | 제출 결과는 LabelOn 결과 모달 텍스트로 판정. "저장되었습니다" 포함이면 성공. 실패 시 REVIEW로 복귀하고 편집값 보존 |
| BR-36 | 제출 절차 중 페이지의 job_id가 파싱 시점과 다르면 제출을 중단한다(다른 건에 덮어쓰기 방지) |
| BR-37 | 건너뛰기(반환)는 확인 질문을 거친 뒤 수행하고 이력에 SKIP으로 기록 |
| BR-38 | 마감 = job_date + 60분. 잔여 10분 미만 경고. 0 이하 EXPIRED. 페이지 카운트다운 텍스트가 읽히면 그 값으로 보정 |

## E. 오류·재시도 규칙

| ID | 규칙 |
|---|---|
| BR-40 | 모델 호출: 타임아웃 120초, 최대 2회 재시도(지수 백오프 2초, 4초). 429/5xx/네트워크만 재시도. 스키마 검증 실패는 1회 재요청 |
| BR-41 | 모델 최종 실패 시 judge 또는 revised 없이 초안 그대로 REVIEW. warnings에 사유. 사용자는 수동 검토·제출 가능 |
| BR-42 | 페이지 구조 오류(PageStructureError)는 즉시 ERROR. 재시도하지 않고 사유 표시(구조 변경 감지) |
| BR-43 | 로그인 만료 감지(로그인 페이지로 리다이렉트) 시 상태 유지하고 UI에 "다시 로그인" 안내. 재로그인 후 이어서 진행 |
| BR-44 | Submitter의 fill 값 불일치는 1회 재시도. 모달 미표시 10초는 실패 |

## F. 이력·데이터 규칙

| ID | 규칙 |
|---|---|
| BR-50 | 텍스트 이력은 무기한 보관 |
| BR-51 | 이미지 캐시는 fetched_at 기준 7일(설정) 경과 시 삭제. 시작 시 1회, 이후 24시간마다 |
| BR-52 | 모든 상태 전이는 items.state에 최종값을 반영하고, 제출·반환은 submissions에 별도 행으로 남긴다 |
| BR-53 | 비밀번호, API 키, 세션 쿠키 값은 어떤 테이블·로그에도 기록하지 않는다 |

## G. 스토리 인수 기준 대응

| 스토리 AC | 규칙/로직 |
|---|---|
| US-1 | BR-43, BR-53, SessionService |
| US-2 | BR-30, BR-40, BR-41, BR-42, 시간 예산 |
| US-3 | BR-01~BR-05, BR-10~BR-13 |
| US-4 | BR-20~BR-28, Diff 알고리즘 |
| US-5 | BR-31~BR-33, BR-35, BR-36, 제출 절차 |
| US-6 | BR-34, 불가 제출 절차 |
| US-7 | BR-32, BR-37, BR-38, 반환 절차 |
| US-8 | BR-50~BR-52 |
| US-9 | ConfigLoader 검증(NFR 단계에서 스키마 확정) |

## 사이클 7 개정 메모 (2026-10-02)
- BR-03/BR-21: Instruction(archetype·persona·task)은 모델이 바꾸지 않지만 **사람은 화면에서 편집**할 수 있다(필드 주소 archetype/persona/task). 제출은 최종안 Instruction 으로 textarea 3개를 채운다
- 건수 집계: 오늘/누적 = 승인 제출(APPROVE)만. 불가·반환은 보조 표시
- 상태 전이: REVIEW --REANALYZE--> JUDGING (같은 item_id·마감 유지, 사람 편집 초기화)
- 세션: login_required 가 켜지면 5초 간격 로그인 감시 → 로그인 확인 시 자동 해제·데이터셋 갱신

## 사이클 10 개정 메모 (2026-10-03)
- BR-05: 불가 후보는 더 이상 2단계 수정을 생략하지 않는다(`revision_rules.revise_impossible`, 기본 true). 수정안을 함께 보여 주고 사람이 '고쳐서 승인' 또는 '불가 제출'을 고른다
