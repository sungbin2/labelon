# Logical Components - labelon-ucle-reviewer

## 1. 논리 컴포넌트

| 컴포넌트 | 종류 | 수량 | 소유·생명주기 |
|---|---|---|---|
| Reviewer 서버 프로세스 | Python 프로세스(uvicorn + asyncio) | 1 | `run.bat`이 시작. Ctrl+C 또는 UI 종료 버튼으로 종료 |
| 검토 화면 브라우저 탭 | 사용자 기본 브라우저 | 1 | 서버가 시작 시 `webbrowser.open`. 서버가 소유하지 않음 |
| Chrome 전용 프로필 창 | Playwright persistent context(channel=chrome) | 1 | 서버가 실행·소유. 서버 종료 시 `context.close()`. 사용자가 닫으면 감지 후 재실행 버튼 |
| CLI 서브프로세스 | `claude.exe -p` | 최대 1 (동시) | 모델 호출마다 생성·종료. 타임아웃 시 트리 종료 |
| 백그라운드 분석 태스크 | asyncio.Task | 최대 1 | fetch 요청으로 생성, 완료·취소로 소멸 |
| 마감 감시 태스크 | asyncio.Task | 1 | 서버 수명 동안 상주 |
| SSE 채널 | asyncio.Queue(구독자별) | 구독자 수(보통 1) | 클라이언트 연결마다 생성 |
| SQLite DB | 파일 `data/history.db` | 1 커넥션 | 서버 시작 시 열고 종료 시 닫음. WAL |
| 이미지 캐시 | 파일 `data/cache`, `data/resized` | n | 7일 보관, 시작 시·24시간마다 정리 |
| 로그 | 파일 `logs/app.log` 회전 | 1 | 상주 |
| CLI 작업 디렉터리 | 빈 디렉터리(CLAUDE.md 조상 없음) | 1 | 설정 `cli.cwd`, 없으면 생성 |

## 2. 프로세스·태스크 모델

```
+------------------------------------------------------------------------------------+  
| run.bat                                                                            |  
|   +-- .venv\Scripts\python -m labelon_reviewer                                     |  
|        +--------------------------------------------------------------------------+|  
|        | uvicorn (asyncio loop, 127.0.0.1:8765)                                   ||  
|        |                                                                          ||  
|        |  [Task] HTTP/SSE 핸들러 (요청마다)                                         ||       
|        |  [Task] DeadlineService  (1초 tick)                                        || 
|        |  [Task] FetchAndAnalyze  (최대 1개, fetch 요청 시 생성)                     ||       
|        |     |                                                                    ||  
|        |     +--> Playwright (Chrome 프로필 창 조작, 비동기 IPC)                     ||        
|        |     +--> to_thread: Pillow 축소, sqlite3 저장                              ||    
|        |     +--> create_subprocess_exec: claude.exe -p ... (judge) ---+           || 
|        |     +--> create_subprocess_exec: claude.exe -p ... (revise) --+           || 
|        |  [Task] BrowserLiveness (5초 tick)                              |           ||
|        +----------------------------------------------------------------|----------+| 
|                                                                         |            |
+-------------------------------------------------------------------------|------------+
                 |                                    |                   |             
                 v                                    v                   v             
   +------------------------+        +------------------------+   +------------------+  
   | Chrome (channel=chrome)|        | 기본 브라우저 탭        |   | claude.exe (node)|        
   | user-data-dir=.profile |        | http://127.0.0.1:8765  |   | Read 도구만      |     
   | labelon.kr 로그인 세션 |        | index.html + SSE       |   | 이미지 파일 읽기  |             
   +------------------------+        +------------------------+   +------------------+  
```

## 3. 자원 한도

| 자원 | 한도 | 강제 위치 |
|---|---|---|
| 동시 ReviewItem | 1 | ReviewStateMachine(BR-30) |
| 동시 분석 태스크 | 1 | FetchAndAnalyzeService (409) |
| 동시 CLI 서브프로세스 | 1 | 분석 태스크가 순차 호출 |
| SQLite 커넥션 | 1 | HistoryRepository (to_thread 직렬화) |
| Chrome 페이지 | 1 (작업 화면 탭) | BrowserSession |
| 이미지 캐시 용량 | 7일 보관, 별도 용량 상한 없음 | ImageService.cleanup |

## 4. 시작 시퀀스

1. `run.bat`: venv 활성화 → `python -m labelon_reviewer --config config.yaml`
2. ConfigLoader.load → 실패 시 항목명 출력 후 종료(코드 2)
3. 로깅 초기화, `data/`, `logs/`, `.profile/`, `cli.cwd` 디렉터리 생성
4. HistoryRepository 열기(스키마 마이그레이션 = CREATE TABLE IF NOT EXISTS), ImageService.cleanup
5. `ANTHROPIC_API_KEY` 존재 시 경고 로그
6. uvicorn 기동 → lifespan startup에서 BrowserSession.start(Chrome 창 표시) → SessionService.ensure_login(비동기, 로그인 대기는 UI 안내)
7. DeadlineService, BrowserLiveness 태스크 시작
8. `webbrowser.open("http://127.0.0.1:8765")`
9. 미완료 건이 있으면 첫 SSE 스냅샷에 포함

## 5. 종료 시퀀스

1. Ctrl+C 또는 POST /actions/shutdown(UI 종료 버튼, Origin 검사 대상)
2. 진행 중 분석 태스크 취소 → 실행 중 CLI 서브프로세스 트리 종료
3. 현재 건이 REVIEW/SUBMITTING이면 `mark_state(state, "server shutdown")`(자동 반환·제출 없음)
4. BrowserSession.close() → Chrome 창 종료(프로필·세션 보존)
5. SQLite 닫기, 로그 flush

## 6. 실패 시 컴포넌트별 동작

| 실패 | 감지 | 동작 |
|---|---|---|
| Chrome 창 사용자 종료 | BrowserLiveness | 상태 유지, UI 배너 + "브라우저 다시 열기" 버튼 → BrowserSession.start 재실행 |
| LabelOn 로그인 만료 | open_job_page가 LOGIN 종류 반환 | LoginRequired → UI "다시 로그인" 안내, 로그인 후 fetch 재시도 |
| claude.exe 없음/인증 실패 | 서브프로세스 비0 종료 + stderr | ModelCallError → 초안 그대로 REVIEW, warnings에 stderr 요약, 설정 백엔드 전환 안내 |
| SQLite 잠김/오류 | 예외 | 해당 저장 실패를 로그·UI 경고. 처리 흐름은 계속(이력 손실 경고) |
| 포트 8765 사용 중 | uvicorn 기동 실패 | 오류 메시지와 `ui_port` 변경 안내 후 종료 |
