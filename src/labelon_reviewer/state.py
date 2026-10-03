"""상태 기계 C-10 (business-logic-model.md 5절 전이표)."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from .domain import IllegalTransition, ReviewItem, SubmissionKind, utcnow
from .domain import ReviewEvent as E
from .domain import ReviewState as S

log = logging.getLogger(__name__)

Subscriber = Callable[[ReviewItem], Awaitable[None]]

# (state, event) -> next state ("*" = payload 로 결정)
TRANSITIONS: dict[tuple[S, E], S | str] = {
    (S.READY, E.FETCH_STARTED): S.FETCHING,
    (S.READY, E.RESET): S.READY,
    (S.DONE, E.FETCH_STARTED): S.FETCHING,
    (S.DONE, E.RESET): S.READY,
    (S.ERROR, E.RESET): S.READY,
    (S.ERROR, E.FETCH_STARTED): S.FETCHING,
    (S.EXPIRED, E.RESET): S.READY,
    (S.EXPIRED, E.FETCH_STARTED): S.FETCHING,
    (S.FETCHING, E.PARSED): S.JUDGING,
    (S.FETCHING, E.REVIEW_READY): S.REVIEW,
    (S.FETCHING, E.FAILED): S.ERROR,
    (S.FETCHING, E.RESET): S.READY,
    (S.JUDGING, E.JUDGED): "*",  # needs_revision → REVISING / REVIEW
    (S.JUDGING, E.REVIEW_READY): S.REVIEW,
    (S.JUDGING, E.EXPIRED): S.EXPIRED,
    (S.JUDGING, E.FAILED): S.ERROR,
    (S.JUDGING, E.RESET): S.READY,
    (S.REVISING, E.REVISED): S.REVIEW,
    (S.REVISING, E.REVIEW_READY): S.REVIEW,
    (S.REVISING, E.EXPIRED): S.EXPIRED,
    (S.REVISING, E.FAILED): S.ERROR,
    (S.REVISING, E.RESET): S.READY,
    (S.REVIEW, E.EDITED): S.REVIEW,
    (S.REVIEW, E.REVERTED): S.REVIEW,
    (S.REVIEW, E.SUBMIT_STARTED): S.SUBMITTING,
    (S.REVIEW, E.EXPIRED): S.EXPIRED,
    (S.REVIEW, E.RESET): S.READY,
    (S.REVIEW, E.REANALYZE): S.JUDGING,  # 사이클 7: 같은 건 다시 판독 (item 유지)
    (S.SUBMITTING, E.SUBMITTED): "*",  # kind == SKIP → READY, else DONE
    (S.SUBMITTING, E.SUBMIT_FAILED): S.REVIEW,
    (S.SUBMITTING, E.RELEASED): S.READY,
    (S.SUBMITTING, E.EXPIRED): S.EXPIRED,
}


class ReviewStateMachine:
    def __init__(self) -> None:
        self._item = ReviewItem(state=S.READY)
        self._subs: list[Subscriber] = []

    # ------------------------------------------------------------ 조회
    def current(self) -> ReviewItem:
        return self._item

    @property
    def state(self) -> S:
        return self._item.state

    def remaining_seconds(self) -> int | None:
        return self._item.remaining_seconds()

    def snapshot(self) -> ReviewItem:
        return self._item.model_copy(deep=True)

    # ------------------------------------------------------------ 구독
    def subscribe(self, cb: Subscriber) -> None:
        self._subs.append(cb)

    def _notify(self) -> None:
        if not self._subs:
            return
        snap = self.snapshot()
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return  # 동기 컨텍스트(테스트)에서는 통지 생략
        for cb in self._subs:
            loop.create_task(cb(snap))

    def publish(self) -> None:
        """상태 전이 없이 스냅샷만 다시 통지(경고 추가 등)."""
        self._notify()

    # ------------------------------------------------------------ 전이
    def transition(self, event: E, payload: dict[str, Any] | None = None) -> ReviewItem:
        payload = payload or {}
        key = (self._item.state, event)
        nxt = TRANSITIONS.get(key)
        if nxt is None:
            raise IllegalTransition(f"{self._item.state.value} 상태에서 {event.value} 이벤트는 허용되지 않습니다")
        if nxt == "*":
            if event is E.JUDGED:
                nxt = S.REVISING if payload.get("needs_revision") else S.REVIEW
            elif event is E.SUBMITTED:
                kind = payload.get("kind")
                nxt = S.READY if kind in (SubmissionKind.SKIP, "SKIP") else S.DONE
        assert isinstance(nxt, S)

        if event in (E.FETCH_STARTED, E.RESET):
            # 새 건 시작 또는 초기화: 이전 건 정보를 비운다
            self._item = ReviewItem(state=nxt, login_required=self._item.login_required, browser_alive=self._item.browser_alive)
        else:
            self._item.state = nxt
        self._item.stage_started_at = utcnow()

        # payload 병합 (item 필드만)
        for k, v in payload.items():
            if k in ReviewItem.model_fields and k != "state":
                setattr(self._item, k, v)
        if event is E.FAILED and "error" in payload:
            self._item.error = payload["error"]

        log.info("state %s --%s--> %s (item_id=%s)", key[0].value, event.value, nxt.value, self._item.item_id)
        self._notify()
        return self._item

    def add_warning(self, msg: str) -> None:
        self._item.warnings.append(msg)
        self._notify()

    def set_flags(self, *, login_required: bool | None = None, browser_alive: bool | None = None) -> None:
        if login_required is not None:
            self._item.login_required = login_required
        if browser_alive is not None:
            self._item.browser_alive = browser_alive
        self._notify()
