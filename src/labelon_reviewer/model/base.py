"""ModelClient 프로토콜과 공통 기반 클래스 (재시도·타임아웃·usage)."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from ..config import AppConfig
from ..domain import Draft, Instruction, JudgeResult, ModelCallError, ModelRefused, ModelUsage, SourceItem
from ..prompts import build_judge_user, build_revise_user, system_prompt_path
from ..schemas import JUDGE_SCHEMA, REVISE_SCHEMA

log = logging.getLogger(__name__)

MAX_RETRIES = 2
BACKOFF_SECONDS = (2, 4)


@dataclass
class ModelRequest:
    stage: str  # judge | revise
    model: str
    effort: str
    system_file: Path
    user: str
    schema: dict[str, Any]
    image: Path
    timeout: int
    fallback_model: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


class ModelClient(Protocol):
    async def judge(self, image: Path, item: SourceItem, draft: Draft) -> tuple[dict[str, Any], ModelUsage]: ...

    async def revise(
        self, image: Path, item: SourceItem, draft: Draft, judge: JudgeResult, corrected: Instruction | None = None
    ) -> tuple[dict[str, Any], ModelUsage]: ...


class BaseModelClient:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    async def judge(self, image: Path, item: SourceItem, draft: Draft) -> tuple[dict[str, Any], ModelUsage]:
        req = ModelRequest(
            stage="judge", model=self.config.models.judge, effort=self.config.effort.judge,
            system_file=system_prompt_path("judge"), user=build_judge_user(item, draft, str(image), self.config),
            schema=JUDGE_SCHEMA, image=Path(image), timeout=self.config.cli.timeouts.judge,
            fallback_model=self.config.models.judge_fallback,
        )
        return await self._call_with_retry(req)

    async def revise(
        self, image: Path, item: SourceItem, draft: Draft, judge: JudgeResult, corrected: Instruction | None = None
    ) -> tuple[dict[str, Any], ModelUsage]:
        req = ModelRequest(
            stage="revise", model=self.config.models.revise, effort=self.config.effort.revise,
            system_file=system_prompt_path("revise"),
            user=build_revise_user(item, draft, judge, str(image), self.config, corrected),
            schema=REVISE_SCHEMA, image=Path(image), timeout=self.config.cli.timeouts.revise,
            fallback_model=self.config.models.revise_fallback,
        )
        return await self._call_with_retry(req)

    async def _call_with_retry(self, req: ModelRequest) -> tuple[dict[str, Any], ModelUsage]:
        last: Exception | None = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                # 구현체 자체 타임아웃 + 여유 15초 가드
                return await asyncio.wait_for(self._call(req), timeout=req.timeout + 15)
            except asyncio.CancelledError:
                raise
            except ModelRefused as e:
                # 같은 모델로 재시도해도 결과가 같고 비용만 든다. 폴백 모델이 있으면 1회만 시도
                log.warning("model %s refused by %s", req.stage, req.model)
                if req.fallback_model and req.fallback_model != req.model:
                    fb = ModelRequest(**{**req.__dict__, "model": req.fallback_model, "fallback_model": ""})
                    log.info("retrying %s with fallback model %s", req.stage, fb.model)
                    return await asyncio.wait_for(self._call(fb), timeout=fb.timeout + 15)
                raise ModelCallError(f"{req.stage} 모델({req.model})이 응답을 거부했습니다. 폴백 모델이 없어 중단합니다") from e
            except (ModelCallError, TimeoutError, OSError) as e:
                last = e
                log.warning("model %s attempt %d failed: %s", req.stage, attempt + 1, e)
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(BACKOFF_SECONDS[min(attempt, len(BACKOFF_SECONDS) - 1)])
        raise ModelCallError(f"{req.stage} 모델 호출이 {MAX_RETRIES + 1}회 모두 실패했습니다: {last}")

    async def _call(self, req: ModelRequest) -> tuple[dict[str, Any], ModelUsage]:  # pragma: no cover
        raise NotImplementedError
