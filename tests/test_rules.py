from labelon_reviewer import rules
from labelon_reviewer.domain import Instruction
from tests.conftest import SAMPLE_INSTRUCTION


def test_real_draft_matches(config):
    ic = rules.check(Instruction(**SAMPLE_INSTRUCTION), config)
    assert ic.ok and ic.mismatch_details == []


def test_particle_variation_allowed(config):
    ins = Instruction(**SAMPLE_INSTRUCTION)
    ins.task = ins.task.replace("어린아이가 음식을", "어린아이는 음식을")
    assert rules.check(ins, config).task_matches_template


def test_whitespace_variation_allowed(config):
    ins = Instruction(**SAMPLE_INSTRUCTION)
    ins.task = ins.task.replace(" ", "  ")
    assert rules.check(ins, config).task_matches_template


def test_wrong_template_detected(config):
    ins = Instruction(**SAMPLE_INSTRUCTION)
    ins.task = "장난기가 많은 어린아이가 안전하게 이동할 수 있도록 진행 방향의 보행환경을 확인하고, 이동 경로의 장애물과 위험요소를 우선 안내하세요."
    ic = rules.check(ins, config)
    assert not ic.task_matches_template and ic.archetype_known and ic.persona_matches_config
    assert any("템플릿과 다릅니다" in d for d in ic.mismatch_details)


def test_legacy_daily_support_template_still_matches(config):
    """일상지원 템플릿 변경(2026-09-30): 옛 문장 초안도 일치, 정정 Task 는 새 문장."""
    persona = "장난기가 많은 어린아이"
    old = Instruction(archetype="일상지원", persona=persona, task=rules.build_task("(Persona) 이 공간에서 필요한 것을 찾을 수 있도록 주변 시설과 물건이 어떻게 놓여 있는지 확인하고, 무엇이 어느 쪽에 있는지 우선 안내하세요.", persona))
    new = Instruction(archetype="일상지원", persona=persona, task=rules.build_task("(Persona) 이 주변에서 가려는 곳과 필요한 것을 찾아갈 수 있도록 주변 시설과 길이 어떻게 이어져 있는지 확인하고, 어느 쪽으로 가야 하는지와 걸리는 것을 우선 안내하세요.", persona))
    assert rules.check(old, config).task_matches_template and rules.check(new, config).task_matches_template
    fixed = rules.correct_instruction(Instruction(archetype="음식", persona=persona, task="x"), "일상지원", config)
    assert fixed is not None and fixed.task.startswith(persona + "가 이 주변에서 가려는 곳과")
    assert config.templates_for("일상지원")[0] == config.archetype_templates["일상지원"] and len(config.templates_for("없음")) == 0


def test_compound_directions():
    assert rules.find_compound_directions("앞 왼쪽에 소파, 뒤 오른쪽에 문, 왼쪽 앞의 상자, 오른쪽에 창문") == ["앞 왼쪽", "뒤 오른쪽", "왼쪽 앞"]
    assert rules.find_compound_directions("앞왼쪽 앞왼쪽") == ["앞왼쪽"]
    assert rules.find_compound_directions("앞쪽과 왼쪽") == []


def test_unknown_archetype(config):
    ins = Instruction(archetype="요리", persona=config.persona, task="x")
    ic = rules.check(ins, config)
    assert not ic.archetype_known and not ic.task_matches_template


def test_other_dataset_persona_is_not_a_mismatch(config):
    # 데이터셋마다 페르소나가 다르므로 설정 페르소나와 비교하지 않는다 (사이클 2)
    ins = Instruction(**SAMPLE_INSTRUCTION)
    ins.persona = "시각장애인"
    ins.task = ins.task.replace("장난기가 많은 어린아이가", "시각장애인이")
    ic = rules.check(ins, config)
    assert ic.task_matches_template and ic.persona_matches_config and ic.ok and ic.mismatch_details == []


def test_empty_persona_noted(config):
    ins = Instruction(archetype="음식", persona="", task="x")
    ic = rules.check(ins, config)
    assert not ic.ok and any("persona" in d for d in ic.mismatch_details)


def test_subject_particle_and_build_task(config):
    assert rules.subject_particle("장난기가 많은 어린아이") == "가"
    assert rules.subject_particle("혼자 지내는 시각장애 성인") == "이"
    assert rules.subject_particle("") == "가"
    t = rules.build_task(config.archetype_templates["쇼핑"], "장난기가 많은 어린아이")
    assert t.startswith("장난기가 많은 어린아이가 찾는 물건에") and rules.check(Instruction(archetype="쇼핑", persona="장난기가 많은 어린아이", task=t), config).ok


def test_correct_instruction(config):
    ins = Instruction(**SAMPLE_INSTRUCTION)
    fixed = rules.correct_instruction(ins, "쇼핑", config)
    assert fixed.archetype == "쇼핑" and fixed.persona == ins.persona and "찾는 물건에 닿을 수 있도록" in fixed.task
    assert rules.correct_instruction(ins, "음식", config) is None  # 같은 아키타입
    assert rules.correct_instruction(ins, "요리", config) is None  # 미지 아키타입


def test_phone_numbers():
    assert rules.find_phone_numbers("문의는 234-5678 또는 010-1234-5678 로.") == ["234-5678", "010-1234-5678"]
    assert rules.find_phone_numbers("2021-01-14 촬영") == []
    assert rules.strip_phone_numbers("문의는 234-5678 로 하세요.") == "문의는 로 하세요."
