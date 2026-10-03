# Services

서비스는 컴포넌트를 조합해 사용자 스토리 하나를 완결한다. 모두 단일 프로세스 안에서 동작하며 ReviewStateMachine을 통해 상태를 공유한다.

---

## S-01. SessionService
- **스토리**: US-1
- **책임**: 앱 시작 시 BrowserSession.start → 로그인 여부 확인 → 미로그인이면 로그인 페이지 표시 후 대기. 로그인 완료 시 상태 기계를 READY로. 이후 주기적으로(5분) 로그인 상태 확인
- **사용 컴포넌트**: C-02, C-10
- **흐름**:
  1. start()
  2. is_logged_in()? 아니면 wait_for_login() (UI에 "로그인을 완료해 주세요")
  3. transition(RESET) → READY

## S-02. FetchAndAnalyzeService
- **스토리**: US-2, US-3, US-4(수정안 생성 부분)
- **책임**: 건 1개를 가져와 판정·수정까지 마치고 REVIEW 상태로 올린다
- **사용 컴포넌트**: C-02, C-03, C-04, C-05, C-07, C-08, C-09, C-10, C-12
- **흐름**:
  1. 전제: current() is None 또는 state in {READY, DONE}. 아니면 IllegalTransition
  2. transition(FETCH_STARTED) → FETCHING
  3. open_job_page(dataset_id) → PageKind. JOB이 아니면 NoJobAvailable(kind) → FAILED(사유 표시)
  4. parse(page) → (item, draft). save_item → item_id. transition(PARSED)
  5. ImageService.fetch → images
  6. transition(JUDGING) → JudgeStage.run → judge. save_judge. transition(JUDGED)
  7. judge.needs_revision이면 transition(REVISING) → ReviseStage.run → revised. save_revision. transition(REVISED). 아니면 revised = draft 복사
  8. FinalDraft 초기값 = revised. diff 계산. transition(REVIEW_READY) → REVIEW
  9. 모델 오류(ModelCallError) 시: judge 또는 revised 없이 FinalDraft = draft로 REVIEW_READY. 오류 메시지를 ReviewItem.warnings에 추가(US-2 AC5)
- **시간**: 3분 초과 시 UI에 경고만 표시하고 계속 진행

## S-03. EditService
- **스토리**: US-4
- **책임**: 사용자 편집값을 FinalDraft에 반영하고 diff 재계산, 되돌리기
- **사용 컴포넌트**: C-09, C-10, C-12
- **흐름**: PUT /draft → 유효성(facts 5개, 턴 수 유지) → transition(EDITED) / POST revert → FinalDraft = 서버 초안 → transition(REVERTED)

## S-04. SubmitService
- **스토리**: US-5, US-6, US-7(건너뛰기)
- **책임**: 사용자의 명시적 동작으로만 LabelOn에 제출·반환
- **사용 컴포넌트**: C-02, C-03(locators, csrf), C-10, C-11, C-12
- **흐름 approve**:
  1. 전제 state == REVIEW. remaining_seconds() <= 0이면 ItemExpired → EXPIRED
  2. transition(SUBMIT_STARTED) → SUBMITTING. save_final
  3. Submitter.approve(page, final, locators) → rec
  4. 성공: save_submission, transition(SUBMITTED) → DONE. 실패: transition(SUBMIT_FAILED) → REVIEW(편집값 보존) + 오류 메시지
- **흐름 impossible**: 사유 필수 검증 → 위와 동일하되 Submitter.impossible
- **흐름 skip(release)**: 확인 후 Submitter.release → save_submission(kind=SKIP) → transition(RELEASED) → READY

## S-05. DeadlineService
- **스토리**: US-7
- **책임**: 1초 주기로 remaining_seconds 계산, 10분 미만 경고 플래그, 0 이하이면 transition(EXPIRED), mark_state(EXPIRED)
- **사용 컴포넌트**: C-10, C-12

## S-06. HistoryService
- **스토리**: US-8
- **책임**: 상태 기계 이벤트를 구독해 mark_state 기록, 조회 API 제공, 앱 시작 시 find_unfinished를 UI에 전달, ImageService.cleanup 실행
- **사용 컴포넌트**: C-04, C-10, C-12

## S-07. ConfigService
- **스토리**: US-9
- **책임**: 시작 시 ConfigLoader.load, 오류 시 항목명 출력 후 종료. UI용 설정 노출
- **사용 컴포넌트**: C-01

---

## 상태 전이와 서비스

```
  READY --FETCH_STARTED--> FETCHING --PARSED--> JUDGING --JUDGED--> REVISING --REVISED--> REVIEW
    ^                          |                   |                  |                    |
    |                          |(NoJobAvailable)   |(ModelCallError)  |(ModelCallError)    |
    |                          v                   v                  v                    |
    |                        ERROR             REVIEW(초안 그대로)  REVIEW(초안 그대로)      |
    |                          |                                                           |
    |<---------RESET-----------+                                                           |
    |                                                                                      |
    |<---RELEASED---- SUBMITTING <--SUBMIT_STARTED-- (approve / impossible / skip) <--------+
    |                    |         \                                                       |
    |                    |          `--SUBMIT_FAILED--> REVIEW                             |
    |                    v                                                                 |
    +-------------------DONE                                        REVIEW --EXPIRED--> EXPIRED --RESET--> READY
```

문자 설명: READY에서 fetch로 시작해 FETCHING, JUDGING, REVISING을 거쳐 REVIEW에 도달한다. 모델 오류는 초안 그대로 REVIEW로 보낸다. REVIEW에서 approve, impossible, skip은 SUBMITTING을 거쳐 DONE(또는 skip이면 READY)으로 가고, 실패하면 REVIEW로 돌아온다. 마감이 지나면 EXPIRED가 되고 RESET으로 READY가 된다.

---

## 스토리 → 서비스 → 컴포넌트

| 스토리 | 서비스 | 핵심 컴포넌트 |
|---|---|---|
| US-1 로그인 세션 준비 | S-01 | C-02, C-10 |
| US-2 다음 건 가져오기 | S-02 | C-02, C-03, C-04, C-10 |
| US-3 판정 결과 확인 | S-02 | C-05, C-06, C-07, C-14 |
| US-4 수정안 편집 | S-02, S-03 | C-08, C-09, C-14 |
| US-5 승인·제출 | S-04 | C-11, C-03 |
| US-6 불가 제출 | S-04 | C-11 |
| US-7 반환·제한시간 | S-04, S-05 | C-10, C-11, C-14 |
| US-8 이력·비용 | S-06 | C-12, C-04 |
| US-9 설정 변경 | S-07 | C-01 |
