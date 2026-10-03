# Cycle 8 Build and Test Summary

작성일: 2026-10-03.

## Build Status
- **Build**: Success — `labelon-reviewer 0.8.0`. ruff·node check 통과. 배포: git 저장소 https://github.com/sungbin2/labelon.git (보조 zip `dist/labelon-reviewer-0.8.0.zip`)

## Test Execution Summary
- **Unit**: 119 passed (+2), 커버리지 79%. 신규: drop 기본 무시·허용 시 삭제, 턴 비움 차단, revert_field(항목만 되돌리기·edited 플래그), `/actions/revert-field`
- **Pending (사용자)**: 항목별 "초안으로" 버튼 동작, 턴을 비웠을 때 승인 차단 문구, `run.bat` 자동 업데이트(다음 push 후 재시작 시 "updated" 메시지)

## Overall Status
- **Build**: Success / **All Tests**: Pass (자동 범위) / **Ready for Operations**: Yes

## 사용자 확인 절차
1. `run.bat` 재시작 → "checking for updates" 메시지 → 버전 0.8.0
2. 항목을 고친 뒤 머리글의 "초안으로" 버튼 → 그 항목만 초안으로, 다른 편집은 유지
3. 턴의 질문·답변을 모두 지우면 승인 버튼이 비활성(툴팁에 "삭제할 수 없습니다")
4. 다른 PC: `git clone https://github.com/sungbin2/labelon.git labelon-reviewer` → `setup.bat` → `run.bat`
