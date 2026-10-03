# Interaction Diagrams (Reverse Engineering, 2026-09-28)

## 건 가져오기·분석
```mermaid
sequenceDiagram
    participant UI as Frontend
    participant API as web/app.py
    participant F as FetchAndAnalyzeService
    participant B as BrowserSession
    participant P as parser
    participant J as JudgeStage
    participant R as ReviseStage
    participant M as ClaudeCliModelClient
    UI->>API: POST /actions/fetch
    API->>F: start()
    F->>B: open_job_page(config.dataset_id)
    B-->>F: (kind, html)
    F->>P: parse_html(html)
    F->>J: run(images, item, draft)
    J->>M: judge → claude -p (sonnet-5)
    F->>R: run(...)
    R->>M: revise → claude -p (fable-5-1, refusal 시 sonnet-5)
    F-->>UI: SSE state=REVIEW
```

## 승인 제출
```mermaid
sequenceDiagram
    participant UI as Frontend
    participant API as web/app.py
    participant S as SubmitService
    participant Sub as Submitter
    participant L as LabelOn 작업 화면
    UI->>API: POST /actions/approve
    API->>S: approve()
    S->>Sub: approve(page, final, job_id)
    Sub->>L: job_id 재확인, textarea fill, 가능 radio, 제출 클릭
    L-->>Sub: #commonmodal2 확인 모달
    Sub->>L: 확인 클릭
    L-->>Sub: #commonmodal1 결과("저장되었습니다")
    Sub-->>S: SubmissionRecord
    S-->>UI: SSE state=DONE
```

## 변경 요청이 닿는 상호작용
- 가져오기 시퀀스의 `open_job_page(config.dataset_id)` 가 "사용자가 선택한 데이터셋"으로 바뀌어야 한다
- 프로젝트 홈에서 진행중 데이터셋 목록을 읽는 새 상호작용(BrowserSession 요청 API → parser)이 필요하다
