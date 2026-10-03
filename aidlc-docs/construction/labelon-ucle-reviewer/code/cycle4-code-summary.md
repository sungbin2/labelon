# Cycle 4 Code Summary - 검수 가이드 이미지 슬라이드 반영

생성일: 2026-09-28. 계획: `cycle4-code-generation-plan.md` (5단계 전부 [x]).

## 변경 파일
| 파일 | 변경 |
|---|---|
| `domain.py` | `ImpossibleFlags`(core_error_propagated, persona_infeasible_guidance, unsafe_guidance, note, `any()`), `TextIssue`(field, kind, wrong, correct), `JudgeResult.archetype_fits_environment/environment_note/impossible_flags/text_issues` |
| `schemas.py` | JUDGE_SCHEMA 에 위 4개 필드(required), text_issues.kind enum typo/speculation/number |
| `prompts/judge_system.md` | QA 검수 포인트, 텍스트 오류 3종 정의, 불가 예시 1~7, archetype_fits_environment 와 archetype_suggestion 구분 |
| `prompts/revise_system.md` | 규칙 15 텍스트 오류 반영(오탈자·숫자·추측) |
| `prompts/__init__.py` | 판정 블록에 텍스트 오류 목록 |
| `judge.py` | normalize_raw 새 필드(누락 시 문제 없음, 잘못된 kind 무시), 환경 충돌 시 아키타입 정정 미적용+경고, 불가 사유 4종 추가, text_issues → needs_revision |
| `web/static/app.js`, `style.css` | 환경 부적합 배지, 텍스트 오류 목록(필드 클릭 이동, 종류 태그) |
| `tests/conftest.py`, `tests/test_judge.py` | 기본값, 신규 6개(환경 충돌·정정 미적용, 플래그 3종 파라미터, text_issues → 수정·프롬프트, 누락 보정) |
| `README.md`, `business-rules.md`(BR-05), `domain-rules.md`(6절) | 문서 |

## 테스트
`pytest -q` → **108 passed** (사이클 3: 102). ruff 통과. `node --check app.js` 통과.

## 규칙 요약 (동작)
- 불가 후보 사유 9종 = 사이클 3 의 5종 + 환경 충돌 / 오인식 전파 / 페르소나 불가 안내 / 위험 행위 권고. 환경 충돌이면 아키타입 정정 제안은 무시하고 경고를 남김
- 수정 필요 조건에 text_issues 추가. revise 사용자 프롬프트에 "텍스트 오류 field (종류): '잘못' → '바름'" 로 전달
- 설정·제출기·서비스 변경 없음. 구버전 모델 출력(필드 누락)도 "문제 없음"으로 동작

## 미검증 (Build and Test)
- 실제 모델이 환경 충돌과 라벨 불일치를 구분해 판정하는지, text_issues 를 과잉 생성하지 않는지 → 실제 건에서 확인
