from labelon_reviewer.diff import diff, diff_text, split_sentences
from labelon_reviewer.domain import DiffOp


def test_split_sentences():
    assert split_sentences("첫 문장이다. 둘째 문장이다! 셋째?") == ["첫 문장이다.", "둘째 문장이다!", "셋째?"]
    assert split_sentences("") == []


def test_identical_is_unchanged(sample_draft):
    out = diff(sample_draft, sample_draft.model_copy(deep=True))
    assert all(not d.changed for d in out)
    assert [d.field for d in out][:4] == ["archetype", "persona", "task", "scene"] and "turn_3_assistant" in [d.field for d in out]


def test_fact_replace(sample_draft):
    other = sample_draft.model_copy(deep=True)
    other.facts[1] = "냄비의 검은 손잡이가 오른쪽으로 뻗어 있다."
    out = {d.field: d for d in diff(sample_draft, other)}
    assert out["fact_2"].changed and out["fact_2"].segments[0].op == DiffOp.REPLACE
    assert not out["fact_1"].changed


def test_sentence_level_ops():
    d = diff_text("scene", "A다. B다. C다.", "A다. C다. D다.")
    ops = [s.op for s in d.segments]
    assert d.changed and DiffOp.DELETE in ops and DiffOp.INSERT in ops and DiffOp.EQUAL in ops
