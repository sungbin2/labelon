"""테스트·데모용 FakeModelClient. 미리 정한 결과를 반환하고 호출을 기록한다."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..config import AppConfig
from ..domain import Draft, JudgeResult, ModelCallError, ModelUsage, SourceItem


def default_judge_raw(draft: Draft) -> dict[str, Any]:
    return {
        "facts": [{"index": i, "verdict": "TRUE", "evidence": "(fake) 확인"} for i in range(5)],
        "scene": {"consistent": True, "note": ""},
        "cot": [{"field": f, "consistent": True, "note": ""} for f in ("cot1", "cot2", "cot3")],
        "dialogue_turns": [{"turn": t.turn, "consistent": True, "note": ""} for t in draft.dialogue.active_turns()],
        "persona_task_fit": {"cot_fits": True, "dialogue_fits": True, "note": ""},
        "missing_in_image": [],
        "impossible_reason_suggestion": "",
        "qa_matches_cot3": True, "task_qa_direction_match": True, "appliance_controls_visible": None,
        "archetype_suggestion": {"fits": True, "suggested": "", "reason": ""},
    }


def default_revise_raw(draft: Draft) -> dict[str, Any]:
    return {
        "scene": draft.scene, "facts": list(draft.facts), "cot1": draft.cot1, "cot2": draft.cot2, "cot3": draft.cot3,
        "dialogue_assistant": [{"turn": t.turn, "assistant": t.assistant} for t in draft.dialogue.active_turns()],
        "change_notes": [],
    }


class FakeModelClient:
    def __init__(
        self, config: AppConfig | None = None, *, judge_raw: dict | None = None, revise_raw: dict | None = None,
        fail_judge: bool = False, fail_revise: bool = False,
    ) -> None:
        self.config = config
        self.judge_raw = judge_raw
        self.revise_raw = revise_raw
        self.fail_judge = fail_judge
        self.fail_revise = fail_revise
        self.calls: list[str] = []

    async def judge(self, image: Path, item: SourceItem, draft: Draft) -> tuple[dict[str, Any], ModelUsage]:
        self.calls.append("judge")
        if self.fail_judge:
            raise ModelCallError("(fake) judge 실패")
        raw = self.judge_raw if self.judge_raw is not None else default_judge_raw(draft)
        return raw, ModelUsage(stage="judge", model="fake", input_tokens=100, output_tokens=50)

    async def revise(self, image: Path, item: SourceItem, draft: Draft, judge: JudgeResult, corrected=None) -> tuple[dict[str, Any], ModelUsage]:
        self.calls.append("revise")
        self.last_corrected = corrected
        if self.fail_revise:
            raise ModelCallError("(fake) revise 실패")
        raw = self.revise_raw if self.revise_raw is not None else default_revise_raw(draft)
        return raw, ModelUsage(stage="revise", model="fake", input_tokens=120, output_tokens=80)
