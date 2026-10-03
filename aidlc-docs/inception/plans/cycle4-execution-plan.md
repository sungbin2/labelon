# Cycle 4 Execution Plan - 검수 가이드 이미지 슬라이드 반영

작성일: 2026-09-28. 유닛: labelon-ucle-reviewer. 요구사항: cycle4-requirements.md (FR-C4-1~5, AC-C4-1~5)

## Detailed Analysis Summary

### Transformation Scope (Brownfield)
- **Transformation Type**: 기존 컴포넌트 경계 안의 판정 기준 확장(사이클 3 구조 재사용)
- **Primary Changes**: judge 스키마·프롬프트에 판정 필드 5종(archetype_fits_environment, core_error_propagated, persona_infeasible_guidance, unsafe_guidance, text_issues) 추가, JudgeStage 불가 규칙 4종·needs_revision 조건(text_issues)·환경 충돌 시 정정 미적용, revise 프롬프트·사용자 프롬프트에 text_issues 반영 규칙, 프론트엔드 판정 패널, 문서
- **Related Components**: C-07 Judge, C-08 Revise(프롬프트만), C-14 Frontend, prompts, schemas, domain. Config·Submitter·Services 변경 없음

### Change Impact Assessment
- **User-facing**: Yes. 판정 패널에 불가 사유·텍스트 오류 목록 추가. 승인·제출 흐름 불변
- **Structural**: No
- **Data model**: JudgeResult 필드 추가(bool 4종 + reason, TextIssue 목록). DB 스키마 변경 없음(JSON 컬럼)
- **API**: 스냅샷 필드 추가만
- **NFR**: 모델 호출 수 불변. judge 프롬프트 길이 증가(불가 예시 7종 열거)

### Risk Assessment
- **Risk Level**: Low-Medium. 불가 후보가 늘어나 모델이 과잉 판정하면 수정 단계가 생략되는 건이 많아질 수 있다. 사람이 화면에서 불가 대신 편집·승인할 수 있고, 사유가 목록으로 보이므로 과잉 판정을 바로 알 수 있다
- **Rollback**: Easy (코드 되돌리기. 스키마 누락 필드는 기본값 보정)
- **Testing**: Moderate (Fake 모델 출력으로 불가 사유 4종·정정 미적용·text_issues 경로 검증, 실제 건 1회 수동)

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
- [ ] Functional Design - SKIP — 판정 필드·불가 규칙·text_issues 처리는 코드 생성 계획의 설계 결정 절에 명시
- [ ] NFR Requirements / NFR Design / Infrastructure Design - SKIP
- [ ] Code Generation - EXECUTE
- [ ] Build and Test - EXECUTE (pytest·ruff, 서버 스모크, 사용자 실제 1건 확인)

## Success Criteria
- AC-C4-1~5 충족, 기존 102개 테스트 유지
- 실제 건에서 판정 패널에 새 불가 사유·텍스트 오류 목록이 표시되고 제출이 정상
