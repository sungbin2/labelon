import json
from pathlib import Path

import pytest

from labelon_reviewer.domain import ModelCallError
from labelon_reviewer.model.base import BaseModelClient, ModelRequest
from labelon_reviewer.model.claude_cli import build_args, build_env, parse_output
from labelon_reviewer.model.fake import FakeModelClient
from labelon_reviewer.schemas import JUDGE_SCHEMA


def _req(tmp_path, stage="judge"):
    return ModelRequest(stage=stage, model="claude-sonnet-5", effort="medium", system_file=tmp_path / "sys.md",
                        user="hello", schema=JUDGE_SCHEMA, image=tmp_path / "img.jpg", timeout=5)


def test_build_args_profiles(config, tmp_path):
    req = _req(tmp_path)
    config.cli.flags_profile = "basic"
    a = build_args(config, req, tmp_path)
    assert a[:2] == ["-p", a[1]] and "--system-prompt-file" not in a and "--json-schema" in a
    assert a[a.index("--model") + 1] == "claude-sonnet-5" and a[a.index("--effort") + 1] == "medium"
    assert json.loads(a[a.index("--json-schema") + 1]) == JUDGE_SCHEMA
    config.cli.flags_profile = "system_prompt"
    b = build_args(config, req, tmp_path)
    assert "--system-prompt-file" in b and "--tools" not in b
    config.cli.flags_profile = "minimal"
    c = build_args(config, req, tmp_path)
    assert "--tools" in c and "--disable-slash-commands" in c and "--strict-mcp-config" in c


def test_build_env_strips_nested_guard(monkeypatch):
    monkeypatch.setenv("CLAUDECODE", "1")
    monkeypatch.setenv("CLAUDE_CODE_ENTRYPOINT", "cli")
    env = build_env()
    assert "CLAUDECODE" not in env and "CLAUDE_CODE_ENTRYPOINT" not in env


def test_parse_output_success(tmp_path):
    payload = {"is_error": False, "structured_output": {"ok": 1}, "usage": {"input_tokens": 6, "output_tokens": 384,
               "cache_read_input_tokens": 112396, "cache_creation_input_tokens": 16993}, "total_cost_usd": 0.0943,
               "duration_api_ms": 7543, "num_turns": 4}
    data, usage = parse_output("Warning: something\n" + json.dumps(payload), _req(tmp_path), 100)
    assert data == {"ok": 1} and usage.cache_read_tokens == 112396 and usage.latency_ms == 7543 and usage.num_turns == 4


def test_parse_output_errors(tmp_path):
    req = _req(tmp_path)
    with pytest.raises(ModelCallError):
        parse_output("", req, 0)
    with pytest.raises(ModelCallError):
        parse_output(json.dumps({"is_error": True, "result": "auth failed"}), req, 0)
    with pytest.raises(ModelCallError):
        parse_output(json.dumps({"is_error": False, "result": "plain text"}), req, 0)
    data, _ = parse_output(json.dumps({"is_error": False, "result": json.dumps({"a": 1})}), req, 0)
    assert data == {"a": 1}


async def test_retry_count(config, sample_item, sample_draft, tmp_path, monkeypatch):
    from labelon_reviewer.model import base as basemod

    monkeypatch.setattr(basemod, "BACKOFF_SECONDS", (0, 0))
    calls = []

    class Failing(BaseModelClient):
        async def _call(self, req):
            calls.append(req.stage)
            raise ModelCallError("boom")

    with pytest.raises(ModelCallError):
        await Failing(config).judge(Path("x.jpg"), sample_item, sample_draft)
    assert len(calls) == 3


async def test_fake_client(sample_item, sample_draft):
    fake = FakeModelClient()
    raw, usage = await fake.judge(Path("x"), sample_item, sample_draft)
    assert len(raw["facts"]) == 5 and usage.stage == "judge" and fake.calls == ["judge"]


async def test_refusal_uses_fallback_once(config, sample_item, sample_draft, tmp_path, monkeypatch):
    from labelon_reviewer.domain import ModelRefused
    from labelon_reviewer.model import base as basemod

    monkeypatch.setattr(basemod, "BACKOFF_SECONDS", (0, 0))
    calls = []

    class Refusing(BaseModelClient):
        async def _call(self, req):
            calls.append(req.model)
            if req.model == "claude-fable-5-1":
                raise ModelRefused("refused")
            return {"ok": 1}, basemod.ModelUsage(stage=req.stage, model=req.model)

    config.models.revise = "claude-fable-5-1"
    config.models.revise_fallback = "claude-sonnet-5"
    from labelon_reviewer.domain import InstructionCheck, JudgeResult

    judge = JudgeResult(instruction_check=InstructionCheck(archetype_known=True, task_matches_template=True, persona_matches_config=True),
                        fact_verdicts=[], field_verdicts=[], consistency_score=80, impossible_candidate=False, needs_revision=True)
    data, usage = await Refusing(config).revise(Path("x.jpg"), sample_item, sample_draft, judge)
    assert calls == ["claude-fable-5-1", "claude-sonnet-5"] and usage.model == "claude-sonnet-5"

    calls.clear()
    config.models.revise_fallback = ""
    with pytest.raises(ModelCallError):
        await Refusing(config).revise(Path("x.jpg"), sample_item, sample_draft, judge)
    assert calls == ["claude-fable-5-1"]  # refusal 은 같은 모델로 재시도하지 않음


def test_parse_output_refusal(tmp_path):
    from labelon_reviewer.domain import ModelRefused

    with pytest.raises(ModelRefused):
        parse_output(json.dumps({"stop_reason": "refusal", "is_error": True, "result": ""}), _req(tmp_path), 0)
