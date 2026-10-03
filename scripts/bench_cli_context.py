"""Claude Code CLI 호출당 기본 컨텍스트 벤치 (NFR C-3, nfr-design 성능 패턴).

플래그 조합 3가지(basic / system_prompt / minimal)로 짧은 호출을 1회씩 실행해 usage 와 소요 시간을 표로 출력한다.
구독 사용량이 소량 소모되므로 사용자가 직접 실행한다:

    .venv\\Scripts\\python scripts\\bench_cli_context.py --config config.yaml [--profiles basic,system_prompt,minimal]
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from labelon_reviewer.config import load  # noqa: E402
from labelon_reviewer.domain import ModelCallError  # noqa: E402
from labelon_reviewer.model.base import ModelRequest  # noqa: E402
from labelon_reviewer.model.claude_cli import ClaudeCliModelClient  # noqa: E402

SCHEMA = {"type": "object", "additionalProperties": False, "required": ["answer"], "properties": {"answer": {"type": "string"}}}


async def run_profile(cfg, profile: str, sys_file: Path, img: Path) -> dict:
    cfg.cli.flags_profile = profile
    client = ClaudeCliModelClient(cfg)
    req = ModelRequest(stage="judge", model=cfg.models.judge, effort="low", system_file=sys_file,
                       user="다음 질문에 한 단어로 답하세요: 1+1은? answer 필드에 넣으세요.", schema=SCHEMA, image=img, timeout=120)
    t0 = time.monotonic()
    try:
        data, usage = await client._call(req)
        return {"profile": profile, "ok": True, "answer": data.get("answer"), "in": usage.input_tokens, "out": usage.output_tokens,
                "cache_read": usage.cache_read_tokens, "cache_create": usage.cache_creation_tokens,
                "context_total": usage.input_tokens + usage.cache_read_tokens + usage.cache_creation_tokens,
                "cost": usage.cost_usd, "api_ms": usage.latency_ms, "wall_s": round(time.monotonic() - t0, 1)}
    except ModelCallError as e:
        return {"profile": profile, "ok": False, "error": str(e)[:200], "wall_s": round(time.monotonic() - t0, 1)}


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--profiles", default="basic,system_prompt,minimal")
    args = ap.parse_args()
    cfg = load(args.config)
    cfg.ensure_dirs()
    tmp = Path(tempfile.mkdtemp(prefix="bench_"))
    sys_file = tmp / "sys.md"
    sys_file.write_text("당신은 간단한 질문에 JSON 으로만 답하는 도우미입니다.", encoding="utf-8")
    img = tmp / "none.jpg"  # Read 도구는 호출되지 않음(이미지 언급 없음). add-dir 용 경로만 필요
    img.write_bytes(b"")
    rows = [await run_profile(cfg, p.strip(), sys_file, img) for p in args.profiles.split(",") if p.strip()]
    print("\nprofile        ok   context_total  cache_read  cache_create  in    out   cost($)  api_ms  wall_s")
    for r in rows:
        if r["ok"]:
            print(f"{r['profile']:<14} {'Y':<4} {r['context_total']:>13} {r['cache_read']:>11} {r['cache_create']:>13} {r['in']:>5} {r['out']:>5} {r['cost']:>8.4f} {r['api_ms']:>7} {r['wall_s']:>6}")
        else:
            print(f"{r['profile']:<14} {'N':<4} error: {r['error']}")
    ok = [r for r in rows if r["ok"]]
    if ok:
        best = min(ok, key=lambda r: r["context_total"])
        print(f"\n최소 컨텍스트 조합: {best['profile']} ({best['context_total']} tokens). config.yaml 의 cli.flags_profile 에 반영하세요.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
