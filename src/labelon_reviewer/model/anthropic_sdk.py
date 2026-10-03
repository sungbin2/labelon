"""Anthropic Python SDK 백엔드 (대안). 인증: ANTHROPIC_API_KEY 또는 `ant auth login` OAuth 프로파일.

`anthropic` 패키지는 선택 의존성이다: pip install "labelon-reviewer[anthropic]".
이 백엔드는 설계 시점에 실제 호출로 검증되지 않았다(Build 단계 수동 체크리스트 항목).
"""

from __future__ import annotations

import asyncio
import base64
import json
import time
from typing import Any

from ..domain import ModelCallError, ModelUsage
from .base import BaseModelClient, ModelRequest


class AnthropicSdkModelClient(BaseModelClient):
    def __init__(self, config) -> None:
        super().__init__(config)
        try:
            import anthropic  # noqa: F401
        except ImportError as e:  # pragma: no cover
            raise ModelCallError(
                "anthropic 패키지가 설치되어 있지 않습니다. `pip install anthropic` 후 model_backend: anthropic_sdk 를 사용하세요"
            ) from e
        self._client = None

    def _get_client(self):
        if self._client is None:
            import anthropic

            self._client = anthropic.AsyncAnthropic()
        return self._client

    async def _call(self, req: ModelRequest) -> tuple[dict[str, Any], ModelUsage]:
        client = self._get_client()
        image_b64 = base64.b64encode(await asyncio.to_thread(req.image.read_bytes)).decode("ascii")
        system_text = await asyncio.to_thread(req.system_file.read_text, "utf-8")
        t0 = time.monotonic()
        try:
            resp = await client.messages.create(
                model=req.model,
                max_tokens=8000,
                system=[{"type": "text", "text": system_text, "cache_control": {"type": "ephemeral"}}],
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": image_b64}},
                        {"type": "text", "text": req.user},
                    ],
                }],
                output_config={"format": {"type": "json_schema", "schema": req.schema}, "effort": req.effort},
                timeout=req.timeout,
            )
        except Exception as e:  # SDK 예외 계층은 설치 후 세분화
            raise ModelCallError(f"Anthropic SDK 호출 실패: {e}") from e
        latency_ms = int((time.monotonic() - t0) * 1000)
        if getattr(resp, "stop_reason", None) == "refusal":
            raise ModelCallError("모델이 응답을 거부했습니다(refusal)")
        text = "".join(getattr(b, "text", "") for b in resp.content if getattr(b, "type", "") == "text")
        try:
            structured = json.loads(text)
        except json.JSONDecodeError as e:
            raise ModelCallError(f"구조화 출력 파싱 실패: {text[:200]}") from e
        u = resp.usage
        usage = ModelUsage(
            stage=req.stage, model=req.model,
            input_tokens=int(getattr(u, "input_tokens", 0) or 0), output_tokens=int(getattr(u, "output_tokens", 0) or 0),
            cache_read_tokens=int(getattr(u, "cache_read_input_tokens", 0) or 0),
            cache_creation_tokens=int(getattr(u, "cache_creation_input_tokens", 0) or 0),
            latency_ms=latency_ms,
        )
        return structured, usage
