from labelon_reviewer.domain import Draft, FinalDraft


def test_draft_json_roundtrip(sample_draft):
    data = sample_draft.model_dump(mode="json")
    again = Draft.model_validate(data)
    assert again == sample_draft


def test_facts_variable_length():
    assert Draft(facts=["a", "b"]).facts == ["a", "b"]
    d6 = Draft(facts=list("abcdef"))
    assert d6.fact_count == 6 and d6.editable_fields()[9] == "fact_6"
    assert Draft(facts=[None, "x"]).facts == ["", "x"]


def test_field_addressing(sample_draft):
    assert sample_draft.get_field("fact_1") == sample_draft.facts[0]
    sample_draft.set_field("turn_2_assistant", "새 답변")
    assert sample_draft.dialogue.turn(2).assistant == "새 답변"
    names = sample_draft.editable_fields()
    assert names[3] == "scene" and "turn_3_assistant" in names and "turn_4_assistant" not in names
    # 사이클 6: 질문(user)도 편집
    sample_draft.set_field("turn_1_user", "새 질문?")
    sample_draft.set_field("task", "새 task")  # 사이클 7
    assert sample_draft.instruction.task == "새 task" and names[:4] == ["archetype", "persona", "task", "scene"]
    assert sample_draft.get_field("turn_1_user") == "새 질문?" and "turn_1_user" in names and "turn_4_user" not in names


def test_final_draft_conversion(sample_draft):
    final = FinalDraft.from_draft(sample_draft)
    assert final.edited_by_user is False
    assert final.as_draft() == sample_draft
