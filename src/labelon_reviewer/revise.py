"""수정 단계 C-08: (아키타입 정정) → 모델 수정 → 제약 강제(BR-20~28) → change_notes.

사이클 3(검수 가이드): Instruction 정정(템플릿 치환, D4), 턴 삭제·병합(D5), 전화번호 제거(D6).
"""

from __future__ import annotations

import logging
from typing import Any

from . import rules
from .config import AppConfig
from .domain import (
    Dialogue,
    DialogueTurn,
    Draft,
    ImagePaths,
    Instruction,
    JudgeResult,
    RevisedDraft,
    SourceItem,
)
from .model.base import ModelClient

log = logging.getLogger(__name__)


def raw_to_draft(raw: dict[str, Any], original: Draft, allow_drop: bool = True) -> tuple[Draft, list[int]]:
    """모델 출력 → Draft. drop=true 턴은 제외(첫 활성 턴 제외 불가), 남은 턴은 1부터 재번호. 반환: (draft, 삭제된 원래 턴 번호).
    allow_drop=False(사이클 8 기본)면 drop 을 무시하고 모든 턴을 유지한다."""
    by_turn: dict[int, dict[str, Any]] = {
        int(t.get("turn", 0)): t for t in (raw.get("dialogue_assistant") or []) if isinstance(t, dict)
    }
    active = original.dialogue.active_turns()
    kept: list[DialogueTurn] = []
    dropped: list[int] = []
    for idx, ot in enumerate(active):
        entry = by_turn.get(ot.turn, {})
        if allow_drop and idx > 0 and bool(entry.get("drop")):
            dropped.append(ot.turn)
            continue
        assistant = str(entry.get("assistant", "")) if entry else ot.assistant
        kept.append(DialogueTurn(turn=ot.turn, user=ot.user, assistant=assistant or ot.assistant))
    # 재번호 (연속 1..k). 비활성 턴은 뒤에 이어 붙인다
    turns = [DialogueTurn(turn=i + 1, user=t.user, assistant=t.assistant) for i, t in enumerate(kept)]
    inactive = [t for t in original.dialogue.turns if t.is_empty()]
    for _ in inactive:
        turns.append(DialogueTurn(turn=len(turns) + 1, user="", assistant=""))
    facts = [str(x) for x in (raw.get("facts") or [])]
    return (
        Draft(
            instruction=original.instruction, scene=str(raw.get("scene", "")), facts=facts,
            cot1=str(raw.get("cot1", "")), cot2=str(raw.get("cot2", "")), cot3=str(raw.get("cot3", "")),
            dialogue=Dialogue(context=dict(original.dialogue.context), turns=turns),
        ),
        dropped,
    )


def enforce_constraints(original: Draft, proposed: Draft, notes: list[dict[str, str]], config: AppConfig | None = None) -> Draft:
    """BR-20~28 + 사이클 3: 턴 수 감소만 허용, 전화번호 제거."""
    out = proposed.model_copy(deep=True)
    out.instruction = original.instruction.model_copy(deep=True)  # BR-20 (정정본이면 original 이 이미 정정본)
    # 턴: 증가 금지, 최소 1개, user 발화는 원본 순서로 유지
    orig_active = original.dialogue.active_turns()
    prop_active = proposed.dialogue.active_turns()
    if len(prop_active) > len(orig_active):
        notes.append({"field": "dialogue", "reason": "constraint: 초과 턴 제거"})
        prop_active = prop_active[: len(orig_active)]
    if not prop_active and orig_active:
        notes.append({"field": "dialogue", "reason": "constraint: 턴이 모두 삭제되어 원본 복원"})
        prop_active = [t.model_copy(deep=True) for t in orig_active]
    turns: list[DialogueTurn] = []
    for i, pt in enumerate(prop_active):
        assistant = pt.assistant if pt.assistant.strip() else (orig_active[i].assistant if i < len(orig_active) else "")
        turns.append(DialogueTurn(turn=i + 1, user=pt.user, assistant=assistant))
    for t in original.dialogue.turns:
        if t.is_empty():
            turns.append(DialogueTurn(turn=len(turns) + 1, user="", assistant=""))
    out.dialogue = Dialogue(context=dict(original.dialogue.context), turns=turns)
    # facts 개수 = 원본, 빈 값 복원
    n = len(original.facts)
    facts = list(out.facts)[:n]
    if len(out.facts) != n:
        notes.append({"field": "facts", "reason": f"constraint: 개수 {len(out.facts)} → {n} 보정"})
    while len(facts) < n:
        facts.append("")
    for i in range(n):
        if not facts[i].strip():
            facts[i] = original.facts[i]
            notes.append({"field": f"fact_{i + 1}", "reason": "constraint: 빈 값 → 초안 복원"})
    out.facts = facts
    for name in ("scene", "cot1", "cot2", "cot3"):
        if not getattr(out, name).strip():
            setattr(out, name, getattr(original, name))
            notes.append({"field": name, "reason": "constraint: 빈 값 → 초안 복원"})
    # 전화번호 제거 (D6)
    if config is None or config.text_rules.remove_phone_numbers:
        removed = False
        for name in ("scene", "cot1", "cot2", "cot3"):
            v = getattr(out, name)
            if rules.find_phone_numbers(v):
                setattr(out, name, rules.strip_phone_numbers(v))
                removed = True
        out.facts = [rules.strip_phone_numbers(f) if rules.find_phone_numbers(f) else f for f in out.facts]
        for t in out.dialogue.turns:
            if rules.find_phone_numbers(t.assistant):
                t.assistant = rules.strip_phone_numbers(t.assistant)
                removed = True
        if removed:
            notes.append({"field": "text", "reason": "전화번호 제거"})
    return out


class ReviseStage:
    def __init__(self, config: AppConfig, client: ModelClient) -> None:
        self.config = config
        self.client = client

    def correction_for(self, draft: Draft, judge: JudgeResult) -> Instruction | None:
        sug = judge.archetype_suggestion
        if sug.fits or not sug.suggested:
            return None
        return rules.correct_instruction(draft.instruction, sug.suggested, self.config)

    async def run(self, images: ImagePaths, item: SourceItem, draft: Draft, judge: JudgeResult) -> RevisedDraft:
        if not judge.needs_revision:
            return RevisedDraft(draft=draft.model_copy(deep=True), change_notes=[], skipped=True)
        corrected = self.correction_for(draft, judge)
        base = draft.model_copy(deep=True)
        notes: list[dict[str, str]] = []
        if corrected is not None:
            base.instruction = corrected
            notes.append({"field": "archetype", "reason": f"아키타입 정정 {draft.instruction.archetype} → {corrected.archetype}: {judge.archetype_suggestion.reason}"})
            notes.append({"field": "task", "reason": "정정된 아키타입 템플릿으로 task 재생성"})
        raw, usage = await self.client.revise(images.resized, item, base, judge, corrected=corrected)
        notes += [
            {"field": str(n.get("field", "")), "reason": str(n.get("reason", ""))}
            for n in (raw.get("change_notes") or []) if isinstance(n, dict)
        ]
        proposed, dropped = raw_to_draft(raw, base, allow_drop=self.config.revision_rules.allow_turn_drop)
        for d in dropped:
            notes.append({"field": f"turn_{d}", "reason": "턴 삭제(CoT 3단계 범위 밖 또는 불필요한 멀티턴)"})
        final = enforce_constraints(base, proposed, notes, self.config)
        log.info("revise done: %d notes, instruction_changed=%s, dropped=%s", len(notes), corrected is not None, dropped)
        return RevisedDraft(draft=final, change_notes=notes, skipped=False, model_usage=usage,
                            instruction_changed=corrected is not None, dropped_turns=dropped)
