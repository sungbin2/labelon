"""Submitter.approve 의 fill 순서·빈 턴 처리·Instruction 채움을 Fake page 로 검증 (실브라우저 없음)."""

from __future__ import annotations

import pytest

from labelon_reviewer.domain import FinalDraft, SubmissionKind
from labelon_reviewer.labelon.parser import field_locators
from labelon_reviewer.labelon.submitter import Submitter


class FakeLocator:
    def __init__(self, store: dict, key: str, count: int):
        self.store, self.key, self._count = store, key, count

    def nth(self, i):
        return FakeLocator(self.store, f"{self.key}[{i}]", 1)

    @property
    def first(self):
        return self.nth(0)

    async def count(self):
        return self._count

    async def fill(self, v):
        self.store[self.key] = v

    async def input_value(self):
        return self.store.get(self.key, "")

    async def check(self):
        self.store[self.key + ".checked"] = True

    async def click(self, timeout=None):
        self.store["clicked"] = self.store.get("clicked", []) + [self.key]


class FakePage:
    """textarea 값 저장소 + 모달 시뮬레이션. content() 는 job id 스크립트를 흉내낸다."""

    def __init__(self, job_id: int, loc, facts=5, prefilled_turns=3):
        self.job_id, self.loc, self.facts_n = job_id, loc, facts
        self.store: dict = {}
        for n in range(prefilled_turns):  # 화면에는 초안 턴이 미리 채워져 있다
            self.store[f"q[{n}]"] = f"user{n + 1}"
            self.store[f"a[{n}]"] = f"assistant{n + 1}"
        self.store["ins[0]"], self.store["ins[1]"], self.store["ins[2]"] = "음식", "장난기가 많은 어린아이", "원래 task"

    async def content(self):
        return f"<script>const vqaCotList = [{{\"id\": {self.job_id}}}];</script>"

    def locator(self, sel):
        m = {
            self.loc.plain_textarea: ("plain", 4), self.loc.facts_textarea: ("facts", self.facts_n),
            self.loc.question_textarea: ("q", 6), self.loc.answer_textarea: ("a", 6), self.loc.radio: ("radio", 2),
            self.loc.instruction_textarea: ("ins", 3), self.loc.submit_button: ("submit", 1),
            self.loc.confirm_modal: ("confirm", 1), self.loc.confirm_modal_text: ("confirm_text", 1),
            self.loc.alert_modal: ("alert", 1), self.loc.alert_text: ("alert_text", 1), self.loc.alert_close_button: ("alert_btn", 1),
        }
        key, n = m.get(sel, (sel, 0))
        return ModalAwareLocator(self.store, key, n)

    async def wait_for_load_state(self, *a, **k): ...


class ModalAwareLocator(FakeLocator):
    async def wait_for(self, state=None, timeout=None): ...

    async def inner_text(self):
        return {"confirm_text": "해당 작업 내용을 제출하시겠습니까?", "alert_text": "저장되었습니다."}.get(self.key.split("[")[0], "")

    def locator(self, sel):  # confirm.locator(ok button)
        return FakeLocator(self.store, "confirm_ok", 1)


@pytest.fixture
def final(sample_draft):
    f = FinalDraft.from_draft(sample_draft)
    f.instruction.archetype = "쇼핑"
    f.instruction.task = "장난기가 많은 어린아이가 찾는 물건에 닿을 수 있도록 ..."
    f.dialogue.turns = f.dialogue.turns[:2]  # 턴 3 삭제
    f.dialogue.turns[1].user = "수정된 질문"  # 사이클 6
    return f


async def test_approve_fills_instruction_and_clears_dropped_turn(final):
    loc = field_locators()
    page = FakePage(158448, loc)
    rec = await Submitter(loc).approve(page, final, 158448)
    assert rec.kind is SubmissionKind.APPROVE and rec.success and "저장되었습니다" in rec.response_message
    s = page.store
    assert s["ins[0]"] == "쇼핑" and s["ins[2]"].startswith("장난기가 많은 어린아이가 찾는") and s["ins[1]"] == "장난기가 많은 어린아이"
    assert s["plain[0]"] == final.scene and s["plain[3]"] == final.cot3
    assert s["facts[4]"] == final.facts[4]
    assert s["q[0]"] == final.dialogue.turns[0].user and s["a[1]"] == final.dialogue.turns[1].assistant
    assert s["q[1]"] == "수정된 질문" and rec.payload_snapshot["turn_2_user"] == "수정된 질문"
    assert s["q[2]"] == "" and s["a[2]"] == ""  # 삭제된 턴은 비움
    assert s["radio[0].checked"] and "submit[0]" in s["clicked"][0]
    assert rec.payload_snapshot["turn_3_assistant"] == "" and rec.payload_snapshot["archetype"] == "쇼핑"


async def test_approve_aborts_when_job_changed(final):
    loc = field_locators()
    page = FakePage(999, loc)
    rec = await Submitter(loc).approve(page, final, 158448)
    assert not rec.success and "바뀌었습니다" in rec.error and page.store.get("clicked") is None


async def test_approve_rejects_when_fact_fields_fewer(final):
    loc = field_locators()
    page = FakePage(158448, loc, facts=4)
    rec = await Submitter(loc).approve(page, final, 158448)
    assert not rec.success and "적습니다" in rec.error
