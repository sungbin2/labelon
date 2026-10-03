import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from labelon_reviewer.domain import (
    IllegalTransition,
    ItemExpired,
    SubmissionKind,
    SubmissionRecord,
    SubmitError,
)
from labelon_reviewer.domain import (
    ReviewState as S,
)
from labelon_reviewer.history import HistoryRepository
from labelon_reviewer.images import ImageService
from labelon_reviewer.judge import JudgeStage
from labelon_reviewer.model.fake import FakeModelClient
from labelon_reviewer.revise import ReviseStage
from labelon_reviewer.services import (
    AppContext,
    DatasetService,
    DeadlineService,
    EditService,
    FetchAndAnalyzeService,
    SessionService,
    SubmitService,
    validate_final,
)
from labelon_reviewer.state import ReviewStateMachine
from tests.conftest import judge_raw_all_true
from tests.test_images import _jpeg


class FakeBrowser:
    def __init__(self, html: str, kind: str = "JOB"):
        self.html, self.kind, self.page, self.alive = html, kind, object(), True

    def is_alive(self):
        return self.alive

    async def start(self): ...
    async def close(self): ...
    async def is_logged_in(self):
        return True

    async def show_login_page(self): ...
    async def wait_for_login(self, timeout_s=0, poll_s=0): ...
    async def open_job_page(self, dataset_id):
        self.opened = getattr(self, "opened", []) + [dataset_id]
        return self.kind, self.html

    async def fetch_bytes(self, url):
        return _jpeg(800, 600)

    async def content(self):
        return self.html

    async def fetch_project_home(self):
        if getattr(self, "home_html", None) is None:
            from tests.conftest import FIXTURES

            self.home_html = (FIXTURES / "project_home_sample.html").read_text(encoding="utf-8")
        return self.home_html


class FakeSubmitter:
    def __init__(self, success=True):
        self.success, self.calls = success, []

    async def approve(self, page, final, job_id):
        self.calls.append(("approve", job_id, final.scene))
        return SubmissionRecord(kind=SubmissionKind.APPROVE, success=self.success, response_message="저장되었습니다." if self.success else "오류")

    async def impossible(self, page, reason, job_id):
        self.calls.append(("impossible", reason))
        return SubmissionRecord(kind=SubmissionKind.IMPOSSIBLE, success=True, response_message="저장되었습니다.")

    async def release(self, page, item):
        self.calls.append(("release", item.job_id))
        return SubmissionRecord(kind=SubmissionKind.SKIP, success=True)


def make_ctx(config, tmp_path, html, *, judge_raw=None, fail_judge=False, fail_revise=False, kind="JOB", success=True):
    model = FakeModelClient(config, judge_raw=judge_raw, fail_judge=fail_judge, fail_revise=fail_revise)
    ctx = AppContext(
        config=config, sm=ReviewStateMachine(), repo=HistoryRepository(":memory:"), browser=FakeBrowser(html, kind),
        images=ImageService(tmp_path / "c", tmp_path / "r", 400), judge=JudgeStage(config, model),
        revise=ReviseStage(config, model), submitter=FakeSubmitter(success),
    )
    ctx.model = model  # type: ignore[attr-defined]
    return ctx


async def run_fetch(ctx):
    await FetchAndAnalyzeService(ctx).start()
    # 픽스처의 jobDate(2026-09-23 09:52 KST)는 이미 지났으므로 테스트에서는 마감을 미래로 옮긴다
    cur = ctx.sm.current()
    if cur.deadline is not None and ctx.sm.state is S.REVIEW:
        cur.deadline = datetime.now(UTC) + timedelta(minutes=50)


async def test_full_flow_no_revision(config, tmp_path, job_page_html):
    ctx = make_ctx(config, tmp_path, job_page_html, judge_raw=judge_raw_all_true())
    await run_fetch(ctx)
    cur = ctx.sm.current()
    assert ctx.sm.state is S.REVIEW and cur.judge.consistency_score == 100 and cur.revised.skipped
    assert cur.final.scene == cur.draft.scene and all(not d.changed for d in cur.diffs)
    assert ctx.model.calls == ["judge"]
    assert cur.source.job_date == datetime(2026, 9, 23, 0, 52, 33, tzinfo=UTC)  # 마감 = job_date + 60분 (테스트에서 미래로 이동됨)
    rows = ctx.repo.list_recent()
    assert rows[0]["state"] == "REVIEW" and rows[0]["score"] == 100


async def test_flow_with_revision_and_submit(config, tmp_path, job_page_html):
    raw = judge_raw_all_true()
    raw["facts"][1]["verdict"] = "FALSE"
    ctx = make_ctx(config, tmp_path, job_page_html, judge_raw=raw)
    await run_fetch(ctx)
    assert ctx.sm.state is S.REVIEW and ctx.model.calls == ["judge", "revise"] and not ctx.sm.current().revised.skipped
    # 편집 → 승인
    await EditService(ctx).edit("turn_1_user", "질문을 바꿨어요")  # 사이클 6
    assert ctx.sm.current().final.dialogue.turn(1).user == "질문을 바꿨어요"
    assert next(d for d in ctx.sm.current().diffs if d.field == "turn_1_user").changed
    await EditService(ctx).edit("fact_2", "수정된 팩트.")
    assert ctx.sm.current().final.facts[1] == "수정된 팩트." and any(d.changed for d in ctx.sm.current().diffs)
    await SubmitService(ctx).approve()
    assert ctx.sm.state is S.DONE
    assert ctx.submitter.calls[0][0] == "approve" and ctx.submitter.calls[0][1] == 158448
    detail = ctx.repo.get_detail(1)
    assert detail["submissions"][0]["kind"] == "APPROVE" and detail["state"] == "DONE"


async def test_model_failure_falls_back_to_draft(config, tmp_path, job_page_html):
    ctx = make_ctx(config, tmp_path, job_page_html, fail_judge=True)
    await run_fetch(ctx)
    cur = ctx.sm.current()
    assert ctx.sm.state is S.REVIEW and cur.judge is None and cur.final.as_draft() == cur.draft
    assert any("판정 모델 호출 실패" in w for w in cur.warnings)


async def test_no_job_available(config, tmp_path):
    ctx = make_ctx(config, tmp_path, "<html/>", kind="HOME")
    await run_fetch(ctx)
    assert ctx.sm.state is S.ERROR and "HOME" in ctx.sm.current().error


async def test_login_expired(config, tmp_path):
    ctx = make_ctx(config, tmp_path, '<input type="password">', kind="LOGIN")
    await run_fetch(ctx)
    assert ctx.sm.state is S.ERROR and ctx.sm.current().login_required
    # 사이클 7: 감시 태스크가 시작되고, 브라우저가 로그인되면 플래그가 풀린다
    assert ctx.login_watch_task is not None
    ctx.login_watch_task.cancel()
    await SessionService(ctx).watch_login(interval=0.01)  # FakeBrowser.is_logged_in → True
    assert not ctx.sm.current().login_required and any("로그인이 확인" in w for w in ctx.sm.current().warnings)


async def test_reanalyze_keeps_item_and_resets_edits(config, tmp_path, job_page_html):
    raw = judge_raw_all_true()
    raw["facts"][1]["verdict"] = "FALSE"
    ctx = make_ctx(config, tmp_path, job_page_html, judge_raw=raw)
    await run_fetch(ctx)
    item_id = ctx.sm.current().item_id
    await EditService(ctx).edit("scene", "사람이 고친 장면")
    with pytest.raises(IllegalTransition):
        FetchAndAnalyzeService(make_ctx(config, tmp_path, job_page_html)).start_reanalyze()  # READY 에서는 불가
    await FetchAndAnalyzeService(ctx).start_reanalyze()
    cur = ctx.sm.current()
    assert ctx.sm.state is S.REVIEW and cur.item_id == item_id and cur.judge is not None
    assert cur.final.scene != "사람이 고친 장면" and not cur.final.edited_by_user
    assert ctx.model.calls.count("judge") == 2


async def test_submit_preconditions(config, tmp_path, job_page_html):
    ctx = make_ctx(config, tmp_path, job_page_html, judge_raw=judge_raw_all_true())
    with pytest.raises(IllegalTransition):
        await SubmitService(ctx).approve()  # READY 상태
    await run_fetch(ctx)
    ctx.sm.current().final.scene = ""
    with pytest.raises(SubmitError):
        await SubmitService(ctx).approve()
    assert ctx.sm.state is S.REVIEW


async def test_expired_blocks_submit(config, tmp_path, job_page_html):
    ctx = make_ctx(config, tmp_path, job_page_html, judge_raw=judge_raw_all_true())
    await run_fetch(ctx)
    ctx.sm.current().deadline = datetime.now(UTC) - timedelta(seconds=1)
    with pytest.raises(ItemExpired):
        await SubmitService(ctx).approve()
    assert ctx.sm.state is S.EXPIRED and ctx.repo.list_recent()[0]["state"] == "EXPIRED"


async def test_skip_and_impossible(config, tmp_path, job_page_html):
    ctx = make_ctx(config, tmp_path, job_page_html, judge_raw=judge_raw_all_true())
    await run_fetch(ctx)
    await SubmitService(ctx).skip()
    assert ctx.sm.state is S.READY and ctx.submitter.calls[-1] == ("release", 158448)
    await run_fetch(ctx)
    await SubmitService(ctx).impossible("   ")  # 공백 사유 허용
    assert ctx.sm.state is S.DONE and ctx.submitter.calls[-1] == ("impossible", "")


async def test_submit_failure_returns_to_review(config, tmp_path, job_page_html):
    ctx = make_ctx(config, tmp_path, job_page_html, judge_raw=judge_raw_all_true(), success=False)
    await run_fetch(ctx)
    await SubmitService(ctx).approve()
    assert ctx.sm.state is S.REVIEW and ctx.sm.current().submission.success is False


async def test_deadline_tick(config, tmp_path, job_page_html):
    ctx = make_ctx(config, tmp_path, job_page_html, judge_raw=judge_raw_all_true())
    await run_fetch(ctx)
    ds = DeadlineService(ctx)
    ctx.sm.current().deadline = datetime.now(UTC) + timedelta(seconds=300)
    ds.tick()
    assert any("10분 미만" in w for w in ctx.sm.current().warnings) and ctx.sm.state is S.REVIEW
    ctx.sm.current().deadline = datetime.now(UTC) - timedelta(seconds=1)
    ds.tick()
    assert ctx.sm.state is S.EXPIRED


async def test_duplicate_fetch_rejected(config, tmp_path, job_page_html):
    ctx = make_ctx(config, tmp_path, job_page_html, judge_raw=judge_raw_all_true())
    svc = FetchAndAnalyzeService(ctx)
    task = svc.start()
    with pytest.raises(IllegalTransition):
        svc.start()
    await task
    await asyncio.sleep(0)


def test_validate_final(sample_draft):
    assert validate_final(sample_draft) == []
    d = sample_draft.model_copy(deep=True)
    d.dialogue.turns[0].user = ""  # 사이클 6: assistant 는 있는데 질문이 비면 차단
    assert any("1턴 user 가 비어" in p for p in validate_final(d))
    d.instruction.task = " "  # 사이클 7
    assert any("Instruction task" in p for p in validate_final(d))
    # 사이클 8: 초안에 있던 턴을 통째로 비우면 삭제로 보아 차단
    e = sample_draft.model_copy(deep=True)
    e.dialogue.turns[2].user = ""
    e.dialogue.turns[2].assistant = ""
    assert any("3턴을 삭제할 수 없습니다" in p for p in validate_final(e, sample_draft))
    assert validate_final(sample_draft, sample_draft) == []
    sample_draft.facts[2] = ""
    sample_draft.dialogue.turns[0].assistant = ""
    problems = validate_final(sample_draft)
    assert any("Fact 3" in p for p in problems) and any("1턴" in p for p in problems)


async def test_revert_field_only_restores_that_field(config, tmp_path, job_page_html):
    ctx = make_ctx(config, tmp_path, job_page_html, judge_raw=judge_raw_all_true())
    await run_fetch(ctx)
    svc = EditService(ctx)
    await svc.edit("fact_2", "고친 팩트")
    await svc.edit("scene", "고친 장면")
    await svc.revert_field("fact_2")
    cur = ctx.sm.current()
    assert cur.final.facts[1] == cur.draft.facts[1] and cur.final.scene == "고친 장면" and cur.final.edited_by_user
    await svc.revert_field("scene")
    assert not ctx.sm.current().final.edited_by_user
    with pytest.raises(IllegalTransition):
        await svc.revert_field("nope")


# ---------------------------------------------------------------- cycle 2: 데이터셋 선택
async def test_dataset_refresh_and_initial_selection(config, tmp_path, job_page_html):
    ctx = make_ctx(config, tmp_path, job_page_html, judge_raw=judge_raw_all_true())
    svc = DatasetService(ctx)
    st = await svc.refresh()
    assert [d.dataset_id for d in st.datasets] == [688, 687, 686, 685, 684, 682] and st.error is None
    assert svc.effective_id() == 688  # config.dataset_id 가 목록에 있음
    assert (config.data_dir / "ui-state.json").exists()
    assert svc.selected_name().endswith("(어린이3)")


async def test_dataset_select_rules_and_persistence(config, tmp_path, job_page_html):
    ctx = make_ctx(config, tmp_path, job_page_html, judge_raw=judge_raw_all_true())
    svc = DatasetService(ctx)
    await svc.refresh()
    svc.select(685)
    assert svc.effective_id() == 685 and svc.load_saved() == 685
    with pytest.raises(ValueError):
        svc.select(12345)
    # 다음 실행: 저장값이 우선
    ctx2 = make_ctx(config, tmp_path, job_page_html, judge_raw=judge_raw_all_true())
    svc2 = DatasetService(ctx2)
    await svc2.refresh()
    assert svc2.effective_id() == 685
    # 검토 중에는 변경 불가
    await run_fetch(ctx2)
    assert ctx2.browser.opened == [685]  # 선택한 데이터셋으로 작업 화면을 연다
    with pytest.raises(IllegalTransition):
        svc2.select(688)


async def test_dataset_refresh_failure_falls_back(config, tmp_path, job_page_html):
    ctx = make_ctx(config, tmp_path, job_page_html, judge_raw=judge_raw_all_true())
    ctx.browser.home_html = "<html><body>no panel</body></html>"
    svc = DatasetService(ctx)
    st = await svc.refresh()
    assert st.datasets == [] and "프로젝트 홈 구조" in st.error
    assert svc.effective_id() == config.dataset_id and "설정 기본값" in svc.selected_name()
    with pytest.raises(ValueError):
        svc.select(687)
    svc.select(config.dataset_id)


async def test_ensure_login_refreshes_datasets(config, tmp_path, job_page_html):
    from labelon_reviewer.services import SessionService

    ctx = make_ctx(config, tmp_path, job_page_html, judge_raw=judge_raw_all_true())
    await SessionService(ctx).ensure_login()
    assert len(ctx.datasets.datasets) == 6 and ctx.sm.current().login_required is False


# ---------------------------------------------------------------- cycle 3: 가이드 반영 흐름
async def test_flow_with_archetype_correction_and_turn_drop(config, tmp_path, job_page_html):
    config.revision_rules.allow_turn_drop = True  # 사이클 8: 기본은 삭제 금지
    raw = judge_raw_all_true()
    raw["archetype_suggestion"] = {"fits": False, "suggested": "쇼핑", "reason": "QA 가 물건 찾기"}
    raw["dialogue_turns"][2]["beyond_cot3"] = True
    ctx = make_ctx(config, tmp_path, job_page_html, judge_raw=raw)
    from labelon_reviewer.model.fake import default_revise_raw

    base = ctx.sm  # noqa: F841
    # Fake 는 draft 를 받으므로 revise_raw 는 호출 시점의 초안으로 만들 수 없어 고정 값 사용
    ctx.model.revise_raw = None
    orig_revise = ctx.model.revise

    async def revise_with_drop(image, item, draft, judge, corrected=None):
        r = default_revise_raw(draft)
        r["dialogue_assistant"][2]["drop"] = True
        ctx.model.revise_raw = r
        return await orig_revise(image, item, draft, judge, corrected)

    ctx.model.revise = revise_with_drop
    await run_fetch(ctx)
    cur = ctx.sm.current()
    assert ctx.sm.state is S.REVIEW and cur.revised.instruction_changed and cur.revised.dropped_turns == [3]
    assert cur.final.instruction.archetype == "쇼핑" and len(cur.final.dialogue.active_turns()) == 2
    d = {x.field: x for x in cur.diffs}
    assert d["archetype"].changed and d["task"].changed and d["turn_3_assistant"].changed
    # 되돌리기 → 원본 Instruction·턴 복원
    await EditService(ctx).revert()
    cur = ctx.sm.current()
    assert cur.final.instruction.archetype == "음식" and len(cur.final.dialogue.active_turns()) == 3
