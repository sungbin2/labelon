# Cycle 4 Requirements: 검수 가이드 이미지 슬라이드 반영

작성일: 2026-09-28. 깊이: Standard. 기반: cycle4-guide-notes.md(N1~N8), 사이클 3 요구사항. 답변: 질문 4개 모두 A.

## 1. Intent Analysis
| 항목 | 내용 |
|---|---|
| User Request | DRM 없는 검수 가이드 PDF(23쪽)의 오류·불가 예시를 도구의 판정·수정 기준에 반영 |
| Request Type | Enhancement (Brownfield) |
| Scope | Multiple Components: judge 프롬프트·스키마·판정 규칙, revise 프롬프트, 도메인, 화면 판정 패널 |
| Complexity | Moderate (사이클 3 구조 위에 판정 필드·불가 사유 추가. 제출·서비스 흐름 변경 없음) |

## 2. 기능 요구사항

### FR-C4-1. 아키타입-이미지 환경 충돌은 불가 (N8, Q1=A)
- judge 출력에 `archetype_fits_environment: bool` 추가. 사진의 환경(실내/실외, 도로/매장/주방 등)에서 현재 Archetype 의 task 를 수행하는 것이 애초에 불가능하면 false (예: 실외 도로 사진에 실내탐색·가전조작·음식·쇼핑·일상지원)
- false 이면 불가 후보, 사유 "아키타입이 이미지 환경과 맞지 않음: (모델 사유)". 이 경우 `archetype_suggestion` 정정은 적용하지 않는다(불가가 우선)
- true 이면 사이클 3 대로 라벨 불일치(QA 는 사진과 맞음)만 정정 제안

### FR-C4-2. 새 불가 사유 3종 (N4~N7, Q2=A)
- judge 출력 추가: `core_error_propagated: bool`(핵심 물체 오인식·팩트 오해가 CoT·QA 전반에 전파), `persona_infeasible_guidance: bool`(페르소나가 수행할 수 없는 확인·행동 요구, 예: 시각장애인에게 "보이면"), `unsafe_guidance: bool`(사용자를 위험에 빠뜨리는 행위 권고, 예: 횡단보도 없는 도로 횡단). 각각 `*_reason: str`
- true 이면 불가 후보 + `impossible_reasons` 에 사유 추가. 판정 패널 불가 사유 목록에 표시

### FR-C4-3. 텍스트 오류 판정·수정 (N1~N3, Q3=A)
- judge 출력에 `text_issues: list[{field, kind: "typo"|"speculation"|"number", wrong, correct, note}]` 추가. kind: typo = 오탈자·맞춤법, speculation = 사진으로 확인할 수 없는 주관적 추측 문장, number = 이미지의 숫자를 한글 수사로 적음("열세 번" → "13번")
- text_issues 가 비어 있지 않으면 needs_revision=True (불가가 아닐 때)
- revise 프롬프트 규칙 추가: 판정의 text_issues 를 반영해 오탈자 수정, 이미지 속 숫자는 숫자 그대로, 추측 문장은 삭제하거나 사진에서 확인되는 사실로 교체. 판정 블록(build_revise_user)에 text_issues 목록 포함
- 판정 패널에 text_issues 목록(필드, 종류, 잘못 → 바름) 표시

### FR-C4-4. QA 검수 기준 문구 (5~7쪽, Q4=A)
- judge 프롬프트에 "QA 는 단순 설명형이 아닌 상황 맥락·Facts·CoT 기반 페르소나 맞춤형 멀티턴" 기준을 persona_task_fit·qa_matches_cot3 판단 근거로 추가. 연관 QA 목록은 참고용 유지(도구가 검수하지 않음)
- 불가 예시 1~7 을 judge 프롬프트에 짧게 열거해 판정 기준으로 제공

### FR-C4-5. 문서·설정
- README 판정 항목 설명, domain-rules 가이드 절, business-rules 개정 메모(BR-05 불가 사유 추가)
- 설정 변경 없음(새 규칙은 모델 판정 기반. 끄고 켜는 스위치는 두지 않음)

## 3. 비기능·제약
- 모델 호출 수 불변. judge 프롬프트·스키마 확장으로 호출당 입력 토큰 소폭 증가
- 기존 테스트 102개 유지. 신규: 불가 사유 4종(환경 충돌·전파·페르소나 불가 안내·위험 권고), 환경 충돌 시 정정 미적용, text_issues → needs_revision, 누락 필드 보정(기본값: 모두 문제 없음)
- 스키마 필드 누락 시 기본값은 "문제 없음"(false/true 적절히)으로 보정해 구버전 출력에도 동작

## 4. 인수 기준
- AC-C4-1 archetype_fits_environment=false 이면 불가 후보·사유 표시, archetype_suggestion 이 있어도 Instruction 정정이 적용되지 않는다
- AC-C4-2 core_error_propagated / persona_infeasible_guidance / unsafe_guidance 중 하나라도 true 이면 불가 후보이고 사유 목록에 각 문구가 들어간다
- AC-C4-3 text_issues 에 항목이 있고 다른 문제가 없으면 needs_revision=True 이며 revise 사용자 프롬프트에 목록이 포함된다
- AC-C4-4 text_issues 가 비고 다른 문제도 없으면 사이클 3 과 동일하게 수정 없이 승인 대기
- AC-C4-5 판정 패널에 새 불가 사유와 text_issues 가 표시된다
