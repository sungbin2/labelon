"""모델 백엔드 팩토리 (Strategy)."""

from __future__ import annotations

from ..config import AppConfig
from .base import ModelClient


def make_client(config: AppConfig) -> ModelClient:
    if config.model_backend == "claude_cli":
        from .claude_cli import ClaudeCliModelClient

        return ClaudeCliModelClient(config)
    if config.model_backend == "anthropic_sdk":
        from .anthropic_sdk import AnthropicSdkModelClient

        return AnthropicSdkModelClient(config)
    from .fake import FakeModelClient

    return FakeModelClient(config)
