from labelon_reviewer.domain import (
    ArchetypeSuggestion,
    DialogueTurn,
    ImagePaths,
    InstructionCheck,
    JudgeResult,
)
from labelon_reviewer.model.fake import FakeModelClient, default_revise_raw
from labelon_reviewer.revise import ReviseStage, enforce_constraints, raw_to_draft

IMG = ImagePaths(original="o.jpg", resized="r.jpg")


def _judge(needs: bool, suggestion: ArchetypeSuggestion | None = None) -> JudgeResult:
    return JudgeResult(
        instruction_check=InstructionCheck(archetype_known=True, task_matches_template=True, persona_matches_config=True),
        fact_verdicts=[], field_verdicts=[], consistency_score=80, impossible_candidate=False, needs_revision=needs,
        archetype_suggestion=suggestion or ArchetypeSuggestion(),
    )


async def test_skipped_when_not_needed(config, sample_item, sample_draft):
    fake = FakeModelClient()
    r = await ReviseStage(config, fake).run(IMG, sample_item, sample_draft, _judge(False))
    assert r.skipped and r.draft == sample_draft and fake.calls == []


async def test_constraints_enforced(config, sample_item, sample_draft):
    raw = default_revise_raw(sample_draft)
    raw["facts"][1] = "냄비의 검은 손잡이가 오른쪽으로 뻗어 있다."
    raw["facts"][4] = ""  # 빈 값 → 복원
    raw["dialogue_assistant"] = [
        {"turn": 1, "assistant": "새 답변 1"},
        {"turn": 4, "assistant": "새 턴(허용 안 됨)"},
    ]
    raw["change_notes"] = [{"field": "fact_2", "reason": "방향 수정"}]
    r = await ReviseStage(config, FakeModelClient(revise_raw=raw)).run(IMG, sample_item, sample_draft, _judge(True))
    d = r.draft
    assert d.instruction == sample_draft.instruction and not r.instruction_changed
    assert d.dialogue.context == sample_draft.dialogue.context
    assert len(d.dialogue.turns) == 3 and d.dialogue.turn(1).assistant == "새 답변 1"
    assert d.dialogue.turn(1).user == sample_draft.dialogue.turn(1).user
    assert d.facts[1].startswith("냄비의 검은 손잡이가 오른쪽") and d.facts[4] == sample_draft.facts[4]
    assert any(n["field"] == "fact_5" for n in r.change_notes) and not r.skipped and r.dropped_turns == []


def test_raw_to_draft_keeps_empty_turns(sample_draft):
    draft = sample_draft.model_copy(deep=True)
    draft.dialogue.turns.append(DialogueTurn(turn=4, user="", assistant=""))
    raw = default_revise_raw(draft)
    raw["dialogue_assistant"].append({"turn": 4, "assistant": "채우면 안 됨"})
    proposed, dropped = raw_to_draft(raw, draft)
    out = enforce_constraints(draft, proposed, [])
    assert out.dialogue.turn(4).assistant == "" and dropped == []


async def test_fact_count_follows_original(config, sample_item, sample_draft):
    six = sample_draft.model_copy(deep=True)
    six.facts = sample_draft.facts + ["여섯 번째 사실이다."]
    raw = default_revise_raw(six)
    raw["facts"] = raw["facts"][:4]
    r = await ReviseStage(config, FakeModelClient(revise_raw=raw)).run(IMG, sample_item, six, _judge(True))
    assert len(r.draft.facts) == 6 and r.draft.facts[5] == "여섯 번째 사실이다."
    assert any(n["field"] == "facts" for n in r.change_notes)


# ---------------------------------------------------------------- cycle 3
async def test_archetype_correction_applied(config, sample_item, sample_draft):
    fake = FakeModelClient(revise_raw=default_revise_raw(sample_draft))
    sug = ArchetypeSuggestion(fits=False, suggested="쇼핑", reason="QA 가 물건 찾기")
    r = await ReviseStage(config, fake).run(IMG, sample_item, sample_draft, _judge(True, sug))
    assert r.instruction_changed and r.draft.instruction.archetype == "쇼핑"
    assert r.draft.instruction.persona == sample_draft.instruction.persona
    assert r.draft.instruction.task.startswith("장난기가 많은 어린아이가 찾는 물건에")
    assert fake.last_corrected is not None and fake.last_corrected.archetype == "쇼핑"
    assert any(n["field"] == "archetype" for n in r.change_notes)


async def test_turn_drop_ignored_by_default(config, sample_item, sample_draft):
    """사이클 8: 기본 설정(allow_turn_drop=False)에서는 drop 을 무시하고 모든 턴을 유지한다."""
    assert config.revision_rules.allow_turn_drop is False
    raw = default_revise_raw(sample_draft)
    raw["dialogue_assistant"] = [{"turn": 1, "assistant": "a1"}, {"turn": 2, "assistant": "a2"}, {"turn": 3, "assistant": "a3", "drop": True}]
    r = await ReviseStage(config, FakeModelClient(revise_raw=raw)).run(IMG, sample_item, sample_draft, _judge(True))
    assert r.dropped_turns == [] and [t.turn for t in r.draft.dialogue.active_turns()] == [1, 2, 3]
    assert r.draft.dialogue.turn(3).assistant == "a3"


async def test_turn_drop_and_renumber(config, sample_item, sample_draft):
    config.revision_rules.allow_turn_drop = True  # 사이클 8: 설정으로 허용했을 때만
    raw = default_revise_raw(sample_draft)
    raw["dialogue_assistant"] = [
        {"turn": 1, "assistant": "a1", "drop": True},  # 첫 턴은 삭제 불가
        {"turn": 2, "assistant": "a2 + 합쳐진 내용", "drop": False},
        {"turn": 3, "assistant": "", "drop": True},
    ]
    r = await ReviseStage(config, FakeModelClient(revise_raw=raw)).run(IMG, sample_item, sample_draft, _judge(True))
    turns = r.draft.dialogue.turns
    assert r.dropped_turns == [3] and [t.turn for t in turns] == [1, 2]
    assert turns[0].assistant == "a1" and turns[0].user == sample_draft.dialogue.turn(1).user
    assert turns[1].assistant == "a2 + 합쳐진 내용" and turns[1].user == sample_draft.dialogue.turn(2).user
    assert any(n["field"] == "turn_3" for n in r.change_notes)


async def test_turn_count_cannot_grow(config, sample_item, sample_draft):
    raw = default_revise_raw(sample_draft)
    raw["dialogue_assistant"].append({"turn": 4, "assistant": "새 턴"})
    r = await ReviseStage(config, FakeModelClient(revise_raw=raw)).run(IMG, sample_item, sample_draft, _judge(True))
    assert len(r.draft.dialogue.active_turns()) == 3


async def test_phone_numbers_removed(config, sample_item, sample_draft):
    raw = default_revise_raw(sample_draft)
    raw["cot3"] = raw["cot3"] + " 문의 234-5678"
    raw["dialogue_assistant"][0]["assistant"] = "전화 010-1234-5678 로 물어봐."
    r = await ReviseStage(config, FakeModelClient(revise_raw=raw)).run(IMG, sample_item, sample_draft, _judge(True))
    assert "234-5678" not in r.draft.cot3 and "010-1234-5678" not in r.draft.dialogue.turn(1).assistant
    assert any(n["reason"] == "전화번호 제거" for n in r.change_notes)
