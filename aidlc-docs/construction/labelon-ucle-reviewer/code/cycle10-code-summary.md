# Cycle 10 Code Summary - 불가 후보 건에도 수정안 생성

생성일: 2026-10-03.

| 파일 | 변경 |
|---|---|
| `config.py`, `config.yaml`, `config.example.yaml` | `revision_rules.revise_impossible`(기본 true) |
| `judge.py` | `needs_revision = (revise_impossible or not impossible) and (조건들)` |
| `web/static/app.js` | 불가 후보 알림에 "수정안도 생성되었습니다…" 안내 |
| `README.md`, `business-rules.md` | BR-05 개정 |
| `tests/test_judge.py` | 불가 후보 + 수정 조건 → needs_revision True, 설정 false 면 False |

테스트 121 passed, ruff·node 통과. v0.10.0.
