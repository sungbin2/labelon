"""프롬프트 로더와 user 프롬프트 조립 (고정 지시문 → 초안·QA → 이미지 경로)."""

from __future__ import annotations

from pathlib import Path

from ..config import AppConfig
from ..domain import Draft, Instruction, JudgeResult, SourceItem

_DIR = Path(__file__).parent


def system_prompt_path(name: str) -> Path:
    return _DIR / f"{name}_system.md"


def load_system(name: str) -> str:
    return system_prompt_path(name).read_text(encoding="utf-8")


def _draft_block(draft: Draft) -> str:
    lines = [
        "## 초안",
        f"- Instruction.archetype: {draft.instruction.archetype}",
        f"- Instruction.persona: {draft.instruction.persona}",
        f"- Instruction.task: {draft.instruction.task}",
        "",
        f"### Scene\n{draft.scene}",
        "",
        "### Facts",
    ]
    for i, f in enumerate(draft.facts):
        lines.append(f"{i}. {f}")
    lines += ["", f"### CoT\n- cot1: {draft.cot1}\n- cot2: {draft.cot2}\n- cot3: {draft.cot3}", "", "### 대화"]
    ctx = draft.dialogue.context or {}
    if ctx:
        lines.append(f"- context.user_type: {ctx.get('user_type', '')}")
        lines.append(f"- context.situation: {ctx.get('situation', '')}")
        lines.append(f"- context.priority: {ctx.get('priority', '')}")
    for t in draft.dialogue.active_turns():
        lines.append(f"- turn {t.turn} user: {t.user}")
        lines.append(f"- turn {t.turn} assistant: {t.assistant}")
    return "\n".join(lines)


def _meta_block(item: SourceItem, config: AppConfig, persona: str = "") -> str:
    qa = "\n".join(f"- Q: {q.question} / A: {q.answer}" for q in item.related_qa) or "- (없음)"
    return (
        "## 메타데이터\n"
        f"- 데이터셋: {item.dataset_name or item.dataset_id}\n"
        f"- 이 건의 페르소나(초안 기준): {persona or config.persona}\n"
        f"- category: {item.category}\n- weather: {item.weather}\n- detectedObject: {item.detected_object}\n\n"
        f"## 연관 QA (참고)\n{qa}"
    )


def build_judge_user(item: SourceItem, draft: Draft, image_path: str, config: AppConfig) -> str:
    return (
        "아래 초안을 사진과 대조해 판정하세요. 먼저 Read 도구로 사진 파일을 열어 직접 확인한 뒤, 요구된 JSON 스키마로만 답하세요.\n\n"
        f"{_meta_block(item, config, draft.instruction.persona)}\n\n{_draft_block(draft)}\n\n"
        f"## 사진 파일 (Read 도구로 열기)\n{image_path}\n"
    )


def _judge_block(judge: JudgeResult) -> str:
    lines = ["## 판정 결과"]
    if not judge.qa_matches_cot3:
        lines.append("- 대화가 CoT 3단계와 맞지 않음")
    for fld in judge.field_verdicts:
        if fld.field.startswith("cot") and not fld.role_fits:
            lines.append(f"- {fld.field}: 단계 역할에 맞지 않음 — {fld.note}")
        if fld.field.startswith("turn_") and fld.beyond_cot3:
            lines.append(f"- {fld.field.replace('turn_', 'turn ')}: CoT 3단계 범위를 넘는 추론 → 삭제(drop) 또는 앞 턴에 병합 검토 — {fld.note}")
    if judge.phone_numbers:
        lines.append("- 전화번호 발견(삭제 필요): " + ", ".join(judge.phone_numbers))
    for ti in judge.text_issues:
        kind = {"typo": "오탈자", "speculation": "추측", "number": "숫자 표기"}.get(ti.kind, ti.kind)
        lines.append(f"- 텍스트 오류 {ti.field} ({kind}): '{ti.wrong}' → '{ti.correct}'")
    for fv in judge.fact_verdicts:
        if fv.verdict.value != "TRUE":
            lines.append(f"- fact_{fv.index + 1}: {fv.verdict.value} — {fv.evidence}")
    for fld in judge.field_verdicts:
        if not fld.consistent:
            lines.append(f"- {fld.field}: 불일치 — {fld.note}")
    fit = judge.persona_task_fit
    if not (fit.cot_fits and fit.dialogue_fits):
        lines.append(f"- persona/task 적합성: cot_fits={fit.cot_fits}, dialogue_fits={fit.dialogue_fits} — {fit.note}")
    if judge.missing_in_image:
        lines.append("- 사진에 없는 것: " + ", ".join(judge.missing_in_image))
    if len(lines) == 1:
        lines.append("- (표시된 문제 없음)")
    return "\n".join(lines)


def build_revise_user(
    item: SourceItem, draft: Draft, judge: JudgeResult, image_path: str, config: AppConfig, corrected: Instruction | None = None
) -> str:
    priority = (draft.dialogue.context or {}).get("priority", "")
    corr = ""
    if corrected is not None:
        corr = (
            "## 정정된 Instruction (도구가 템플릿으로 정정함. CoT·assistant 를 이 task 목적에 맞게 조정)\n"
            f"- 이전 archetype: {draft.instruction.archetype} → 정정: {corrected.archetype}\n- 정정 task: {corrected.task}\n\n"
        )
    drop_rule = (
        "## 턴 삭제: 허용 (CoT 3단계 범위 밖의 턴만 drop=true)\n\n" if config.revision_rules.allow_turn_drop
        else "## 턴 삭제: 금지. 어떤 턴도 drop 하지 말고 모든 턴을 유지한 채 내용만 고치세요. CoT 3단계 범위를 넘는 턴은 사진에 있는 상황으로 바꿔 씁니다.\n\n"
    )
    return (
        corr + drop_rule +
        "아래 초안에서 판정 결과에 표시된 부분만 사진에 근거해 최소한으로 고치세요. 먼저 Read 도구로 사진 파일을 열어 직접 확인하세요. "
        "표시되지 않은 필드는 글자 그대로 출력합니다.\n\n"
        f"{_meta_block(item, config, draft.instruction.persona)}\n\n{_draft_block(draft)}\n\n{_judge_block(judge)}\n\n"
        f"## 문체 기준 (assistant 발화)\n{priority or '(초안의 말투를 유지)'}\n\n"
        f"## 사진 파일 (Read 도구로 열기)\n{image_path}\n"
    )
