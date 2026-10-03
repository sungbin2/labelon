"""로그인된 도구 프로필로 LabelOn 작업 화면 HTML 을 캡처해 파서 회귀 픽스처로 저장한다.

주의: 작업 화면을 열면 LabelOn 이 해당 건을 이 계정에 할당하고 60분 제한시간이 시작된다.
      캡처 후 --release 를 주면 페이지가 만료 시 쓰는 반환 요청으로 즉시 반환한다.

    .venv\\Scripts\\python scripts\\capture_job_page.py --config config.yaml --out tests/fixtures/job_page_live.html [--release]
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from labelon_reviewer.config import load  # noqa: E402
from labelon_reviewer.labelon import parser  # noqa: E402
from labelon_reviewer.labelon.browser import BrowserSession  # noqa: E402
from labelon_reviewer.labelon.submitter import Submitter  # noqa: E402


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--out", default="tests/fixtures/job_page_live.html")
    ap.add_argument("--release", action="store_true")
    args = ap.parse_args()
    cfg = load(args.config)
    cfg.ensure_dirs()
    br = BrowserSession(cfg)
    await br.start()
    try:
        if not await br.is_logged_in():
            print("로그인이 필요합니다. 열린 Chrome 창에서 로그인하세요 (최대 30분 대기)...")
            await br.show_login_page()
            await br.wait_for_login()
        kind, html = await br.open_job_page(cfg.dataset_id)
        print("page kind:", kind)
        if kind != "JOB":
            print("작업 화면이 아닙니다. 종료합니다.")
            return 1
        Path(args.out).write_text(html, encoding="utf-8")
        item, draft = parser.parse_html(html, cfg.labelon.server_tz_offset_hours)
        print(f"saved {args.out}; job_id={item.job_id} file={item.org_file_name} facts={len(draft.facts)} turns={len(draft.dialogue.turns)}")
        if args.release:
            rec = await Submitter(parser.field_locators()).release(br.page, item)
            print("release:", "ok" if rec.success else f"failed: {rec.error}")
        else:
            print("주의: 이 건은 할당된 상태입니다(60분 후 자동 반환). 바로 반환하려면 --release 를 사용하세요.")
        return 0
    finally:
        await br.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
