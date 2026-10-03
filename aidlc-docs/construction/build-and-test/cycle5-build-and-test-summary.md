# Cycle 5 Build and Test Summary - 검수자 피드백 반영

작성일: 2026-09-30. 기존 지침·요약은 유효. 사이클 5 추가분만 기록.

## Build Status
- **Build**: Success — `labelon-reviewer 0.5.0` (0.4.3 → 0.5.0)
- **Lint**: ruff 통과, `node --check app.js` 통과
- **배포물**: `dist/labelon-reviewer-0.5.0.zip`

## Test Execution Summary
### Unit Tests
- **Total**: 114 (사이클 4 hotfix 후 111, +3). **Passed** 114. **Coverage** 79%
- **신규**: 레거시·새 일상지원 템플릿 일치와 정정 Task 새 문장, 방향 결합 정규식, 판정 결정론 검출·모델 보고 중복 제거

### Integration Tests
| 시나리오 | 결과 |
|---|---|
| `config.yaml` 로드(새 템플릿·레거시 목록) | Pass |
| 서버 스모크(`--no-chrome`): `/config`, `/history/summary`(제출 기준 집계), 타 Origin 403, shutdown | Pass |
| 가전조작 + 가구 사진에서 불가·정정 제안 없음 | Pending (사용자 E2E) |
| 사진에 없는 어른 도움 요청 턴 → 불일치·신호 확인 안내로 수정 | Pending (사용자 E2E) |
| "앞 왼쪽" 포함 초안 → "방향" 라벨, 수정안에서 한 방향 | Pending (사용자 E2E) |

## Overall Status
- **Build**: Success / **All Tests**: Pass (자동 범위) / **Ready for Operations**: Yes

## 사용자 확인 절차 (E2E)
1. `run.bat` 재시작 → 버전 0.5.0
2. 일상지원 건(옛 문장·새 문장 모두)에서 Instruction 경고가 없는지
3. 가전조작 아키타입에 가구 사진인 건: 불가 사유·정정 제안이 없는지
4. 횡단보도 건에서 "어른에게 도와달라고 해" 발화: 어른이 사진에 없으면 불일치 표시와 수정안 확인
5. "앞 왼쪽" 같은 표현이 있는 건: 텍스트 오류 "방향" 표시와 수정안
