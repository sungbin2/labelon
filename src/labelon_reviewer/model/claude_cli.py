"""Claude Code CLI(-p) 서브프로세스 백엔드. 기존 Claude Code 로그인 자격증명을 그대로 사용한다.

검증(2026-09-23): `claude -p ... --model claude-sonnet-5 --output-format json --allowedTools Read --add-dir <dir> --json-schema {...}`
가 이미지 Read + 구조화 출력을 정상 반환.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Any

from ..config import AppConfig
from ..domain import ModelCallError, ModelRefused, ModelUsage
from .base import BaseModelClient, ModelRequest

log = logging.getLogger(__name__)

STRIP_ENV = ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT")
PROMPT_HEADER = "아래 입력을 시스템 지시에 따라 처리하고, 요구된 JSON 스키마로만 답하세요."


def build_args(config: AppConfig, req: ModelRequest, add_dir: Path) -> list[str]:
    """flags_profile 에 따른 CLI 인자. -p 다음의 프롬프트 본문은 stdin 으로 전달한다."""
    profile = config.cli.flags_profile
    args: list[str] = [
        "-p", PROMPT_HEADER,
        "--model", req.model,
        "--effort", req.effort,
        "--output-format", "json",
        "--json-schema", json.dumps(req.schema, ensure_ascii=False, separators=(",", ":")),
        "--allowedTools", "Read",
        "--add-dir", str(add_dir),
        "--max-turns", str(config.cli.max_turns),
        "--permission-mode", "dontAsk",
        "--no-session-persistence",
    ]
    if profile in ("system_prompt", "minimal"):
        args += ["--system-prompt-file", str(req.system_file)]
    if profile == "minimal":
        args += [
            "--tools", "Read",
            "--disable-slash-commands",
            "--permission-prompts", "none",
            "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}',
        ]
    return args


def build_env() -> dict[str, str]:
    env = dict(os.environ)
    for k in STRIP_ENV:
        env.pop(k, None)
    if env.get("ANTHROPIC_API_KEY"):
        log.warning("ANTHROPIC_API_KEY 가 환경에 설정되어 있어 Claude Code 로그인 대신 API 키가 사용됩니다")
    return env


def resolve_cli(path: str) -> str:
    found = shutil.which(path)
    if found:
        return found
    if Path(path).exists():
        return str(Path(path))
    raise ModelCallError(f"claude 실행 파일을 찾을 수 없습니다: {path}. config.cli.path 를 확인하세요")


def parse_output(stdout: str, req: ModelRequest, latency_ms: int) -> tuple[dict[str, Any], ModelUsage]:
    text = stdout.strip()
    if not text:
        raise ModelCallError("CLI 출력이 비어 있습니다")
    # 앞에 경고 문구가 섞일 수 있어 첫 '{' 부터 파싱
    start = text.find("{")
    if start < 0:
        raise ModelCallError(f"CLI 출력이 JSON 이 아닙니다: {text[:200]}")
    try:
        data = json.loads(text[start:])
    except json.JSONDecodeError as e:
        raise ModelCallError(f"CLI JSON 파싱 실패: {e}: {text[:200]}") from e
    if data.get("stop_reason") == "refusal":
        raise ModelRefused(f"모델({req.model})이 응답을 거부했습니다 (refusal)")
    if data.get("is_error"):
        raise ModelCallError(f"CLI 오류 응답: {str(data.get('result'))[:300]}")
    structured = data.get("structured_output")
    if structured is None:
        # 폴백: result 문자열이 JSON 일 수 있음
        result = data.get("result")
        if isinstance(result, str):
            try:
                structured = json.loads(result)
            except json.JSONDecodeError:
                structured = None
    if not isinstance(structured, dict):
        raise ModelCallError(f"structured_output 이 없습니다 (subtype={data.get('subtype')}, stop={data.get('stop_reason')})")
    u = data.get("usage") or {}
    usage = ModelUsage(
        stage=req.stage, model=req.model,
        input_tokens=int(u.get("input_tokens") or 0), output_tokens=int(u.get("output_tokens") or 0),
        cache_read_tokens=int(u.get("cache_read_input_tokens") or 0),
        cache_creation_tokens=int(u.get("cache_creation_input_tokens") or 0),
        latency_ms=int(data.get("duration_api_ms") or latency_ms), cost_usd=float(data.get("total_cost_usd") or 0.0),
        num_turns=int(data.get("num_turns") or 0),
    )
    return structured, usage


async def _kill_tree(proc: asyncio.subprocess.Process) -> None:
    if proc.returncode is not None:
        return
    try:
        if sys.platform == "win32":
            killer = await asyncio.create_subprocess_exec(
                "taskkill", "/PID", str(proc.pid), "/T", "/F",
                stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
            )
            await killer.wait()
        else:  # pragma: no cover
            proc.kill()
    except Exception as e:  # pragma: no cover
        log.warning("kill tree failed: %s", e)


class ClaudeCliModelClient(BaseModelClient):
    async def _call(self, req: ModelRequest) -> tuple[dict[str, Any], ModelUsage]:
        cli = resolve_cli(self.config.cli.path)
        cwd = Path(self.config.cli.cwd)
        cwd.mkdir(parents=True, exist_ok=True)
        args = build_args(self.config, req, req.image.parent)
        env = build_env()
        t0 = time.monotonic()
        log.debug("cli exec: %s %s", cli, " ".join(args[:6]))
        proc = await asyncio.create_subprocess_exec(
            cli, *args, cwd=str(cwd), env=env,
            stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        try:
            out, err = await asyncio.wait_for(proc.communicate(req.user.encode("utf-8")), timeout=req.timeout)
        except TimeoutError:
            await _kill_tree(proc)
            raise ModelCallError(f"{req.stage} 호출이 {req.timeout}초를 초과했습니다") from None
        except asyncio.CancelledError:
            await _kill_tree(proc)
            raise
        latency_ms = int((time.monotonic() - t0) * 1000)
        stdout = out.decode("utf-8", errors="replace")
        stderr = err.decode("utf-8", errors="replace")
        if proc.returncode != 0:
            # refusal 등은 종료 코드 1 이지만 stdout 에 JSON 이 있다 → 파싱해 구체적 예외로
            if "{" in stdout:
                try:
                    return parse_output(stdout, req, latency_ms)
                except ModelRefused:
                    raise
                except ModelCallError as e:
                    raise ModelCallError(f"CLI 종료 코드 {proc.returncode}: {e}") from e
            raise ModelCallError(f"CLI 종료 코드 {proc.returncode}: {(stderr or stdout)[:300]}")
        if stderr.strip():
            log.debug("cli stderr: %s", stderr[:500])
        return parse_output(stdout, req, latency_ms)
