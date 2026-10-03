# Cycle 8 Requirements: 항목별 되돌리기 · 삭제 금지 · Git 배포·자동 업데이트

작성일: 2026-10-03. 깊이: Minimal. 실행 계획 포함(Code Generation → Build and Test).

## 1. Intent Analysis
| 항목 | 내용 |
|---|---|
| User Request | (1) 각 항목은 삭제하지 않고 수정만 (2) 항목마다 수정안을 초안으로 되돌리기 (3) git 에 올리고 run.bat 이 자동 업데이트 |
| Request Type | Enhancement + 배포 방식 변경 (Brownfield) |
| Scope | revise(턴 삭제 끄기), services(항목 되돌리기·검증), web API, 프론트엔드(항목별 버튼), run.bat/setup.bat, .gitignore, README, git 저장소 |
| Complexity | Low-Moderate |

## 2. 기능 요구사항
### FR-C8-1. 삭제 금지 (Q2)
- 모델의 턴 삭제(drop) 기능을 설정 `revision_rules.allow_turn_drop`(기본 **false**)으로 끈다. false 면 revise 결과의 drop 을 무시하고 턴 수를 유지하며, 프롬프트에도 "턴을 삭제하지 말고 내용을 고쳐라" 로 안내한다
- 사람 편집: 초안에 내용이 있던 항목(Instruction 3개, Scene, Facts, CoT, 각 턴의 user/assistant)을 빈 값으로 두면 승인 차단("… 비어 있습니다" 기존 + 턴 전체 비움 추가). 턴을 통째로 비우는 것은 삭제로 보아 차단

### FR-C8-2. 항목별 초안 되돌리기
- `POST /actions/revert-field {field}`: 최종안의 해당 필드만 서버 초안 값으로 되돌리고 diff 재계산. 필드 주소는 편집 주소와 동일(archetype/persona/task/scene/fact_N/cot1~3/turn_N_user/turn_N_assistant)
- 화면: 변경된 항목의 머리글에 "초안으로" 작은 버튼. Instruction 행에도 동일. 전체 되돌리기(Alt+R)는 유지

### FR-C8-3. Git 배포·자동 업데이트 (Q1, Q3)
- 작업 폴더를 git 저장소로 초기화하고 사용자가 지정한 원격(private)에 올린다. `.gitignore` 에 `guide/`(회사 자료) 추가. 비밀번호·토큰은 저장소에 없음(점검 완료). 계정 이메일은 감사 로그에 남아 있음(private 저장소 전제)
- `run.bat`: 시작 시 `.git` 이 있고 `git` 이 PATH 에 있으면 `git pull --ff-only` 시도. 변경이 있으면 `pip install -e .` 후 실행. 네트워크 오류·충돌이면 경고만 내고 현재 버전으로 실행. `--no-update` 인자로 건너뛰기
- `setup.bat`: 변경 없음(클론 후 실행). README 에 "git clone → setup.bat → run.bat" 설치 절차와 zip 대체 안내
- 다른 PC 는 `git clone <원격>` 후 setup.bat. config.yaml 은 PC 별 로컬 파일(ignore 유지)

## 3. 인수 기준
- AC-C8-1 `allow_turn_drop=false`(기본)에서 revise 가 drop=true 를 보내도 최종안 턴 수가 초안과 같다
- AC-C8-2 초안에 있던 턴의 user·assistant 를 모두 비우면 validate_final 이 차단한다
- AC-C8-3 `POST /actions/revert-field {field: fact_2}` 가 fact_2 만 초안으로 되돌리고 다른 편집은 유지한다
- AC-C8-4 run.bat 이 git 저장소에서 `git pull` 을 수행하고, 실패해도 서버가 실행된다
- AC-C8-5 기존 117개 테스트 유지
