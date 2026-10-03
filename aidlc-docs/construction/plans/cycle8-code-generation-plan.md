# Cycle 8 Code Generation Plan

## 설계 결정
- D1 `config.RevisionRules{allow_turn_drop: bool=False}`, `AppConfig.revision_rules`. `ReviseStage.run`: allow_turn_drop=False 면 raw 의 drop 을 모두 무시(raw_to_draft 에 `allow_drop` 인자). revise 프롬프트 규칙 12 를 조건부 문구로("턴 삭제는 허용된 경우에만")→ `build_revise_system`/프롬프트에 allow_turn_drop 반영: 간단히 사용자 프롬프트 메타 블록에 "턴 삭제 허용: 아니오(모든 턴 유지, 내용만 수정)" 한 줄 추가
- D2 `validate_final(final, draft=None)`: draft 가 주어지면 초안에 내용이 있던 턴이 최종안에서 user·assistant 모두 비면 "대화 N턴을 삭제할 수 없습니다" 추가. SubmitService.approve 는 draft 전달. 프론트 validate 도 동일(store.item.draft 참조)
- D3 `EditService.revert_field(field)`: `cur.final.set_field(field, cur.draft.get_field(field))`, diffs 재계산, edited_by_user 는 diff 가 하나라도 남아 있으면 유지. `POST /actions/revert-field`. 프론트: fieldHTML/turnHTML/renderInstruction 의 변경된 항목 머리글에 `<button class="btn tiny" data-revert="field">초안으로</button>`
- D4 `.gitignore` 에 `guide/`, `*.zip`(dist 는 이미). `git init`, 첫 커밋(Co-Authored-By 포함). 원격은 Q1 답변 후 `git remote add origin … && git push -u origin main`
- D5 `run.bat`: `:update` 라벨 — `if "%1"=="--no-update"` 건너뜀; `where git` + `.git` 존재 시 `git pull --ff-only` → 출력에 "Already up to date" 없으면 `pip install -q -e .`; 실패 시 echo 경고. ASCII·goto 구조 유지(한글 금지)
- D6 README: 설치(git clone), 업데이트 자동, zip 은 보조. operations.md

## 생성 단계
- [x] Step 1 config/revise/prompts + tests(revise drop 무시, 기본값 false)
- [x] Step 2 services(validate draft 비교, revert_field)/web/app.py + tests(services, web)
- [x] Step 3 app.js/style.css 항목별 초안 버튼, node --check
- [x] Step 4 .gitignore, run.bat, README, git init + 첫 커밋 (push 는 Q1 답변 후)
