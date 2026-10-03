# Application Design (통합)

유닛: labelon-ucle-reviewer
작성일: 2026-09-23
상세 문서: components.md, component-methods.md, services.md, component-dependency.md

## 1. 설계 결정 요약

| 결정 | 선택 | 근거 |
|---|---|---|
| 프로세스 구조 | 단일 Python 프로세스, asyncio | 명령 하나로 실행, 상태 공유 단순 |
| LabelOn 제출 경로 | 작업 화면 UI 조작(textarea 입력 + 제출·확인 클릭) | 플랫폼의 상태 결정·검증을 그대로 따름. RK-4 해소 |
| 모델 호출 계층 | ModelClient 인터페이스 + Agent SDK / Anthropic SDK 구현체 | RK-1 결과에 따라 설정만으로 전환 |
| 상태 전달 | SSE 푸시 + HTTP POST | 단방향 푸시로 충분 |
| 프론트엔드 | 단일 HTML + 순수 JS | 화면 1개, 빌드 불필요 |
| 이력 저장 | Repository 패턴 위 SQLite | 테스트 시 메모리 DB 교체 |

## 2. 구조 개요

```
+-----------------------------------------------------------------------------------+
|                         labelon-ucle-reviewer (single process)                     |
|                                                                                   |
|  +-------------------+   +-----------------------------+   +-------------------+  |
|  | C-13 ReviewWebApp |   | Services                    |   | C-10 StateMachine |  |
|  |  HTTP + SSE       |-->| S-01 Session  S-04 Submit   |-->|  ReviewItem       |  |
|  |  (localhost)      |   | S-02 Fetch    S-05 Deadline |   |  state, deadline  |  |
|  +---------+---------+   | S-03 Edit     S-06 History  |   +-------------------+  |
|            ^             +------+-----------+----------+                          |
|            | SSE/HTTP           |           |                                     |
|  +---------+---------+          v           v                                     |
|  | C-14 Frontend     |   +-------------+  +--------------------------------+      |
|  |  index.html       |   | C-02 Browser|  | Analysis                       |      |
|  +-------------------+   | C-03 Parser |  | C-05 Rule  C-07 Judge          |      |
|                          | C-04 Image  |  | C-06 Model C-08 Revise C-09Diff|      |
|                          | C-11 Submit |  +--------------------------------+      |
|                          +------+------+                    |                     |
|                                 |                           |                     |
|  +-------------------+          |         +-------------------+                   |
|  | C-01 Config       |          |         | C-12 HistoryRepo  |                   |
|  +-------------------+          |         |  SQLite           |                   |
|                                 |         +-------------------+                   |
+---------------------------------+-------------------------------------------------+
                                  |                           |
                                  v                           v
                      +-------------------+        +-------------------+
                      | LabelOn (Chrome,  |        | Claude (Agent SDK |
                      |  tool profile)    |        |  or Anthropic SDK)|
                      +-------------------+        +-------------------+
```

## 3. 컴포넌트 (요약)

| ID | 이름 | 한 줄 책임 |
|---|---|---|
| C-01 | ConfigLoader | 설정 파일 로드·검증 |
| C-02 | BrowserSession | 도구 전용 Chrome 프로필로 LabelOn 페이지 유지, 로그인 대기 |
| C-03 | LabelOnPageParser | 작업 화면에서 원천 데이터·초안·CSRF 파싱, 필드 locator 제공 |
| C-04 | ImageService | 이미지 다운로드·캐시·축소·정리 |
| C-05 | RuleChecker | R1(아키타입 템플릿·페르소나 일치) 결정론적 검사 |
| C-06 | ModelClient | judge/revise 인터페이스. Agent SDK, Anthropic SDK 구현체 |
| C-07 | JudgeStage | 1단계 판정, 점수·불가 후보·수정 필요 결정 |
| C-08 | ReviseStage | 2단계 수정안 생성과 제약 강제 |
| C-09 | DiffService | 문장 단위 diff |
| C-10 | ReviewStateMachine | 현재 건 상태·마감·이벤트 |
| C-11 | Submitter | UI 조작으로 승인/불가 제출, 반환 |
| C-12 | HistoryRepository | SQLite 이력 저장·조회 |
| C-13 | ReviewWebApp | 로컬 HTTP/SSE 서버 |
| C-14 | Frontend | 검토 화면 |

## 4. 서비스 (요약)

| ID | 서비스 | 스토리 |
|---|---|---|
| S-01 | SessionService | US-1 |
| S-02 | FetchAndAnalyzeService | US-2, US-3, US-4 |
| S-03 | EditService | US-4 |
| S-04 | SubmitService | US-5, US-6, US-7 |
| S-05 | DeadlineService | US-7 |
| S-06 | HistoryService | US-8 |
| S-07 | ConfigService | US-9 |

## 5. 핵심 시나리오: 건 1개 처리

1. 사용자가 "다음 건 가져오기" 클릭 → POST /actions/fetch → S-02 백그라운드 시작 (FETCHING)
2. C-02가 작업 화면을 열고 C-03이 SourceItem, Draft를 파싱. C-04가 이미지 축소본 생성
3. C-07이 C-05 규칙 검사와 C-06.judge를 합쳐 JudgeResult (JUDGING → JUDGED)
4. needs_revision이면 C-08이 C-06.revise로 RevisedDraft (REVISING → REVISED)
5. C-10이 REVIEW 상태 ReviewItem 보유. C-13이 SSE로 C-14에 전달. C-09 diff 표시
6. 사용자가 편집(PUT /draft) 또는 되돌리기. 카운트다운은 S-05가 관리
7. 사용자가 승인 → S-04 → C-11이 같은 작업 화면 textarea에 입력하고 제출·확인 클릭 → 결과 모달 읽기 (SUBMITTING → DONE)
8. C-12가 모든 단계 결과 저장. 상태 READY로 복귀

## 6. 추적표 (스토리 → 서비스 → 컴포넌트)

services.md 마지막 표와 components.md 요구사항 배정표 참조. 모든 FR-1~8과 US-1~9가 최소 1개 컴포넌트·서비스에 연결됨.

## 7. Functional Design으로 위임하는 항목

- consistency_score 산식과 needs_revision 결정 규칙
- RuleChecker의 템플릿 비교 허용 오차(조사 "가/이", 공백)
- judge/revise 프롬프트 본문과 출력 JSON 스키마 상세
- 문장 분할 규칙(DiffService)
- textarea 입력 시 React 상태 갱신 보장 방법과 모달 대기 절차(Submitter)
- SQLite 테이블 DDL
- Frontend 레이아웃과 단축키 상세

## 8. NFR 단계로 위임하는 항목

- 모델 백엔드 확정(Agent SDK vs Anthropic SDK)과 실제 계정 검증(RK-1)
- 웹 프레임워크 선정(FastAPI 등), 프롬프트 캐싱 구조, 재시도·타임아웃 값
- 이미지 축소 크기와 토큰 비용 추정
