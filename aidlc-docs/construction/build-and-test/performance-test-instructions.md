# Performance Test Instructions

## Purpose
단일 사용자 로컬 도구이므로 부하·동시성 테스트는 해당 없음. 성능 요구는 건당 처리 시간(P-1)과 모델 호출 컨텍스트(C-3)다.

## Performance Requirements
- **건당 처리 시간**: 가져오기 → 판정 → 수정 → 검토 대기 목표 90초, 180초 초과 시 UI 경고
- **모델 타임아웃**: judge 120초, revise 180초
- **컨텍스트**: 호출당 기본 컨텍스트 1만 토큰 이하(NFR C-3)
- **UI 반응**: 편집 → diff 갱신 1초 이내

## Measured (2026-09-23)
| 항목 | 값 |
|---|---|
| CLI 호출 기본 컨텍스트 (`minimal`) | 2,193 토큰 (basic 35,659 대비 94% 절감) — 목표 달성 |
| 짧은 호출 API 시간 (`minimal`) | 1.4초 |
| NFR 단계 이미지 Read + 스키마 호출 (basic 프로필) | API 7.5초, 4턴 |
| Chrome 기동 | 1.4초 |
| 단위 테스트 전체 | 1.1초 |

## Run Performance Checks

### 1. 컨텍스트 벤치
```bat
.venv\Scripts\python scripts\bench_cli_context.py --config config.yaml
```
결과의 `context_total` 최소 프로필을 `cli.flags_profile` 에 반영(현재 `minimal`).

### 2. 건당 처리 시간 (실제 건, 사용자 수행)
`run.bat` 로 5건 처리하며 검토 화면의 "N초 경과" 표시 또는 `logs/app.log` 의 `fetch+analyze done in Xs` 를 기록한다.

| 건 | judge 시간 | revise 시간 | 합계 |
|---|---|---|---|
| 1 | | | |
| 2 | | | |
| 3 | | | |
| 4 | | | |
| 5 | | | |

### 3. 이력 탭 토큰 집계
20건 처리 후 이력 탭 요약의 입력·출력 토큰과 추정 비용을 기록(NFR C-5).

## Performance Optimization
처리 시간이 180초를 자주 넘으면:
1. `effort.judge` 를 `low` 로 낮춘다(판정 품질 확인 후)
2. `image_max_side` 를 1200 으로 낮춘다(비전 토큰 약 40% 감소)
3. `cli.max_turns` 가 4 로 충분한지 로그의 `num_turns` 로 확인
