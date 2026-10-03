# Cycle 10 Requirements: 불가 후보 건에도 수정안 생성

작성일: 2026-10-03. 깊이: Minimal(요청이 명확해 질문 없이 진행). 실행: Code Generation → Build and Test.

| 항목 | 내용 |
|---|---|
| User Request | "불가건이라도 수정사항은 검토하여 화면에 반영될수 있도록 해주세요." |
| 변경 | BR-05 의 "불가 후보는 2단계 수정 생략" 을 폐지. `revision_rules.revise_impossible`(기본 true)이면 불가 후보라도 수정 조건이 있으면 ReviseStage 실행 → 수정안·diff 표시. 불가 후보 알림에 "수정안도 생성됨" 문구 |
| 영향 | 불가 후보 건마다 모델 호출 1회(revise) 추가. 사람은 고쳐서 승인하거나 불가로 제출 |
| 인수 기준 | AC-C10-1 점수 ≤ 임계값·거짓 팩트 다수 건에서 needs_revision=True 이고 수정안이 생성된다. AC-C10-2 설정 false 면 기존처럼 생략. AC-C10-3 기존 테스트 유지(121) |
