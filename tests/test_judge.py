import pytest

from labelon_reviewer.domain import FactVerdict, FieldVerdict, ImagePaths, Verdict
from labelon_reviewer.judge import JudgeStage, compute_score, normalize_raw
from labelon_reviewer.model.fake import FakeModelClient
from tests.conftest import judge_raw_all_true

IMG = ImagePaths(original="o.jpg", resized="r.jpg")


def test_score_example_79():
    facts = [FactVerdict(index=i, verdict=v) for i, v in enumerate([Verdict.TRUE] * 3 + [Verdict.UNKNOWN, Verdict.FALSE])]
    fields = [FieldVerdict(field="scene", consistent=True)] + [
        FieldVerdict(field=f, consistent=c) for f, c in [("cot1", True), ("cot2", True), ("cot3", False), ("turn_1", True), ("turn_2", True), ("turn_3", False)]
    ]
    assert compute_score(facts, fields) == 42 + 20 + round(20 * 4 / 6)


def test_score_all_true_is_100():
    facts = [FactVerdict(index=i, verdict=Verdict.TRUE) for i in range(5)]
    fields = [FieldVerdict(field="scene", consistent=True), FieldVerdict(field="cot1", consistent=True)]
    assert compute_score(facts, fields) == 100


async def test_all_true_no_revision(config, sample_item, sample_draft):
    stage = JudgeStage(config, FakeModelClient(judge_raw=judge_raw_all_true()))
    j = await stage.run(IMG, sample_item, sample_draft)
    assert j.consistency_score == 100 and not j.needs_revision and not j.impossible_candidate and j.instruction_check.ok


async def test_false_fact_triggers_revision(config, sample_item, sample_draft):
    raw = judge_raw_all_true()
    raw["facts"][1]["verdict"] = "FALSE"
    j = await JudgeStage(config, FakeModelClient(judge_raw=raw)).run(IMG, sample_item, sample_draft)
    assert j.needs_revision and j.consistency_score == 88


async def test_persona_fit_triggers_revision(config, sample_item, sample_draft):
    raw = judge_raw_all_true()
    raw["persona_task_fit"]["dialogue_fits"] = False
    j = await JudgeStage(config, FakeModelClient(judge_raw=raw)).run(IMG, sample_item, sample_draft)
    assert j.needs_revision and j.consistency_score == 100


async def test_impossible_candidate_skips_revision(config, sample_item, sample_draft):
    raw = judge_raw_all_true()
    for f in raw["facts"]:
        f["verdict"] = "FALSE"
    raw["scene"]["consistent"] = False
    raw["impossible_reason_suggestion"] = "이미지와 초안의 장면이 다름"
    j = await JudgeStage(config, FakeModelClient(judge_raw=raw)).run(IMG, sample_item, sample_draft)
    assert j.impossible_candidate and j.needs_revision and j.consistency_score <= config.threshold  # 사이클 10: 불가 후보도 수정안 생성
    config.revision_rules.revise_impossible = False
    j2 = await JudgeStage(config, FakeModelClient(judge_raw=raw)).run(IMG, sample_item, sample_draft)
    assert j2.impossible_candidate and not j2.needs_revision


def test_normalize_fills_missing(sample_draft):
    warnings: list[str] = []
    facts, fields, fit, missing, reason, extras = normalize_raw({"facts": [{"index": 0, "verdict": "TRUE", "evidence": ""}]}, sample_draft, warnings)
    assert extras["archetype_suggestion"].fits and extras["qa_matches_cot3"] is True
    assert len(facts) == 5 and facts[4].verdict is Verdict.UNKNOWN  # 초안 facts 개수(5)에 맞춤
    assert [f.field for f in fields] == ["scene", "cot1", "cot2", "cot3", "turn_1", "turn_2", "turn_3"]
    assert all(not f.consistent for f in fields) and len(warnings) >= 8


def test_score_with_six_facts():
    facts = [FactVerdict(index=i, verdict=Verdict.TRUE) for i in range(6)]
    facts[5] = FactVerdict(index=5, verdict=Verdict.FALSE)
    fields = [FieldVerdict(field="scene", consistent=True), FieldVerdict(field="cot1", consistent=True)]
    assert compute_score(facts, fields) == 50 + 20 + 20


async def test_archetype_suggestion_triggers_revision_not_impossible(config, sample_item, sample_draft):
    raw = judge_raw_all_true()
    raw["task_qa_direction_match"] = False  # 방향 불일치지만 정정 가능하면 불가가 아니라 정정
    raw["archetype_suggestion"] = {"fits": False, "suggested": "쇼핑", "reason": "QA 가 물건 찾기"}
    j = await JudgeStage(config, FakeModelClient(judge_raw=raw)).run(IMG, sample_item, sample_draft)
    assert not j.impossible_candidate and j.needs_revision and j.archetype_correction() == "쇼핑"


async def test_direction_mismatch_without_correction_is_impossible(config, sample_item, sample_draft):
    raw = judge_raw_all_true()
    raw["task_qa_direction_match"] = False
    j = await JudgeStage(config, FakeModelClient(judge_raw=raw)).run(IMG, sample_item, sample_draft)
    assert j.impossible_candidate and any("방향" in r for r in j.impossible_reasons) and not j.needs_revision


async def test_invalid_suggestion_ignored(config, sample_item, sample_draft):
    raw = judge_raw_all_true()
    raw["archetype_suggestion"] = {"fits": False, "suggested": "요리", "reason": "x"}
    warnings = []
    j = await JudgeStage(config, FakeModelClient(judge_raw=raw)).run(IMG, sample_item, sample_draft, warnings)
    assert j.archetype_correction() is None and not j.needs_revision and any("적용할 수 없어" in w for w in warnings)


async def test_appliance_controls_rule(config, sample_item, sample_draft):
    d = sample_draft.model_copy(deep=True)
    d.instruction.archetype = "가전조작"
    raw = judge_raw_all_true()
    raw["appliance_controls_visible"] = False
    j = await JudgeStage(config, FakeModelClient(judge_raw=raw)).run(IMG, sample_item, d)
    assert j.impossible_candidate and any("조작부" in r for r in j.impossible_reasons)


async def test_too_many_false_facts_is_impossible(config, sample_item, sample_draft):
    raw = judge_raw_all_true()
    for i in range(3):
        raw["facts"][i]["verdict"] = "FALSE"
    j = await JudgeStage(config, FakeModelClient(judge_raw=raw)).run(IMG, sample_item, sample_draft)
    assert j.impossible_candidate and any("거짓 팩트 3개" in r for r in j.impossible_reasons) and j.needs_revision


async def test_qa_cot3_and_phone_trigger_revision(config, sample_item, sample_draft):
    raw = judge_raw_all_true()
    raw["qa_matches_cot3"] = False
    j = await JudgeStage(config, FakeModelClient(judge_raw=raw)).run(IMG, sample_item, sample_draft)
    assert j.needs_revision and not j.impossible_candidate
    d = sample_draft.model_copy(deep=True)
    d.cot3 = d.cot3 + " 문의 234-5678"
    j2 = await JudgeStage(config, FakeModelClient(judge_raw=judge_raw_all_true())).run(IMG, sample_item, d)
    assert j2.needs_revision and j2.phone_numbers == ["234-5678"]


async def test_beyond_cot3_and_role_fits(config, sample_item, sample_draft):
    raw = judge_raw_all_true()
    raw["dialogue_turns"][2]["beyond_cot3"] = True
    j = await JudgeStage(config, FakeModelClient(judge_raw=raw)).run(IMG, sample_item, sample_draft)
    assert j.needs_revision and [f for f in j.field_verdicts if f.field == "turn_3"][0].beyond_cot3
    raw2 = judge_raw_all_true()
    raw2["cot"][1]["role_fits"] = False
    j2 = await JudgeStage(config, FakeModelClient(judge_raw=raw2)).run(IMG, sample_item, sample_draft)
    assert j2.needs_revision


# ---- 사이클 4 (가이드 이미지 슬라이드)


async def test_environment_conflict_is_impossible_and_blocks_correction(config, sample_item, sample_draft):
    raw = judge_raw_all_true()
    raw["archetype_fits_environment"] = False
    raw["environment_note"] = "실외 도로 사진에 실내탐색"
    raw["archetype_suggestion"] = {"fits": False, "suggested": "보행안전", "reason": "도로"}
    warnings: list[str] = []
    j = await JudgeStage(config, FakeModelClient(judge_raw=raw)).run(IMG, sample_item, sample_draft, warnings)
    assert j.impossible_candidate and not j.needs_revision and j.archetype_correction() is None
    assert any("환경과 맞지 않음: 실외 도로" in r for r in j.impossible_reasons)
    assert any("정정 제안 '보행안전' 을 적용하지 않습니다" in w for w in warnings)
    assert j.impossible_reason_suggestion.startswith("아키타입이 이미지 환경과 맞지 않음")


@pytest.mark.parametrize("flag,text", [
    ("core_error_propagated", "오인식이 CoT·QA 전반에 전파됨"),
    ("persona_infeasible_guidance", "수행할 수 없는 확인·행동을 요구함"),
    ("unsafe_guidance", "위험 행위를 권고함"),
])
async def test_impossible_flags(config, sample_item, sample_draft, flag, text):
    raw = judge_raw_all_true()
    raw["impossible_flags"][flag] = True
    raw["impossible_flags"]["note"] = "근거"
    j = await JudgeStage(config, FakeModelClient(judge_raw=raw)).run(IMG, sample_item, sample_draft)
    assert j.impossible_candidate and not j.needs_revision and getattr(j.impossible_flags, flag)
    assert any(text in r and r.endswith(": 근거") for r in j.impossible_reasons)


async def test_text_issues_only_triggers_revision_and_prompt(config, sample_item, sample_draft):
    raw = judge_raw_all_true()
    raw["text_issues"] = [{"field": "turn_1_assistant", "kind": "typo", "wrong": "베런다", "correct": "베란다"},
                          {"field": "fact_2", "kind": "number", "wrong": "열세 번", "correct": "13번"},
                          {"field": "scene", "kind": "bogus", "wrong": "x", "correct": "y"}]  # 잘못된 kind 는 무시
    j = await JudgeStage(config, FakeModelClient(judge_raw=raw)).run(IMG, sample_item, sample_draft)
    assert j.needs_revision and not j.impossible_candidate and j.consistency_score == 100
    assert [t.kind for t in j.text_issues] == ["typo", "number"]
    from labelon_reviewer.prompts import build_revise_user
    p = build_revise_user(sample_item, sample_draft, j, "r.jpg", config)
    assert "텍스트 오류 turn_1_assistant (오탈자): '베런다' → '베란다'" in p and "(숫자 표기): '열세 번' → '13번'" in p


async def test_compound_direction_detected_deterministically(config, sample_item, sample_draft):
    """사이클 5: '앞 왼쪽' 은 모델이 놓쳐도 도구가 text_issues(direction) 로 넣고 수정 필요. 모델 보고와 중복 제거."""
    d = sample_draft.model_copy(deep=True)
    d.cot1 = d.cot1 + " 앞 왼쪽에 상자 더미가 있다."
    d.dialogue.turns[0].assistant = d.dialogue.turns[0].assistant + " 뒤 오른쪽은 조심해."
    raw = judge_raw_all_true()
    raw["text_issues"] = [{"field": "cot1", "kind": "direction", "wrong": "앞 왼쪽", "correct": "앞쪽"}]
    j = await JudgeStage(config, FakeModelClient(judge_raw=raw)).run(IMG, sample_item, d)
    assert j.needs_revision and not j.impossible_candidate
    assert [(t.field, t.kind, t.wrong) for t in j.text_issues] == [("cot1", "direction", "앞 왼쪽"), ("turn_1_assistant", "direction", "뒤 오른쪽")]


async def test_cycle4_fields_missing_defaults_to_no_problem(config, sample_item, sample_draft):
    raw = judge_raw_all_true()
    for k in ("archetype_fits_environment", "environment_note", "impossible_flags", "text_issues"):
        raw.pop(k)
    j = await JudgeStage(config, FakeModelClient(judge_raw=raw)).run(IMG, sample_item, sample_draft)
    assert not j.needs_revision and not j.impossible_candidate and j.archetype_fits_environment and not j.impossible_flags.any() and j.text_issues == []
