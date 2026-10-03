# NFR Requirements - labelon-ucle-reviewer

작성일: 2026-09-23. 요구사항 NFR-1~7과 NFR 질문 답변(모두 권장안)을 구체화한다.

## 1. 성능

| ID | 요구사항 | 값 |
|---|---|---|
| P-1 | 건당 처리 시간(가져오기 → 판정 → 수정 → 검토 대기) | 목표 90초, 180초 초과 시 UI 경고 |
| P-2 | 모델 호출 타임아웃 | judge 120초, revise 180초 |
| P-3 | 이미지 축소 | 긴 변 1568px JPEG 품질 85. 4000x3000 원본 → 1568x1176, 비전 토큰 약 2,400 |
| P-4 | 프롬프트 고정부 앞배치 | system prompt 파일(규칙·템플릿·스키마)은 호출 간 불변. 가변부(이미지·초안·연관 QA)만 user 프롬프트 |
| P-5 | 검토 화면 반응 | 편집 → diff 갱신 1초 이내(400ms debounce + 서버 처리) |
| P-6 | 측정치(2026-09-23 검증) | 텍스트 1회: API 1.6초. 이미지 Read + JSON 스키마: API 7.5초, 4턴, 출력 384토큰 |

## 2. 신뢰성

| ID | 요구사항 |
|---|---|
| R-1 | 모델 호출 실패(비0 종료, is_error, JSON 파싱 실패, 타임아웃)는 최대 2회 재시도(2초, 4초 백오프). 최종 실패 시 초안 그대로 REVIEW + warnings |
| R-2 | 스키마 검증은 CLI의 `--json-schema`가 1차 보장. 도구가 pydantic으로 2차 검증. 불일치 시 1회 재요청 |
| R-3 | 제출은 결과 모달 텍스트로만 성공 판정. 판정 불가(모달 미표시)면 실패로 기록하고 사용자에게 LabelOn 화면 확인 안내 |
| R-4 | 비정상 종료 후 재시작 시 이력 DB의 미완료 건 표시. LabelOn 60분 만료가 자동 반환 |
| R-5 | 로그인 만료 감지 시 진행 중 상태 유지, "다시 로그인" 안내 후 재시도 가능 |
| R-6 | CLI 실행 환경 격리: 호출마다 새 프로세스, `--no-session-persistence`, 세션 파일 미생성 |

## 3. 보안·개인정보

| ID | 요구사항 |
|---|---|
| S-1 | LabelOn 비밀번호, Anthropic API 키, OAuth 토큰, 세션 쿠키 값을 코드·설정·DB·로그에 저장하지 않는다. 자격증명은 Chrome 프로필(LabelOn)과 Claude Code 자체 저장소(Claude)에만 존재 |
| S-2 | 검토 웹 서버는 127.0.0.1에만 바인딩. 외부 인터페이스 노출 금지 |
| S-3 | 외부 전송 대상은 LabelOn(labelon.kr, images.labelon.kr)과 Anthropic(Claude Code CLI 경유) 두 곳으로 한정 |
| S-4 | 모델 요청·응답 본문은 DEBUG 로그에서만 기록. INFO 로그에는 건 ID, 상태, 점수, 토큰 수만 |
| S-5 | Chrome 전용 프로필 디렉터리와 이미지 캐시, DB는 `.gitignore`에 포함 |
| S-6 | CLI 호출 시 도구는 Read 도구만 허용(`--tools Read`, `--permission-mode dontAsk`, `--permission-prompts none`). Bash·Write·Edit·Web 도구 비활성 |

## 4. 가용성·운영

| ID | 요구사항 |
|---|---|
| A-1 | 단일 사용자, 단일 프로세스. 고가용성 요구 없음 |
| A-2 | 시작: `run.bat` → venv 활성화 → uvicorn 기동 → 기본 브라우저로 검토 화면 오픈 → Chrome 전용 프로필 창 자동 실행 |
| A-3 | 종료: Ctrl+C 또는 검토 화면 "종료" 버튼 → Chrome 창 정리 → 현재 건이 REVIEW면 이력에 미완료로 남김 |
| A-4 | 로그: `logs/app.log` 회전(5MB x 5), 콘솔 INFO |

## 5. 유지보수성

| ID | 요구사항 |
|---|---|
| M-1 | 설정 `config.yaml`: dataset_id, persona, archetype_templates, threshold, models{judge, revise}, effort{judge, revise}, model_backend(claude_cli / anthropic_sdk), image_max_side, cache_retention_days, ui_port, chrome{channel, profile_dir}, cli{path, cwd, timeouts}. pydantic 스키마로 검증, 오류 시 항목명 출력 |
| M-2 | LabelOn 구조 지식은 `labelon/parser.py`, `labelon/submitter.py` 두 모듈에 격리 |
| M-3 | 모델 백엔드는 `ModelClient` 프로토콜 구현체 교체. 설정 1줄로 전환 |
| M-4 | 테스트: pytest. 파서(HTML 픽스처), RuleChecker, Score, enforce_constraints, Diff, StateMachine, HistoryRepository(메모리 DB), 서비스(모델 목). 실브라우저·실모델은 `docs/manual-checklist.md` |
| M-5 | 코드 스타일: ruff 기본 규칙, 타입 힌트 필수 |

## 6. 사용성

| ID | 요구사항 |
|---|---|
| U-1 | 한국어 UI, 단축키 Alt+N/A/X/S/R |
| U-2 | 진행 단계·경과 시간 표시, 3분 초과 경고 |
| U-3 | 잔여 제한시간 카운트다운, 10분 미만 경고 |

## 7. 사용량·비용

| ID | 요구사항 |
|---|---|
| C-1 | 구독 계정 사용량 한도에 대한 상한은 두지 않고 건별·누적 토큰(입력, 출력, 캐시 읽기, 캐시 생성)과 CLI가 보고한 추정 비용(total_cost_usd, 정가 기준)을 기록·표시 |
| C-2 | 측정치: 텍스트 1회 = 캐시 읽기 24,464 + 캐시 생성 18,718 토큰, 추정 $0.080. 이미지+스키마 1회(4턴) = 캐시 읽기 112,396 + 캐시 생성 16,993 + 출력 384, 추정 $0.094. 기본 Claude Code 컨텍스트가 호출당 약 4~5만 토큰을 차지함 |
| C-3 | 컨텍스트 절감 목표: `--system-prompt`(기본 프롬프트 대체), `--disable-slash-commands`, `--tools Read`, `--strict-mcp-config` + 빈 MCP 설정, CLAUDE.md가 없는 작업 디렉터리 사용으로 호출당 기본 컨텍스트를 1만 토큰 이하로 줄인다. Build and Test 단계에서 실측·기록 |
| C-4 | 2단계(fable-5-1)는 수정 필요 건에만 호출. 불가 후보는 생략 |
| C-5 | 20건 처리 후 누적 사용량을 확인하고 구독 한도 대비 처리 가능 속도를 사용자에게 보고(운영 지침) |

## 8. 확장성

| ID | 요구사항 |
|---|---|
| X-1 | 다른 UC-LE 데이터셋은 config의 dataset_id, persona 변경으로 대응 |
| X-2 | 모델 백엔드 `anthropic_sdk`(API 키 또는 ant OAuth 프로파일)로 전환 가능. Claude Code 정책·동작 변경 시 대비책 |
| X-3 | 동시 처리는 지원하지 않음(완전 순차). 향후 확장 시 상태 기계를 건별 인스턴스로 확장 |

## 9. 리스크 갱신

| ID | 상태 | 내용 |
|---|---|---|
| RK-1 인증 경로 | 부분 해소 | `claude -p`(비 bare 모드)가 기존 로그인으로 동작함을 이 PC에서 검증. 잔여: (a) Agent SDK 문서의 정책 문구 "Anthropic does not allow third party developers to offer claude.ai login or rate limits for their products" — 본 도구는 계정 소유자 본인이 자기 PC에서 쓰는 개인 도구이며 Claude Code의 공식 headless 기능을 사용하지만, 정책 해석의 최종 판단은 사용자에게 있음. (b) 문서에 "`--bare`가 향후 `-p`의 기본이 될 것"이라 명시되어 있고 bare 모드는 OAuth 자격증명을 읽지 않으므로, Claude Code 업데이트 후 동작이 바뀌면 `anthropic_sdk` 백엔드로 전환 |
| RK-4 jobStatus | 해소 예정 | UI 조작 제출로 플랫폼이 결정. Build and Test에서 1건 관찰 |
| RK-6 (신규) 32비트 Python | 해소 | 기본 python이 32비트 3.12라 네이티브 휠 빌드 실패. 64비트 Python 3.13으로 venv 재생성 완료 |
| RK-7 (신규) 컨텍스트 사용량 | 관리 중 | 호출당 기본 컨텍스트 4~5만 토큰. C-3 절감 후 실측 |
