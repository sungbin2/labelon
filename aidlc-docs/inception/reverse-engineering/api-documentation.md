# API Documentation (Reverse Engineering, 2026-09-28)

## 로컬 검토 API (FastAPI, 127.0.0.1:8765)
상태 변경 요청(POST/PUT)은 Origin/Host 가 127.0.0.1:{port} 또는 localhost:{port} 여야 한다(403).

| Method | Path | 설명 | 오류 |
|---|---|---|---|
| GET | / | index.html | |
| GET | /static/{name} | 정적 파일 | 404 |
| GET | /state | ReviewItem 스냅샷 + summary + server_now | |
| GET | /config | dataset_id, persona, threshold, models, effort, model_backend, job_time_limit_minutes, archetypes | |
| GET | /events | SSE `event: state` 스냅샷, 30초 heartbeat | |
| POST | /actions/fetch | 가져오기·분석 시작(202) | 409 진행 중/상태 위반 |
| PUT | /draft {field, value} | 최종안 편집, diff 재계산 | 409 |
| POST | /actions/revert | 초안으로 되돌리기 | 409 |
| POST | /actions/approve | 승인 제출 | 409/410(만료)/422(유효성) |
| POST | /actions/impossible {reason} | 불가 제출(사유 선택) | 409/410 |
| POST | /actions/skip | 반환 | 409/410 |
| POST | /actions/reopen-browser | Chrome 재실행 | |
| POST | /actions/shutdown | 서버 종료 | |
| GET | /history?limit | 최근 목록 + 미완료 | |
| GET | /history/summary | 집계 | |
| GET | /history/{id} | 상세 | 404 |
| GET | /images/{item_id} | 캐시 이미지 | 404 |

## 소비하는 외부 인터페이스
| 대상 | 방식 | 비고 |
|---|---|---|
| LabelOn `/project/home` | 요청 API GET(로그인 판별) | 미로그인 시 `/access` 리다이렉트 |
| LabelOn `/job/ucle/annotator?datasetId=N` | 페이지 이동 + HTML 파싱 | 열면 건 할당(60분) |
| LabelOn 작업 화면 DOM | Playwright fill/click, 모달 `#commonmodal2`/`#commonmodal1` | 제출 |
| LabelOn `/job/ucle/annotator/resetData` | 페이지 컨텍스트 jQuery POST | 반환 |
| Claude Code CLI `claude -p` | 서브프로세스(stdin 프롬프트, --json-schema, Read 도구) | judge/revise |
