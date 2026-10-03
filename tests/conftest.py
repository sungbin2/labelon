"""공용 픽스처: 2026-09-23 LabelOn 688 데이터셋 실제 초안 구조를 재현."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from labelon_reviewer.config import AppConfig
from labelon_reviewer.domain import (
    Dialogue,
    DialogueTurn,
    Draft,
    Instruction,
    RelatedQA,
    SourceItem,
)

FIXTURES = Path(__file__).parent / "fixtures"

SAMPLE_INSTRUCTION = {
    "archetype": "음식",
    "persona": "장난기가 많은 어린아이",
    "task": "장난기가 많은 어린아이가 음식을 스스로 다룰 수 있도록 음식과 관련된 것이 어디에 있는지 확인하고, 손이 닿는 방향과 조심할 것을 우선 안내하세요.",
}
SAMPLE_FACTS = [
    "오른쪽 가까이에 음식이 든 냄비가 레인지 위에 놓여 있다.",
    "냄비의 검은 손잡이가 왼쪽으로 뻗어 있어 손이 닿을 만큼 가깝다.",
    "나무 주걱이 냄비 안의 음식 위에 놓여 있다.",
    "가운데 가까이에 유리 냄비 뚜껑이 놓여 있다.",
    "왼쪽 가까이에 빈 그릇이 놓여 있다.",
]
SAMPLE_FINAL_ANSWER = {
    "context": {
        "user_type": "장난기가 많은 어린아이",
        "situation": "조리대의 음식을 왼쪽 빈 그릇에 담으려는 참이다.",
        "priority": "아이에게 직접 말합니다. 옆에 선 어른이 아이에게 말하듯 쉬운 반말로 말하세요.",
    },
    "dialogue": [
        {"turn": 1, "user": "저 음식을 그릇에 담고 싶어.", "assistant": "오른쪽 가까운 냄비는 레인지 위라 뜨거울 수 있어. 먼저 멈추고 몸을 왼쪽 빈 그릇 쪽으로 비켜."},
        {"turn": 2, "user": "왼쪽으로 비켰어. 빈 그릇이 가까이 보여.", "assistant": "그릇 위쪽에는 유리 냄비 뚜껑이 있고, 오른쪽에는 냄비 손잡이가 있어. 둘 다 건드리지 말고 멈춰 있어."},
        {"turn": 3, "user": "멈췄어. 음식은 어떻게 담아?", "assistant": "음식과 나무 주걱은 오른쪽 냄비 안에 있어서 손을 뻗으면 뜨거울 수 있어. 냄비에서 담는 건 어른에게 맡기자. 지금 어른 불러."},
    ],
}


@pytest.fixture
def config(tmp_path: Path) -> AppConfig:
    cfg = AppConfig(dataset_id=688, persona="장난기가 많은 어린아이", model_backend="fake")
    cfg.base_dir = tmp_path
    cfg.cli.cwd = str(tmp_path / "cliwork")
    return cfg


@pytest.fixture
def sample_item() -> SourceItem:
    return SourceItem(
        job_id=158448,
        dataset_id=688,
        dataset_name="[업사이클링] 거주환경 (어린이3)",
        file_id=2190682,
        job_vqa_id=7113916,
        annotator_id=2833767,
        image_url="https://images.labelon.kr/2021/02/11/150a214ef70b4f6ea16ba176044afde9.jpg",
        org_file_name="20210211_084503.jpg",
        file_name="150a214ef70b4f6ea16ba176044afde9.jpg",
        category="음식",
        weather="그외",
        detected_object="병,식탁",
        related_qa=[RelatedQA(question="간장통에 간장이 가득 차있어", answer="아니요", id=7113916)],
        job_date=datetime(2026, 9, 23, 0, 52, 33, tzinfo=UTC),
        job_status="AK01",
        de_identification_status="AY01",
    )


@pytest.fixture
def sample_draft() -> Draft:
    return Draft(
        instruction=Instruction(**SAMPLE_INSTRUCTION),
        scene="조리대 오른쪽 레인지에는 음식이 든 냄비가 있고 왼쪽에는 빈 그릇과 조리 도구가 놓여 있다.",
        facts=list(SAMPLE_FACTS),
        cot1="조리대만 가까이 보이며, 음식이 든 냄비와 손잡이는 오른쪽에 있고 빈 그릇은 왼쪽에 있다.",
        cot2="레인지 위 냄비와 그 안의 음식은 뜨거울 수 있고, 가까운 손잡이를 당기면 냄비가 움직일 수 있으며 유리 뚜껑은 건드리면 깨질 수 있다.",
        cot3="아이를 빈 그릇 쪽으로 비켜서게 한 뒤 손잡이와 유리 뚜껑을 피하게 하고, 뜨거운 냄비에서 음식을 담는 일은 어른에게 맡기도록 안내한다.",
        dialogue=Dialogue(
            context=SAMPLE_FINAL_ANSWER["context"],
            turns=[DialogueTurn(**t) for t in SAMPLE_FINAL_ANSWER["dialogue"]],
        ),
    )


@pytest.fixture
def job_page_html() -> str:
    return (FIXTURES / "job_page_sample.html").read_text(encoding="utf-8")


def judge_raw_all_true(n_turns: int = 3) -> dict:
    return {
        "facts": [{"index": i, "verdict": "TRUE", "evidence": "이미지에서 확인"} for i in range(5)],
        "scene": {"consistent": True, "note": ""},
        "cot": [{"field": f, "consistent": True, "note": ""} for f in ("cot1", "cot2", "cot3")],
        "dialogue_turns": [{"turn": t, "consistent": True, "note": ""} for t in range(1, n_turns + 1)],
        "persona_task_fit": {"cot_fits": True, "dialogue_fits": True, "note": ""},
        "missing_in_image": [],
        "impossible_reason_suggestion": "",
        "qa_matches_cot3": True, "task_qa_direction_match": True, "appliance_controls_visible": None,
        "archetype_suggestion": {"fits": True, "suggested": "", "reason": ""},
        "archetype_fits_environment": True, "environment_note": "",
        "impossible_flags": {"core_error_propagated": False, "persona_infeasible_guidance": False, "unsafe_guidance": False, "note": ""},
        "text_issues": [],
    }


def dump(obj) -> str:
    return json.dumps(obj, ensure_ascii=False)
