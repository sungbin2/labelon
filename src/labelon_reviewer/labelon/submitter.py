"""제출기 C-11: 열려 있는 작업 화면의 UI 를 조작해 제출한다 (business-logic-model.md 6절).

이 모듈의 어떤 메서드도 사용자의 명시적 HTTP 요청 없이 호출되지 않는다 (BR-31).

LabelOn 공통 모달 (method.js, 2026-09-23 확인):
  ModalConfirm → #commonmodal2, 본문 #commonmodal2_text, 버튼 "닫기"/"확인" (확인 클릭 시 콜백 = ucleSubmit)
  ModalAlert   → #commonmodal1, 본문 #commonmodal1_text, 버튼 1개 (클릭 시 콜백 = 페이지 재이동)
"""

from __future__ import annotations

import logging
from typing import Any

from ..domain import FinalDraft, SourceItem, SubmissionKind, SubmissionRecord, SubmitError, utcnow
from .parser import FieldLocatorMap, current_job_id

log = logging.getLogger(__name__)


class Submitter:
    def __init__(self, locators: FieldLocatorMap) -> None:
        self.loc = locators

    # ------------------------------------------------------------ 공통
    async def _assert_same_job(self, page, expected_job_id: int) -> None:
        html = await page.content()
        jid = current_job_id(html)
        if jid != expected_job_id:
            raise SubmitError(f"작업 화면의 건이 바뀌었습니다 (기대 {expected_job_id}, 현재 {jid}). 제출을 중단합니다")

    async def _verify_counts(self, page, fact_count: int) -> None:
        got = {
            "plain": await page.locator(self.loc.plain_textarea).count(),
            "facts": await page.locator(self.loc.facts_textarea).count(),
            "question": await page.locator(self.loc.question_textarea).count(),
            "answer": await page.locator(self.loc.answer_textarea).count(),
            "radio": await page.locator(self.loc.radio).count(),
        }
        expected = {**self.loc.expected_counts, "facts": fact_count}
        for k, v in expected.items():
            if k == "facts":
                if got[k] < v:
                    raise SubmitError(f"화면의 Facts 입력란({got[k]}개)이 초안 Facts({v}개)보다 적습니다")
                if got[k] > v:
                    log.warning("facts textareas %d > draft facts %d; extras left untouched", got[k], v)
                continue
            if got.get(k) != v:
                raise SubmitError(f"화면 구조가 예상과 다릅니다: {k} 개수 {got.get(k)} (기대 {v})")

    async def _fill(self, locator, value: str, label: str) -> None:
        await locator.fill(value)
        if (await locator.input_value()) != value:
            await locator.fill(value)
            if (await locator.input_value()) != value:
                raise SubmitError(f"{label} 입력값이 반영되지 않았습니다")

    async def _click_confirm_and_read_result(self, page, kind: SubmissionKind) -> str:
        """제출 버튼 → 확인 모달(#commonmodal2) 확인 → 결과 모달(#commonmodal1) 텍스트 읽기 → 닫기."""
        await page.locator(self.loc.submit_button).first.click()

        confirm = page.locator(self.loc.confirm_modal)
        try:
            await confirm.wait_for(state="visible", timeout=10_000)
        except Exception as e:
            # React 측 검증 실패(예: 사유 필요)는 확인 모달 대신 알림 모달로 올 수 있다
            alert_text = await self._read_alert_if_visible(page)
            if alert_text:
                await self._close_alert(page)
                raise SubmitError(f"제출이 거부되었습니다: {alert_text}") from e
            raise SubmitError("제출 확인 모달이 표시되지 않았습니다") from e
        confirm_text = (await page.locator(self.loc.confirm_modal_text).inner_text()).strip()
        if self.loc.confirm_text not in confirm_text:
            log.warning("unexpected confirm modal text: %s", confirm_text[:120])
        ok_btn = confirm.locator(self.loc.confirm_ok_button)
        if await ok_btn.count() == 0:
            ok_btn = confirm.locator("button").last
        await ok_btn.first.click()

        alert = page.locator(self.loc.alert_modal)
        try:
            await alert.wait_for(state="visible", timeout=20_000)
        except Exception as e:
            raise SubmitError("제출 결과 모달이 표시되지 않았습니다") from e
        message = (await page.locator(self.loc.alert_text).inner_text()).strip()
        log.info("%s result: %s", kind.value, message)
        await self._close_alert(page)
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=15_000)
        except Exception:
            pass
        return message

    async def _read_alert_if_visible(self, page) -> str:
        alert = page.locator(self.loc.alert_modal)
        try:
            if await alert.count() and await alert.is_visible():
                return (await page.locator(self.loc.alert_text).inner_text()).strip()
        except Exception:
            pass
        return ""

    async def _close_alert(self, page) -> None:
        try:
            await page.locator(self.loc.alert_close_button).first.click(timeout=5_000)
        except Exception:
            pass

    # ------------------------------------------------------------ 승인
    async def approve(self, page, final: FinalDraft, expected_job_id: int) -> SubmissionRecord:
        snapshot: dict[str, Any] = {}
        try:
            await self._assert_same_job(page, expected_job_id)
            await self._verify_counts(page, len(final.facts))
            # Instruction (사이클 3: 아키타입 정정 시 값이 바뀜). 화면 값과 다를 때만 채운다
            ins = page.locator(self.loc.instruction_textarea)
            if await ins.count() >= 3:
                for i, name in enumerate(("archetype", "persona", "task")):
                    value = getattr(final.instruction, name)
                    if (await ins.nth(i).input_value()) != value:
                        await self._fill(ins.nth(i), value, name)
                        snapshot[name] = value
            plain = page.locator(self.loc.plain_textarea)
            for name in ("scene", "cot1", "cot2", "cot3"):
                value = getattr(final, name)
                await self._fill(plain.nth(self.loc.plain_index(name)), value, name)
                snapshot[name] = value
            facts = page.locator(self.loc.facts_textarea)
            for i in range(len(final.facts)):
                await self._fill(facts.nth(i), final.facts[i], f"fact_{i + 1}")
                snapshot[f"fact_{i + 1}"] = final.facts[i]
            q = page.locator(self.loc.question_textarea)
            a = page.locator(self.loc.answer_textarea)
            active = {t.turn: t for t in final.dialogue.active_turns()}
            total = min(await q.count(), await a.count())
            for n in range(1, total + 1):
                t = active.get(n)
                if t is not None:
                    await self._fill(q.nth(n - 1), t.user, f"turn_{n}_user")
                    await self._fill(a.nth(n - 1), t.assistant, f"turn_{n}_assistant")
                    snapshot[f"turn_{n}_user"] = t.user
                    snapshot[f"turn_{n}_assistant"] = t.assistant
                else:  # 삭제된 턴(사이클 3) 또는 원래 빈 턴: 값이 남아 있으면 비운다
                    for loc_, label in ((q.nth(n - 1), f"turn_{n}_user"), (a.nth(n - 1), f"turn_{n}_assistant")):
                        if (await loc_.input_value()).strip():
                            await self._fill(loc_, "", label)
                            snapshot[label] = ""
            await page.locator(self.loc.radio).nth(0).check()
            message = await self._click_confirm_and_read_result(page, SubmissionKind.APPROVE)
            ok = self.loc.success_text in message
            return SubmissionRecord(kind=SubmissionKind.APPROVE, payload_snapshot=snapshot, response_message=message,
                                    success=ok, error=None if ok else message, submitted_at=utcnow())
        except SubmitError as e:
            return SubmissionRecord(kind=SubmissionKind.APPROVE, payload_snapshot=snapshot, success=False, error=str(e))

    # ------------------------------------------------------------ 불가
    async def impossible(self, page, reason: str, expected_job_id: int) -> SubmissionRecord:
        """불가 제출. 사유는 비어 있어도 진행한다(플랫폼이 거부하면 그 메시지를 결과로 기록)."""
        snapshot = {"reason": reason}
        try:
            await self._assert_same_job(page, expected_job_id)
            await page.locator(self.loc.radio).nth(1).check()
            box = page.locator(self.loc.impossible_reason_textarea).first
            try:
                await box.wait_for(state="visible", timeout=5_000)
                await self._fill(box, reason, "impossible_reason")
            except SubmitError:
                raise
            except Exception:
                if reason:
                    raise SubmitError("불가 사유 입력란이 표시되지 않았습니다") from None
                log.info("impossible reason box not visible; proceeding without reason")
            message = await self._click_confirm_and_read_result(page, SubmissionKind.IMPOSSIBLE)
            ok = self.loc.success_text in message
            return SubmissionRecord(kind=SubmissionKind.IMPOSSIBLE, payload_snapshot=snapshot, response_message=message,
                                    success=ok, error=None if ok else message, submitted_at=utcnow())
        except SubmitError as e:
            return SubmissionRecord(kind=SubmissionKind.IMPOSSIBLE, payload_snapshot=snapshot, success=False, error=str(e))

    # ------------------------------------------------------------ 반환
    async def release(self, page, item: SourceItem) -> SubmissionRecord:
        """페이지가 제한시간 만료 시 호출하는 것과 같은 반환 요청을 페이지 컨텍스트(jQuery, CSRF 프리필터 포함)에서 수행."""
        payload = {"datasetId": item.dataset_id, "id": item.job_id, "fileId": item.file_id, "annotatorId": item.annotator_id}
        js = """(p) => new Promise((res, rej) => {
            if (typeof $ === 'undefined') { rej(new Error('jQuery not available')); return; }
            $.ajax({ url: '/job/ucle/annotator/resetData', type: 'post', dataType: 'json', contentType: 'application/json',
                     data: JSON.stringify(p), success: (d) => res(d || {}), error: (x) => rej(new Error('status ' + x.status)) });
        })"""
        try:
            result = await page.evaluate(js, payload)
            log.info("release result: %s", result)
            try:
                await page.goto(page.url.split("/job/")[0] + "/project/home", wait_until="domcontentloaded", timeout=30_000)
            except Exception:
                pass
            return SubmissionRecord(kind=SubmissionKind.SKIP, payload_snapshot=payload, response_message=str(result)[:300], success=True)
        except Exception as e:
            return SubmissionRecord(kind=SubmissionKind.SKIP, payload_snapshot=payload, success=False, error=str(e))
