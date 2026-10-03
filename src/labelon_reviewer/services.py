"""서비스 계층 S-01~S-07 (services.md). 컴포넌트를 조합해 스토리 하나를 완결한다."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any, Protocol

from .config import AppConfig
from .diff import diff as compute_diff
from .domain import (
    DatasetInfo,
    Draft,
    FinalDraft,
    IllegalTransition,
    ItemExpired,
    LoginRequired,
    ModelCallError,
    NoJobAvailable,
    PageStructureError,
    ReviewItem,
    SourceItem,
    SubmissionKind,
    SubmissionRecord,
    SubmitError,
    utcnow,
)
from .domain import (
    ReviewEvent as E,
)
from .domain import (
    ReviewState as S,
)
from .history import HistoryRepository
from .images import ImageService
from .judge import JudgeStage
from .labelon import parser
from .revise import ReviseStage
from .state import ReviewStateMachine

log = logging.getLogger(__name__)

WARN_SECONDS = 600
SLOW_FETCH_SECONDS = 180


# ------------------------------------------------------------ 브라우저 프로토콜 (테스트에서 Fake 로 대체)
class BrowserLike(Protocol):
    page: Any

    def is_alive(self) -> bool: ...
    async def start(self) -> None: ...
    async def close(self) -> None: ...
    async def is_logged_in(self) -> bool: ...
    async def show_login_page(self) -> None: ...
    async def wait_for_login(self, timeout_s: int = ..., poll_s: float = ...) -> None: ...
    async def open_job_page(self, dataset_id: int) -> tuple[str, str]: ...
    async def fetch_bytes(self, url: str) -> bytes: ...
    async def show_image(self, image_url: str, caption: str = "") -> None: ...
    async def content(self) -> str: ...
    async def fetch_project_home(self) -> str: ...


class SubmitterLike(Protocol):
    async def approve(self, page, final: FinalDraft, expected_job_id: int) -> SubmissionRecord: ...
    async def impossible(self, page, reason: str, expected_job_id: int) -> SubmissionRecord: ...
    async def release(self, page, item) -> SubmissionRecord: ...


@dataclass
class AppContext:
    config: AppConfig
    sm: ReviewStateMachine
    repo: HistoryRepository
    browser: BrowserLike
    images: ImageService
    judge: JudgeStage
    revise: ReviseStage
    submitter: SubmitterLike
    fetch_task: asyncio.Task | None = None
    login_watch_task: asyncio.Task | None = None  # 사이클 7: 재로그인 감시
    background: list[asyncio.Task] = field(default_factory=list)
    shutdown_event: asyncio.Event = field(default_factory=asyncio.Event)
    datasets: DatasetState = field(default_factory=lambda: DatasetState())


@dataclass
class DatasetState:
    """진행중 데이터셋 목록과 선택값 (사이클 2)."""

    datasets: list[DatasetInfo] = field(default_factory=list)
    selected_id: int | None = None
    updated_at: str | None = None
    error: str | None = None

    def find(self, dataset_id: int) -> DatasetInfo | None:
        return next((d for d in self.datasets if d.dataset_id == dataset_id), None)


# ============================================================ S-08 DatasetService (cycle 2)
SELECTABLE_STATES = (S.READY, S.DONE, S.ERROR, S.EXPIRED)


class DatasetService:
    def __init__(self, ctx: AppContext) -> None:
        self.ctx = ctx
        self.state = ctx.datasets

    @property
    def _path(self):
        return self.ctx.config.data_dir / "ui-state.json"

    def load_saved(self) -> int | None:
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            v = data.get("selected_dataset_id")
            return int(v) if v is not None else None
        except (OSError, ValueError, json.JSONDecodeError):
            return None

    def save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(json.dumps({"selected_dataset_id": self.state.selected_id}, ensure_ascii=False), encoding="utf-8")
        except OSError as e:  # pragma: no cover
            log.warning("ui-state save failed: %s", e)

    def _apply_initial_selection(self) -> None:
        """저장값 → config.dataset_id → 목록 첫 항목 순으로 선택. 목록이 비면 config.dataset_id 폴백."""
        ids = [d.dataset_id for d in self.state.datasets]
        cur = self.state.selected_id
        if cur is not None and cur in ids:
            return
        saved = self.load_saved()
        cfg_id = self.ctx.config.dataset_id
        if saved in ids:
            self.state.selected_id = saved
        elif cfg_id in ids:
            self.state.selected_id = cfg_id
        elif ids:
            self.state.selected_id = ids[0]
        else:
            self.state.selected_id = saved or cfg_id
        self.save()

    async def refresh(self) -> DatasetState:
        try:
            html = await self.ctx.browser.fetch_project_home()
            self.state.datasets = await asyncio.to_thread(parser.parse_dataset_list, html)
            self.state.updated_at = utcnow().isoformat()
            self.state.error = None
            log.info("datasets refreshed: %s", [d.dataset_id for d in self.state.datasets])
        except LoginRequired as e:
            self.state.error = f"목록을 읽으려면 로그인이 필요합니다: {e}"
            self.ctx.sm.set_flags(login_required=True)
            SessionService(self.ctx).start_login_watch()
        except PageStructureError as e:
            self.state.error = f"프로젝트 홈 구조를 해석하지 못했습니다: {e}"
        except Exception as e:  # 네트워크 등
            log.warning("dataset refresh failed: %s", e)
            self.state.error = f"목록 조회 실패: {e}"
        self._apply_initial_selection()
        self.ctx.sm.publish()
        return self.state

    def select(self, dataset_id: int) -> DatasetState:
        if self.ctx.sm.state not in SELECTABLE_STATES:
            raise IllegalTransition("검토 중인 건이 있어 데이터셋을 바꿀 수 없습니다. 먼저 제출·불가·건너뛰기로 정리하세요")
        ids = [d.dataset_id for d in self.state.datasets]
        if ids and dataset_id not in ids:
            raise ValueError(f"목록에 없는 데이터셋입니다: {dataset_id}")
        if not ids and dataset_id != self.ctx.config.dataset_id:
            raise ValueError("목록이 비어 있어 설정 기본 데이터셋만 선택할 수 있습니다")
        self.state.selected_id = dataset_id
        self.save()
        self.ctx.sm.publish()
        return self.state

    def effective_id(self) -> int:
        return self.state.selected_id or self.ctx.config.dataset_id

    def selected_name(self) -> str:
        d = self.state.find(self.effective_id())
        return d.dataset_name if d else f"설정 기본값 (datasetId={self.effective_id()})"

    def snapshot(self) -> dict[str, Any]:
        return {
            "datasets": [d.model_dump() | {"supported": d.supported} for d in self.state.datasets],
            "selected_dataset_id": self.effective_id(), "selected_dataset_name": self.selected_name(),
            "datasets_updated_at": self.state.updated_at, "datasets_error": self.state.error,
        }


# ============================================================ S-01 SessionService
class SessionService:
    def __init__(self, ctx: AppContext) -> None:
        self.ctx = ctx

    async def ensure_login(self) -> None:
        """시작 시: 로그인 여부 확인 → 미로그인이면 로그인 페이지 표시 후 사용자가 로그인할 때까지 대기."""
        sm = self.ctx.sm
        try:
            if not await self.ctx.browser.is_logged_in():
                sm.set_flags(login_required=True)
                await self.ctx.browser.show_login_page()
                await self.ctx.browser.wait_for_login()
            sm.set_flags(login_required=False)
            await DatasetService(self.ctx).refresh()
        except LoginRequired as e:
            log.warning("login wait ended: %s", e)
            sm.add_warning(f"로그인이 필요합니다: {e}")

    async def liveness_loop(self, interval: float = 5.0) -> None:
        while not self.ctx.shutdown_event.is_set():
            alive = self.ctx.browser.is_alive()
            if alive != self.ctx.sm.current().browser_alive:
                self.ctx.sm.set_flags(browser_alive=alive)
                if not alive:
                    self.ctx.sm.add_warning("브라우저 창이 닫혔습니다. '브라우저 다시 열기'를 누르세요")
            await asyncio.sleep(interval)

    async def reopen_browser(self) -> None:
        await self.ctx.browser.close()
        await self.ctx.browser.start()
        self.ctx.sm.set_flags(browser_alive=True)
        await self.ensure_login()

    # 사이클 7: 작업 중 세션 만료 → 사용자가 Chrome 에서 재로그인하면 자동 복구
    def start_login_watch(self, interval: float = 5.0) -> None:
        t = self.ctx.login_watch_task
        if t is not None and not t.done():
            return
        try:
            self.ctx.login_watch_task = asyncio.create_task(self.watch_login(interval), name="login-watch")
        except RuntimeError:  # 실행 중인 루프 없음(동기 테스트)
            self.ctx.login_watch_task = None

    async def watch_login(self, interval: float = 5.0) -> None:
        sm = self.ctx.sm
        while not self.ctx.shutdown_event.is_set() and sm.current().login_required:
            await asyncio.sleep(interval)
            if not self.ctx.browser.is_alive():
                continue
            try:
                ok = await self.ctx.browser.is_logged_in()
            except Exception as e:  # 네트워크 등
                log.debug("login watch check failed: %s", e)
                ok = False
            if ok:
                log.info("re-login detected")
                sm.set_flags(login_required=False)
                sm.add_warning("로그인이 확인되었습니다. 계속 진행할 수 있습니다")
                self.ctx.datasets.error = None
                await DatasetService(self.ctx).refresh()
                return


# ============================================================ S-02 FetchAndAnalyzeService
class FetchAndAnalyzeService:
    def __init__(self, ctx: AppContext) -> None:
        self.ctx = ctx

    def start(self) -> asyncio.Task:
        if self.ctx.fetch_task and not self.ctx.fetch_task.done():
            raise IllegalTransition("이미 가져오기·분석이 진행 중입니다")
        if self.ctx.sm.state not in (S.READY, S.DONE, S.ERROR, S.EXPIRED):
            raise IllegalTransition(f"{self.ctx.sm.state.value} 상태에서는 가져올 수 없습니다")
        self.ctx.fetch_task = asyncio.create_task(self.run(), name="fetch-analyze")
        return self.ctx.fetch_task

    async def run(self) -> None:
        ctx, sm, cfg = self.ctx, self.ctx.sm, self.ctx.config
        t0 = time.monotonic()
        item_id: int | None = None
        try:
            sm.transition(E.FETCH_STARTED)
            if not ctx.browser.is_alive():
                raise NoJobAvailable("BROWSER_CLOSED", "브라우저 창이 닫혀 있습니다. 다시 열어 주세요")
            dataset_id = DatasetService(ctx).effective_id()
            kind, html = await ctx.browser.open_job_page(dataset_id)
            if kind == "LOGIN":
                sm.set_flags(login_required=True)
                ctx.datasets.error = "로그인이 만료되었습니다. 재로그인 후 새로고침하세요"
                SessionService(ctx).start_login_watch()
                raise NoJobAvailable(kind, "로그인이 만료되었습니다. Chrome 창에서 다시 로그인하면 자동으로 복구됩니다")
            if kind != "JOB":
                raise NoJobAvailable(kind)
            source, draft = parser.parse_html(html, cfg.labelon.server_tz_offset_hours)
            item_id = await asyncio.to_thread(ctx.repo.save_item, source, draft, "JUDGING")
            deadline = source.job_date + timedelta(minutes=cfg.labelon.job_time_limit_minutes)
            sm.transition(E.PARSED, {"item_id": item_id, "source": source, "draft": draft, "deadline": deadline,
                                     "final": FinalDraft.from_draft(draft)})
            await self._analyze(item_id, source, draft, t0)
        except asyncio.CancelledError:
            log.info("fetch task cancelled")
            if item_id is not None:
                await asyncio.to_thread(ctx.repo.mark_state, item_id, "CANCELLED", "fetch cancelled")
            try:
                sm.transition(E.RESET)
            except IllegalTransition:
                pass
            raise
        except NoJobAvailable as e:
            sm.transition(E.FAILED, {"error": str(e)})
        except (PageStructureError, ItemExpired) as e:
            if item_id is not None:
                await asyncio.to_thread(ctx.repo.mark_state, item_id, "ERROR", str(e))
            sm.transition(E.FAILED, {"error": str(e)})
        except Exception as e:  # 예기치 못한 오류도 UI 에 표시
            log.exception("fetch/analyze unexpected error")
            if item_id is not None:
                await asyncio.to_thread(ctx.repo.mark_state, item_id, "ERROR", str(e))
            try:
                sm.transition(E.FAILED, {"error": f"예기치 못한 오류: {e}"})
            except IllegalTransition:
                pass

    async def _analyze(self, item_id: int, source: SourceItem, draft: Draft, t0: float) -> None:
        """이미지 → 판정 → 수정 → 최종안. run() 과 reanalyze() 가 공유한다 (JUDGING 상태에서 호출)."""
        ctx, sm = self.ctx, self.ctx.sm
        images = await ctx.images.fetch(ctx.browser.fetch_bytes, source)
        sm.current().image_paths = images
        sm.publish()
        if ctx.config.chrome.image_tab:  # 사이클 9: Chrome 이미지 전용 탭에 원본 사진 표시
            try:
                await ctx.browser.show_image(source.image_url, source.org_file_name)
            except Exception as e:
                log.warning("image tab failed: %s", e)

        warnings: list[str] = []
        judge = None
        try:
            judge = await ctx.judge.run(images, source, draft, warnings)
            await asyncio.to_thread(ctx.repo.save_judge, item_id, judge)
            sm.current().judge = judge
            for w in warnings:
                sm.current().warnings.append(w)
            sm.transition(E.JUDGED, {"needs_revision": judge.needs_revision})
        except ModelCallError as e:
            log.warning("judge failed: %s", e)
            sm.current().warnings.append(f"판정 모델 호출 실패: {e}. 초안 그대로 검토합니다")
            sm.transition(E.REVIEW_READY)

        revised = None
        if judge is not None:
            try:
                revised = await ctx.revise.run(images, source, draft, judge)  # 수정 불필요면 모델 호출 없이 skipped
                await asyncio.to_thread(ctx.repo.save_revision, item_id, revised)
                sm.current().revised = revised
                if sm.state is S.REVISING:
                    sm.transition(E.REVISED)
            except ModelCallError as e:
                log.warning("revise failed: %s", e)
                sm.current().warnings.append(f"수정 모델 호출 실패: {e}. 초안 그대로 검토합니다")
                if sm.state is S.REVISING:
                    sm.transition(E.REVIEW_READY)

        base = revised.draft if (revised and not revised.skipped) else draft
        final = FinalDraft.from_draft(base)
        cur = sm.current()
        cur.final = final
        cur.diffs = compute_diff(draft, final.as_draft())
        await asyncio.to_thread(ctx.repo.save_final, item_id, final)
        await asyncio.to_thread(ctx.repo.mark_state, item_id, "REVIEW")
        elapsed = time.monotonic() - t0
        if elapsed > SLOW_FETCH_SECONDS:
            cur.warnings.append(f"분석에 {int(elapsed)}초가 걸렸습니다 (목표 90초)")
        sm.publish()
        log.info("analyze done in %.1fs (item_id=%s)", elapsed, item_id)

    # ---- 사이클 7: 다시 판독
    def start_reanalyze(self) -> asyncio.Task:
        if self.ctx.fetch_task and not self.ctx.fetch_task.done():
            raise IllegalTransition("이미 가져오기·분석이 진행 중입니다")
        if self.ctx.sm.state is not S.REVIEW:
            raise IllegalTransition("검토 대기 상태에서만 다시 판독할 수 있습니다")
        self.ctx.fetch_task = asyncio.create_task(self.reanalyze(), name="reanalyze")
        return self.ctx.fetch_task

    async def reanalyze(self) -> None:
        """현재 건의 사진·서버 초안으로 판정·수정을 다시 실행한다. item_id·마감은 유지, 사람 편집은 초기화."""
        ctx, sm = self.ctx, self.ctx.sm
        cur = sm.current()
        assert cur.source is not None and cur.draft is not None and cur.item_id is not None
        item_id, source, draft = cur.item_id, cur.source, cur.draft
        t0 = time.monotonic()
        try:
            sm.transition(E.REANALYZE)
            cur = sm.current()
            cur.warnings, cur.judge, cur.revised, cur.submission, cur.error = [], None, None, None, None
            await asyncio.to_thread(ctx.repo.mark_state, item_id, "JUDGING", "reanalyze")
            await self._analyze(item_id, source, draft, t0)
        except asyncio.CancelledError:
            await asyncio.to_thread(ctx.repo.mark_state, item_id, "CANCELLED", "reanalyze cancelled")
            try:
                sm.transition(E.RESET)
            except IllegalTransition:
                pass
            raise
        except Exception as e:
            log.exception("reanalyze error")
            await asyncio.to_thread(ctx.repo.mark_state, item_id, "ERROR", str(e))
            try:
                sm.transition(E.FAILED, {"error": f"다시 판독 실패: {e}"})
            except IllegalTransition:
                pass

    async def cancel(self) -> None:
        t = self.ctx.fetch_task
        if t and not t.done():
            t.cancel()
            try:
                await t
            except (asyncio.CancelledError, Exception):
                pass


# ============================================================ S-03 EditService
class EditService:
    def __init__(self, ctx: AppContext) -> None:
        self.ctx = ctx

    async def edit(self, field_name: str, value: str) -> ReviewItem:
        sm = self.ctx.sm
        if sm.state is not S.REVIEW:
            raise IllegalTransition("검토 대기 상태에서만 편집할 수 있습니다")
        cur = sm.current()
        assert cur.final is not None and cur.draft is not None
        try:
            cur.final.set_field(field_name, value)
        except KeyError as e:
            raise IllegalTransition(f"편집할 수 없는 필드: {field_name}") from e
        cur.final.edited_by_user = True
        cur.final.updated_at = utcnow()
        cur.diffs = compute_diff(cur.draft, cur.final.as_draft())
        if cur.item_id is not None:
            await asyncio.to_thread(self.ctx.repo.save_final, cur.item_id, cur.final)
        return sm.transition(E.EDITED)

    async def revert_field(self, field_name: str) -> ReviewItem:
        """사이클 8: 해당 항목만 서버 초안 값으로 되돌린다."""
        sm = self.ctx.sm
        if sm.state is not S.REVIEW:
            raise IllegalTransition("검토 대기 상태에서만 되돌릴 수 있습니다")
        cur = sm.current()
        assert cur.final is not None and cur.draft is not None
        try:
            cur.final.set_field(field_name, cur.draft.get_field(field_name))
        except (KeyError, IndexError) as e:
            raise IllegalTransition(f"되돌릴 수 없는 필드: {field_name}") from e
        cur.diffs = compute_diff(cur.draft, cur.final.as_draft())
        cur.final.edited_by_user = any(d.changed for d in cur.diffs)
        cur.final.updated_at = utcnow()
        if cur.item_id is not None:
            await asyncio.to_thread(self.ctx.repo.save_final, cur.item_id, cur.final)
        return sm.transition(E.EDITED)

    async def revert(self) -> ReviewItem:
        sm = self.ctx.sm
        if sm.state is not S.REVIEW:
            raise IllegalTransition("검토 대기 상태에서만 되돌릴 수 있습니다")
        cur = sm.current()
        assert cur.draft is not None
        cur.final = FinalDraft.from_draft(cur.draft)
        cur.diffs = compute_diff(cur.draft, cur.final.as_draft())
        if cur.item_id is not None:
            await asyncio.to_thread(self.ctx.repo.save_final, cur.item_id, cur.final)
        return sm.transition(E.REVERTED)


# ============================================================ S-04 SubmitService
def validate_final(final: Draft, draft: Draft | None = None) -> list[str]:
    """BR-33 승인 전 유효성. draft 가 주어지면 초안에 있던 턴을 통째로 비운 것(삭제)도 차단한다 (사이클 8)."""
    problems = []
    if draft is not None:
        for ot in draft.dialogue.active_turns():
            ft = final.dialogue.turn(ot.turn)
            if ft is None or ft.is_empty():
                problems.append(f"대화 {ot.turn}턴을 삭제할 수 없습니다 (내용을 수정하세요)")
    if not final.scene.strip():
        problems.append("Scene 이 비어 있습니다")
    for i, f in enumerate(final.facts):
        if not f.strip():
            problems.append(f"Fact {i + 1} 이 비어 있습니다")
    for name in ("cot1", "cot2", "cot3"):
        if not getattr(final, name).strip():
            problems.append(f"{name} 이 비어 있습니다")
    for t in final.dialogue.turns:
        if t.user.strip() and not t.assistant.strip():
            problems.append(f"대화 {t.turn}턴 assistant 가 비어 있습니다")
        if t.assistant.strip() and not t.user.strip():
            problems.append(f"대화 {t.turn}턴 user 가 비어 있습니다")
    for k in ("archetype", "persona", "task"):  # 사이클 7
        if not getattr(final.instruction, k).strip():
            problems.append(f"Instruction {k} 이 비어 있습니다")
    return problems


class SubmitService:
    def __init__(self, ctx: AppContext) -> None:
        self.ctx = ctx

    def _precheck(self) -> ReviewItem:
        sm = self.ctx.sm
        if sm.state is S.SUBMITTING:
            raise IllegalTransition("이미 제출 중입니다")
        if sm.state is not S.REVIEW:
            raise IllegalTransition("검토 대기 상태에서만 제출할 수 있습니다")
        cur = sm.current()
        rem = cur.remaining_seconds()
        if rem is not None and rem <= 0:
            sm.transition(E.EXPIRED)
            if cur.item_id is not None:
                self.ctx.repo.mark_state(cur.item_id, "EXPIRED", "expired before submit")
            raise ItemExpired("제한시간이 만료되어 이 건은 반환되었습니다. 다시 가져오세요")
        if not self.ctx.browser.is_alive():
            raise SubmitError("브라우저 창이 닫혀 있습니다")
        return cur

    async def _finish(self, cur: ReviewItem, rec: SubmissionRecord) -> ReviewItem:
        sm = self.ctx.sm
        if cur.item_id is not None:
            await asyncio.to_thread(self.ctx.repo.save_submission, cur.item_id, rec)
        cur.submission = rec
        if rec.success:
            if cur.item_id is not None:
                state = "READY" if rec.kind is SubmissionKind.SKIP else "DONE"
                await asyncio.to_thread(self.ctx.repo.mark_state, cur.item_id, state, rec.kind.value)
            return sm.transition(E.SUBMITTED, {"kind": rec.kind})
        return sm.transition(E.SUBMIT_FAILED, {"error": rec.error or rec.response_message})

    async def approve(self) -> ReviewItem:
        cur = self._precheck()
        assert cur.final is not None and cur.source is not None
        problems = validate_final(cur.final, cur.draft)
        if problems:
            raise SubmitError("; ".join(problems))
        self.ctx.sm.transition(E.SUBMIT_STARTED)
        if cur.item_id is not None:
            await asyncio.to_thread(self.ctx.repo.save_final, cur.item_id, cur.final)
        rec = await self.ctx.submitter.approve(self.ctx.browser.page, cur.final, cur.source.job_id)
        return await self._finish(cur, rec)

    async def impossible(self, reason: str) -> ReviewItem:
        """불가 제출. 사유는 공백(미입력)도 허용한다 (사용자 결정 2026-09-23)."""
        cur = self._precheck()
        assert cur.source is not None
        self.ctx.sm.transition(E.SUBMIT_STARTED)
        rec = await self.ctx.submitter.impossible(self.ctx.browser.page, (reason or "").strip(), cur.source.job_id)
        return await self._finish(cur, rec)

    async def skip(self) -> ReviewItem:
        cur = self._precheck()
        assert cur.source is not None
        self.ctx.sm.transition(E.SUBMIT_STARTED)
        rec = await self.ctx.submitter.release(self.ctx.browser.page, cur.source)
        return await self._finish(cur, rec)


# ============================================================ S-05 DeadlineService
class DeadlineService:
    def __init__(self, ctx: AppContext) -> None:
        self.ctx = ctx
        self._warned_item: int | None = None

    def tick(self) -> None:
        sm = self.ctx.sm
        cur = sm.current()
        if cur.deadline is None or sm.state not in (S.JUDGING, S.REVISING, S.REVIEW):
            return
        rem = cur.remaining_seconds()
        if rem is None:
            return
        if rem <= 0:
            log.warning("item %s expired", cur.item_id)
            sm.transition(E.EXPIRED)
            if cur.item_id is not None:
                self.ctx.repo.mark_state(cur.item_id, "EXPIRED", "deadline passed")
        elif rem < WARN_SECONDS and self._warned_item != cur.item_id:
            self._warned_item = cur.item_id
            sm.add_warning("남은 제한시간이 10분 미만입니다")

    async def loop(self, interval: float = 1.0) -> None:
        while not self.ctx.shutdown_event.is_set():
            try:
                self.tick()
            except Exception:  # pragma: no cover
                log.exception("deadline tick failed")
            await asyncio.sleep(interval)


# ============================================================ S-06 HistoryService
class HistoryService:
    def __init__(self, ctx: AppContext) -> None:
        self.ctx = ctx

    async def list_recent(self, limit: int = 50) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self.ctx.repo.list_recent, limit)

    async def detail(self, item_id: int) -> dict[str, Any] | None:
        return await asyncio.to_thread(self.ctx.repo.get_detail, item_id)

    async def summary(self) -> dict[str, Any]:
        return await asyncio.to_thread(self.ctx.repo.summary)

    async def unfinished(self) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self.ctx.repo.find_unfinished)

    def cleanup_images(self) -> int:
        return self.ctx.images.cleanup(self.ctx.config.cache_retention_days)

    async def cleanup_loop(self, interval: float = 86400.0) -> None:
        while not self.ctx.shutdown_event.is_set():
            try:
                n = await asyncio.to_thread(self.cleanup_images)
                if n:
                    log.info("image cache cleanup removed %d files", n)
            except Exception:  # pragma: no cover
                log.exception("cleanup failed")
            await asyncio.sleep(interval)

    async def on_shutdown(self) -> None:
        cur = self.ctx.sm.current()
        if cur.item_id is not None and cur.state in (S.REVIEW, S.SUBMITTING, S.JUDGING, S.REVISING):
            await asyncio.to_thread(self.ctx.repo.mark_state, cur.item_id, cur.state.value, "server shutdown")


# ============================================================ S-07 ConfigService
class ConfigService:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def public(self) -> dict[str, Any]:
        c = self.config
        return {
            "dataset_id": c.dataset_id, "persona": c.persona, "threshold": c.threshold,
            "models": c.models.model_dump(), "effort": c.effort.model_dump(), "model_backend": c.model_backend,
            "job_time_limit_minutes": c.labelon.job_time_limit_minutes, "archetypes": list(c.archetype_templates),
            "edit_delay_ms": c.ui.edit_delay_ms,
            "archetype_templates": dict(c.archetype_templates),  # 사이클 7: 화면에서 Task 자동 생성
        }
