# Cycle 6 Code Generation Plan - QA 질문 편집 · 편집 반영 지연

## 설계 결정
- D1 `domain.Draft.get_field/set_field/editable_fields` 에 `turn_N_user`. `diff.compute_diff` 는 턴마다 `turn_N_user` 와 `turn_N_assistant` 두 항목(user 가 같으면 changed=False)
- D2 `services.validate_final`: assistant 가 있고 user 가 비면 "대화 N턴 user 가 비어 있습니다". 프론트 validate 도 동일
- D3 `config.UiConfig{edit_delay_ms:int=1500 (300~10000)}`, `AppConfig.ui`, `ConfigService.public()` 에 `edit_delay_ms`
- D4 app.js: 턴 카드에서 user 를 `<textarea data-field="turn_N_user">` 로(기존 읽기 전용 표시 대체), assistant 는 그대로. 삭제 턴 표시는 유지. `fieldLabel` 에 user 라벨
- D5 app.js 편집 UX: `store.pendingItem`. `renderAll` 은 focusField 가 있으면 renderDraft 를 건너뛰고 pendingItem 에 보관. blur 시 즉시 저장 + pendingItem 으로 renderDraft. compositionstart → `store.composing=true`, compositionend → false 후 지연 저장. 지연 = `store.config.edit_delay_ms || 1500`. 저장 응답 후에도 focus 중이면 다시 그리지 않음
- D6 문서: README(편집 지연 설정), business-rules BR-21 메모(user 는 사람만 편집), cycle6-code-summary.md

## 생성 단계
- [x] Step 1 `domain.py`, `diff.py`, `services.py`(validate_final), `tests/test_domain.py`·`test_diff.py`·`test_services.py`(user 편집·diff·검증), `tests/test_submitter.py`(payload turn_1_user 수정값)
- [x] Step 2 `config.py`, `config.example.yaml`, `config.yaml`, `services.py`(public), `tests/test_web.py`(/config edit_delay_ms, PUT turn_1_user)
- [x] Step 3 `web/static/app.js`, `style.css`, `node --check`
- [x] Step 4 문서
