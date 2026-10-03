# Cycle 3 Execution Plan - 검수 가이드 반영

작성일: 2026-09-28. 유닛: labelon-ucle-reviewer

## Detailed Analysis Summary

### Transformation Scope (Brownfield)
- **Transformation Type**: 기존 컴포넌트 경계 안의 판정·수정 로직 확장
- **Primary Changes**: judge/revise 스키마·프롬프트 확장, JudgeStage 불가 규칙·전화번호 검사·needs_revision 조건, ReviseStage 아키타입 정정(템플릿 치환)·턴 삭제 제약, Submitter instruction textarea·빈 턴 채움, 프론트엔드 판정 패널·Instruction diff·삭제 턴, 설정 2항목
- **Related Components**: C-01 Config, C-05 RuleChecker(템플릿 생성 유틸), C-07 Judge, C-08 Revise, C-09 Diff(instruction 필드), C-11 Submitter, C-14 Frontend, prompts, schemas, domain

### Change Impact Assessment
- **User-facing**: Yes. 판정 패널 항목 추가, Instruction diff, 삭제 턴 배지, 승인 확인 문구
- **Structural**: No
- **Data model**: JudgeResult 필드 추가(archetype_suggestion, impossible_reasons, qa_matches_cot3, phone_numbers), DialogueTurn 삭제는 최종안 턴 목록 축소로 표현. DB 스키마 변경 없음(JSON 컬럼)
- **API**: 스냅샷 필드 추가만
- **NFR**: 모델 호출 수 불변. 프롬프트 길이 소폭 증가

### Risk Assessment
- **Risk Level**: Medium. Instruction 정정과 턴 삭제는 제출 내용에 큰 변화를 주므로 사람 확인 단계의 표시가 명확해야 한다. 잘못된 아키타입 제안은 diff 로 드러나며 승인 전 되돌릴 수 있다
- **Rollback**: Easy (코드 되돌리기)
- **Testing**: Moderate (Fake 모델 출력으로 정정·삭제·불가 규칙 경로 검증, 실제 건 1회 수동)

## Workflow
```
INCEPTION: Workspace Detection COMPLETED / Reverse Engineering SKIP(최신) / Requirements COMPLETED / User Stories SKIP /
           Workflow Planning IN PROGRESS / Application Design SKIP / Units Generation SKIP
CONSTRUCTION: Functional Design SKIP(설계 결정은 코드 계획에 명시) / NFR Requirements SKIP / NFR Design SKIP / Infrastructure SKIP /
           Code Generation EXECUTE / Build and Test EXECUTE
```

## Phases to Execute
- [x] Workspace Detection, Requirements Analysis (COMPLETED); User Stories, Reverse Engineering (SKIPPED)
- [ ] Application Design - SKIP — 새 컴포넌트 없음
- [ ] Units Generation - SKIP — 단일 유닛
- [ ] Functional Design - SKIP — 판정 조건·템플릿 치환·턴 삭제 제약은 코드 생성 계획의 설계 결정 절에 명시
- [ ] NFR Requirements / NFR Design / Infrastructure Design - SKIP
- [ ] Code Generation - EXECUTE
- [ ] Build and Test - EXECUTE (pytest·ruff, 서버 스모크, 사용자 실제 1건 확인)

## Success Criteria
- AC-C3-1~6 충족, 기존 84개 테스트 유지
- 실제 건에서 판정 패널에 새 항목이 표시되고 제출이 정상
