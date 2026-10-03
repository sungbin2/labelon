# Operations (Placeholder)

AI-DLC 규칙상 Operations 단계는 플레이스홀더다. 이 도구는 사용자 PC 에서 `run.bat` 으로 실행하는 로컬 도구라 배포·모니터링 인프라가 없다. 운영에 필요한 내용은 아래 문서로 대신한다.

| 주제 | 위치 |
|---|---|
| 설치·실행·문제 해결 | `README.md` |
| 첫 실제 제출 검증 절차 | `docs/manual-checklist.md`, `aidlc-docs/construction/build-and-test/e2e-test-instructions.md` |
| 성능·사용량 기록 | `aidlc-docs/construction/build-and-test/performance-test-instructions.md` |
| LabelOn 화면 변경 대응 | `scripts/capture_job_page.py` 로 HTML 캡처 → `src/labelon_reviewer/labelon/parser.py` 의 `FieldLocatorMap` 조정 → `tests/fixtures/make_job_page_sample.py` 갱신 |
| Claude Code 업데이트 대응 | `claude -p` 동작이 바뀌면(`--bare` 기본화 등) `config.yaml` `model_backend: anthropic_sdk` 로 전환하고 `pip install anthropic` |
| 로그 | `logs/app.log` (회전 5MB x 5) |
| 데이터 | `data/history.db`(이력, 무기한), `data/cache`·`data/resized`(이미지, 7일) |

## 운영 시작 체크
1. `run.bat` → Chrome 창에서 LabelOn 로그인
2. `docs/manual-checklist.md` 0~3절로 실제 1건 승인 제출 검증. 모달 문구·selector 가 다르면 `FieldLocatorMap` 수정
3. 20건 처리 후 이력 탭의 토큰·시간을 기록하고 `effort`·`image_max_side` 조정
4. 검수 반려가 발생하면 이력 탭에서 제출 payload 를 확인하고 프롬프트(`prompts/*.md`) 또는 임계값을 조정


## 사이클 2 (2026-09-28) 운영 메모
- 데이터셋은 검토 화면 헤더 드롭다운에서 선택한다. 목록은 LabelOn "진행중인 작업" 중 UC-LE(AH25) 타입만 자동으로 읽으며, 마지막 선택은 `data/ui-state.json` 에 저장된다
- 새 데이터셋이 배정되면 "새로고침" 버튼으로 목록을 갱신한다. 목록을 읽지 못하면 `config.yaml` 의 `dataset_id` 가 폴백이다
- 프로젝트 홈 구조가 바뀌어 목록이 비면 `tests/fixtures/make_project_home_sample.py` 를 새 구조로 갱신하고 `labelon/parser.py` 의 `parse_dataset_list` 정규식을 조정한다
- `guide/` 폴더의 검수 가이드는 사이클 3 에서 반영했다(아래 참조)


## 사이클 3 (2026-09-28) 운영 메모 (v0.3.0)
- 검수 가이드(guide/) 규칙이 프롬프트와 판정 로직에 들어갔다. 정리본은 `aidlc-docs/inception/requirements/cycle3-guide-notes.md`
- 불가 후보 기준은 `config.yaml` 의 `threshold`(점수), `impossible_rules.max_false_facts`(거짓 팩트 개수), `impossible_rules.max_inconsistent_fields`(불일치 필드 개수)로 조정한다. 불가가 너무 잦거나 드물면 이 값을 먼저 조정한다
- 아키타입 정정은 6종 템플릿(`config.yaml` `archetype_templates`)으로 task 를 다시 만든다. 검토 화면 Instruction 패널의 "되돌리기"로 원본으로 돌아갈 수 있다
- 턴 삭제는 모델 제안이며 첫 턴은 삭제되지 않는다. 제출 시 삭제된 턴의 textarea 를 비운다
- 전화번호 제거는 `text_rules.remove_phone_numbers` 로 끌 수 있다
- 가이드의 이미지 슬라이드(불가 예시)는 사이클 4 에서 반영했다(아래 참조). 원본은 `guide/검수가이드_0911.pdf`
- 실제 1건 E2E 는 `aidlc-docs/construction/build-and-test/cycle3-build-and-test-summary.md` 하단 절차대로 사용자가 수행한다

## 사이클 4 (2026-09-28) 운영 메모 (v0.4.0)
- 검수 가이드 이미지 슬라이드(오류 예시 1~3, 불가 예시 1~7)를 judge 프롬프트와 판정 규칙에 반영했다. 정리본은 `aidlc-docs/inception/requirements/cycle4-guide-notes.md`
- 불가 후보 사유가 9종으로 늘었다(환경 충돌, 오인식 전파, 페르소나 불가 안내, 위험 행위 권고 추가). 이 4종은 모델 판정 기반이라 설정 스위치가 없다. 과잉 판정이 잦으면 `prompts/judge_system.md` 의 "불가 예시" 절 문구를 좁힌다
- 아키타입이 사진 환경과 충돌하면(실외 도로에 실내탐색 등) 불가가 우선이고 아키타입 정정 제안은 무시된다(경고 표시). 라벨만 틀린 경우(음식 → 쇼핑)만 정정된다
- 텍스트 오류(오탈자·추측·숫자 표기)는 판정 패널 목록으로 보이고 수정안에 반영된다. 목록의 필드를 클릭하면 해당 textarea 로 이동한다
- 실제 1건 E2E 는 `aidlc-docs/construction/build-and-test/cycle4-build-and-test-summary.md` 하단 절차대로 사용자가 수행한다

## Hotfix 0.4.1 / 0.4.2 (2026-09-29)
- 데이터셋 목록이 비는 결함 2건 수정(탭 버튼 data-id 오매칭, onclick 인용부호 &#39; 엔티티). 프로젝트 홈 구조를 다시 확인할 때는 렌더링된 DOM 이 아니라 **원본 HTML 전체**(탭 버튼 포함)로 픽스처를 만든다

## Hotfix 0.4.3 (2026-09-29)
- 건수 집계 기준 변경: 오늘/누적 = 승인·불가 제출 완료 건(PC 로컬 날짜 기준). 건너뜀·만료·미완료·가져옴은 따로 표시. 저장 시각은 계속 UTC

## 사이클 5 (2026-09-30) 운영 메모 (v0.5.0)
- 일상지원 Task 템플릿이 바뀌었다. 옛 문장 초안은 `legacy_archetype_templates` 로 일치 인정. LabelOn 이 다른 템플릿을 또 바꾸면 `config.yaml` 의 `archetype_templates` 를 새 문장으로 바꾸고 옛 문장을 `legacy_archetype_templates` 에 추가한다
- 두 방향 결합(앞 왼쪽)은 정규식 검출. 도움 요청·가전조작 가구 규칙은 프롬프트 기반

## 사이클 6 (2026-10-01) 운영 메모 (v0.6.0)
- 대화의 질문(user)도 화면에서 편집할 수 있다(모델은 바꾸지 않음). 편집 저장 지연은 `config.yaml` `ui.edit_delay_ms`(기본 1500ms). 편집 중에는 초안 패널을 다시 그리지 않으므로 다른 패널(판정·경고)만 갱신되고, 칸을 벗어나면 최신 상태로 다시 그린다
- 0.6.1: 정적 파일 캐시 무효화(`?v=버전`, no-cache). 화면 동작이 바뀐 것 같지 않으면 Ctrl+F5 로 강제 새로고침
- 0.6.2: 서버 재시작(버전 변경) 시 열려 있던 화면이 자동 새로고침. 그래도 옛 화면이면 F5

## 사이클 7 (2026-10-02) 운영 메모 (v0.7.0)
- Instruction(아키타입·페르소나·태스크)을 화면에서 편집할 수 있다. "템플릿으로 Task 채우기" 는 `config.yaml` `archetype_templates` 를 쓴다
- 건수(오늘/누적)는 승인 제출만 센다. 불가·반환은 보조 표시. 제출 직후 갱신
- 세션 만료 시 Chrome 에서 재로그인만 하면 5초 간격 감시가 자동 복구한다. 복구가 안 되면 `logs/app.log` 의 `re-login detected` 유무 확인
- "다시 판독(Alt+S)" 은 같은 건을 다시 판정·수정(모델 호출 2회). LabelOn 반환은 작은 "반환" 버튼

## 사이클 8 (2026-10-03) 운영 메모 (v0.8.0)
- 배포는 git 저장소(https://github.com/sungbin2/labelon.git, private)로 한다. `run.bat` 이 시작 시 `git pull --ff-only` 로 갱신. 새 PC 는 `git clone` → `setup.bat`
- 저장소에 올리지 않는 것: `config.yaml`, `.profile/`, `data/`, `logs/`, `guide/`(회사 자료), zip. 감사 로그에는 계정 이메일이 있으므로 저장소는 private 유지
- 모델 턴 삭제는 기본 금지(`revision_rules.allow_turn_drop: false`). 항목별 "초안으로" 되돌리기. 초안에 있던 턴을 비우면 승인 차단
- 코드 변경 후 배포: 커밋 → push. 사용자 PC 는 다음 run.bat 에서 자동 반영
