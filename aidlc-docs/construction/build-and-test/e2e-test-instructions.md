# End-to-End Test Instructions

## Purpose
사용자 여정(US-1 → US-8)을 실제 LabelOn 과 실제 모델로 처음부터 끝까지 검증한다. LabelOn 로그인이 필요하므로 사용자가 수행하며, 실제 제출이 발생한다.

## 절차
`docs/manual-checklist.md` 를 그대로 따른다. 절별 대응 스토리:

| 절 | 스토리 | 핵심 확인 |
|---|---|---|
| 0 준비 | US-1 | 로그인 감지, 세션 보존, 자격증명 파일 없음 |
| 1 벤치 | NFR C-3 | 수행 완료(minimal 확정). 재실행은 선택 |
| 2 가져오기·판정 | US-2, US-3 | 3분 이내 표시, 팩트 배지, 점수, 카운트다운 정확도 |
| 3 편집·승인 | US-4, US-5 | diff, 되돌리기, 승인 전 LabelOn 무변화, 제출 성공, 작업내역 +1 |
| 4 불가 제출 | US-6 | 제안 사유, 빈 사유 거부, [작업불가] 모달 |
| 5 건너뛰기 | US-7 | 반환 후 준비됨 |
| 6 제한시간 | US-7 | 10분 경고, 만료 처리 |
| 7 장애 | 복원 패턴 | 브라우저 닫힘, 서버 재시작 미완료 표시, 모델 실패 폴백 |
| 8 사용량 | NFR C-5 | 20건 후 토큰·비용 기록 |

## 첫 실제 제출 시 특별 확인 (code-summary.md 4절 미검증 항목)
1. 승인 클릭 후 Chrome 창에서 textarea 가 채워지는지 눈으로 확인 (React 상태 반영)
2. 확인 모달의 버튼 이름이 "확인"인지 (다르면 `parser.FieldLocatorMap.confirm_button_name` 수정)
3. 결과 모달 텍스트에 "저장되었습니다" 가 포함되는지 (다르면 `success_text` 수정)
4. 불가 제출 시 사유 입력란이 나타나는지, placeholder 에 "불가 사유" 가 포함되는지 (다르면 `impossible_reason_textarea` 수정)
5. 카운트다운이 LabelOn 화면의 제한시간과 맞는지 (`labelon.server_tz_offset_hours` 조정)

## 결과 기록
`docs/manual-checklist.md` 하단 표에 일시·결과·메모를 남기고, 실패 항목은 이 문서에 "발견 사항"으로 추가한다.

## 발견 사항
- 2026-09-23 11:53 첫 불가 제출: 도구가 결과 모달을 잘못 감지("불가" 글자 매칭)해 SUBMIT_FAILED 로 기록. 실제 서버 반영 여부 불명(작업내역에 688 행 없음). → Submitter 를 LabelOn 공통 모달 id(#commonmodal2/#commonmodal1) 기반으로 재작성.
- 2026-09-23 11:50 revise(fable-5-1) 가 stop_reason=refusal 로 3회 거부 → ModelRefused 도입, 폴백 모델(sonnet-5) 1회 시도, 프롬프트에 데이터셋 목적 문구 추가.
- 사용자 요청으로 불가 사유 공백 허용. 플랫폼이 사유를 요구하면 알림 모달 문구가 실패 사유로 기록됨.
- 2026-09-23 두 번째 건: Facts 가 6개인 초안에서 "facts 개수 6 (기대 5)" 로 제출 거부 → Facts 개수를 초안 기준 가변으로 변경(점수 60점/n 균등 배분).
- 재검증 필요: 불가 제출 1건(사유 공백), 승인 제출 1건, 결과 모달 문구 "저장되었습니다" 확인, Facts 6개 건의 diff·제출.
