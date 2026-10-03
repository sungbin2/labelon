# Cycle 8 Code Summary - 항목별 되돌리기 · 삭제 금지 · Git 배포

생성일: 2026-10-03. 계획: `cycle8-code-generation-plan.md` (4단계 전부 [x]).

## 변경 파일
| 파일 | 변경 |
|---|---|
| `config.py`, `config.yaml`, `config.example.yaml` | `RevisionRules.allow_turn_drop`(기본 false) |
| `revise.py` | `raw_to_draft(..., allow_drop)`; 설정이 false 면 drop 무시(모든 턴 유지) |
| `prompts/__init__.py` | revise 사용자 프롬프트에 "턴 삭제: 금지/허용" 블록 |
| `services.py` | `validate_final(final, draft)`: 초안에 있던 턴을 통째로 비우면 차단; `EditService.revert_field` |
| `web/app.py` | `RevertField` 모델, `POST /actions/revert-field` |
| `web/static/app.js`, `style.css` | 변경된 항목마다 "초안으로" 버튼(초안 패널·턴 user/assistant·Instruction 행), 삭제 차단 검증, `fieldLabel` instruction |
| `run.bat` | 시작 시 `git pull --ff-only` → 변경 시 `pip install -e .` → 실행. 실패 시 경고 후 실행. `--no-update` |
| `.gitignore` | `guide/`, `*.zip` 추가 |
| `README.md` | git clone 설치, 자동 업데이트, 새 설정 |
| `tests/` | test_revise(drop 무시 기본·허용 시 삭제), test_services(삭제 차단, revert_field), test_web(/actions/revert-field) |

## 테스트
`pytest -q` → **119 passed** (사이클 7: 117). ruff·node check 통과.

## 비고
- 작업 중 `RevertField` 를 함수 안에 정의해 FastAPI 가 422 를 내는 문제가 있어 모듈 수준으로 옮김. 테스트 삽입 위치 오류 1건 정정
