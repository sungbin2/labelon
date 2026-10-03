import asyncio

import pytest

from labelon_reviewer.domain import IllegalTransition, SubmissionKind
from labelon_reviewer.domain import ReviewEvent as E
from labelon_reviewer.domain import ReviewState as S
from labelon_reviewer.state import ReviewStateMachine


def test_happy_path_with_revision():
    sm = ReviewStateMachine()
    sm.transition(E.FETCH_STARTED)
    sm.transition(E.PARSED, {"item_id": 1})
    assert sm.state is S.JUDGING and sm.current().item_id == 1
    sm.transition(E.JUDGED, {"needs_revision": True})
    assert sm.state is S.REVISING
    sm.transition(E.REVISED)
    assert sm.state is S.REVIEW
    sm.transition(E.SUBMIT_STARTED)
    sm.transition(E.SUBMITTED, {"kind": SubmissionKind.APPROVE})
    assert sm.state is S.DONE
    sm.transition(E.FETCH_STARTED)  # DONE → FETCHING 허용
    assert sm.state is S.FETCHING and sm.current().item_id is None


def test_judged_without_revision_goes_to_review():
    sm = ReviewStateMachine()
    sm.transition(E.FETCH_STARTED)
    sm.transition(E.PARSED)
    sm.transition(E.JUDGED, {"needs_revision": False})
    assert sm.state is S.REVIEW


def test_reanalyze_from_review_keeps_item():
    sm = ReviewStateMachine()
    for ev, p in [(E.FETCH_STARTED, None), (E.PARSED, {"item_id": 7}), (E.JUDGED, {"needs_revision": False})]:
        sm.transition(ev, p)
    sm.transition(E.REANALYZE)
    assert sm.state is S.JUDGING and sm.current().item_id == 7
    sm.transition(E.JUDGED, {"needs_revision": True})
    sm.transition(E.REVISED)
    assert sm.state is S.REVIEW
    with pytest.raises(IllegalTransition):
        ReviewStateMachine().transition(E.REANALYZE)


def test_skip_returns_to_ready():
    sm = ReviewStateMachine()
    for ev, p in [(E.FETCH_STARTED, None), (E.PARSED, None), (E.JUDGED, {"needs_revision": False}), (E.SUBMIT_STARTED, None)]:
        sm.transition(ev, p)
    sm.transition(E.SUBMITTED, {"kind": SubmissionKind.SKIP})
    assert sm.state is S.READY


def test_illegal_transition():
    sm = ReviewStateMachine()
    with pytest.raises(IllegalTransition):
        sm.transition(E.SUBMIT_STARTED)


def test_failed_and_expired():
    sm = ReviewStateMachine()
    sm.transition(E.FETCH_STARTED)
    sm.transition(E.FAILED, {"error": "boom"})
    assert sm.state is S.ERROR and sm.current().error == "boom"
    sm.transition(E.RESET)
    sm.transition(E.FETCH_STARTED)
    sm.transition(E.PARSED)
    sm.transition(E.JUDGED, {"needs_revision": False})
    sm.transition(E.EXPIRED)
    assert sm.state is S.EXPIRED


async def test_subscribers_notified():
    sm = ReviewStateMachine()
    seen = []

    async def cb(item):
        seen.append(item.state)

    sm.subscribe(cb)
    sm.transition(E.FETCH_STARTED)
    await asyncio.sleep(0)
    assert seen == [S.FETCHING]
