"""브라우저 세션 C-02: 도구 전용 Chrome 프로필로 LabelOn 페이지 유지. 비밀번호를 다루지 않는다."""

from __future__ import annotations

import asyncio
import logging
from html import escape as html_escape
from typing import Any

from ..config import AppConfig
from ..domain import LoginRequired
from .parser import page_kind

log = logging.getLogger(__name__)


IMAGE_VIEW_HTML = """<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8"><title>이미지 - __CAPTION__</title>
<style>
html,body{margin:0;height:100%;background:#111;color:#ddd;font:13px system-ui,sans-serif;overflow:auto}
.cap{position:fixed;left:8px;top:6px;background:rgba(0,0,0,.55);padding:3px 8px;border-radius:4px;z-index:2}
.wrap{min-height:100vh;display:flex;align-items:center;justify-content:center}
img{max-width:100vw;max-height:100vh;object-fit:contain;cursor:zoom-in}
body.zoom .wrap{display:block} body.zoom img{max-width:none;max-height:none;cursor:zoom-out}
</style></head><body>
<div class="cap">__CAPTION__ · 클릭: 원본 크기/맞춤 전환</div>
<div class="wrap"><img src="__SRC__" alt="원본 이미지"></div>
<script>document.querySelector('img').onclick=()=>document.body.classList.toggle('zoom');</script>
</body></html>"""


class BrowserSession:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self._pw = None
        self._ctx = None
        self.page = None
        self._image_page = None
        self._closed = True

    # ----------------------------------------------------------- 생명주기
    async def start(self, headless: bool = False) -> None:
        from playwright.async_api import async_playwright

        self._pw = await async_playwright().start()
        size = self.config.chrome.window_size()
        win_arg = f"--window-size={size[0]},{size[1]}" if size else "--start-maximized"
        kwargs: dict[str, Any] = {
            "user_data_dir": str(self.config.profile_dir), "headless": headless, "no_viewport": True,  # 페이지 영역이 창 크기를 따른다 (viewport=None 은 1280x720 고정)
            "args": [win_arg, "--disable-blink-features=AutomationControlled"],
            "ignore_default_args": ["--enable-automation"],
        }
        if self.config.chrome.channel != "chromium":
            kwargs["channel"] = self.config.chrome.channel
        self._ctx = await self._pw.chromium.launch_persistent_context(**kwargs)
        self.page = self._ctx.pages[0] if self._ctx.pages else await self._ctx.new_page()
        self._closed = False
        self._ctx.on("close", lambda: self._on_close())
        self._image_page = None
        if not headless:
            await self._apply_window()
        log.info("browser started (channel=%s, profile=%s, window=%s)", self.config.chrome.channel, self.config.profile_dir, self.config.chrome.window)

    async def _apply_window(self) -> None:
        """사이클 9: 영구 프로필은 마지막 창 크기를 복원하므로 CDP 로 창 상태를 직접 지정한다. 실패해도 계속 진행."""
        assert self._ctx is not None and self.page is not None
        try:
            cdp = await self._ctx.new_cdp_session(self.page)
            info = await cdp.send("Browser.getWindowForTarget")
            wid = info["windowId"]
            size = self.config.chrome.window_size()
            if size is None:
                await cdp.send("Browser.setWindowBounds", {"windowId": wid, "bounds": {"windowState": "maximized"}})
            else:
                await cdp.send("Browser.setWindowBounds", {"windowId": wid, "bounds": {"windowState": "normal"}})
                await cdp.send("Browser.setWindowBounds", {"windowId": wid, "bounds": {"left": 0, "top": 0, "width": size[0], "height": size[1]}})
            await cdp.detach()
        except Exception as e:  # CDP 미지원·창 없음 등
            log.warning("window size apply failed: %s", e)

    async def show_image(self, image_url: str, caption: str = "") -> None:
        """사이클 9: 이미지 전용 탭(한 번 만들고 재사용)에 원본 사진을 창 크기에 맞춰 표시한다. 작업 탭(self.page)은 그대로 둔다."""
        assert self._ctx is not None
        if self._image_page is None or self._image_page.is_closed():
            self._image_page = await self._ctx.new_page()
        html = IMAGE_VIEW_HTML.replace("__SRC__", html_escape(image_url, quote=True)).replace("__CAPTION__", html_escape(caption))
        await self._image_page.set_content(html)
        await self._image_page.bring_to_front()

    def _on_close(self) -> None:
        self._closed = True
        log.warning("browser context closed")

    def is_alive(self) -> bool:
        return not self._closed and self.page is not None and not self.page.is_closed()

    async def close(self) -> None:
        try:
            if self._ctx and not self._closed:
                await self._ctx.close()
        finally:
            self._closed = True
            if self._pw:
                await self._pw.stop()
            self._pw = None
            self._ctx = None
            self.page = None

    # ----------------------------------------------------------- 탐색
    def _url(self, path: str) -> str:
        return self.config.labelon.base_url.rstrip("/") + path

    async def goto(self, path: str, wait: str = "domcontentloaded") -> None:
        assert self.page is not None
        await self.page.goto(self._url(path), wait_until=wait, timeout=45_000)

    async def content(self) -> str:
        assert self.page is not None
        return await self.page.content()

    async def current_page_kind(self) -> str:
        assert self.page is not None
        return page_kind(self.page.url, await self.page.content())

    async def is_logged_in(self) -> bool:
        """보호 페이지(/project/home)를 컨텍스트 요청 API 로 받아 본다. 페이지를 이동시키지 않으며 쿠키를 공유한다.
        미로그인이면 /access 로 리다이렉트된다."""
        assert self._ctx is not None
        try:
            resp = await self._ctx.request.get(self._url("/project/home"), timeout=30_000)
            text = await resp.text() if resp.ok else ""
        except Exception as e:  # 네트워크 오류는 미로그인으로 취급하지 않고 경고
            log.warning("login check failed: %s", e)
            return False
        return page_kind(resp.url, text) != "LOGIN" and resp.ok

    async def fetch_project_home(self) -> str:
        """프로젝트 홈 HTML 을 요청 API 로 받는다(페이지 이동 없음). 미로그인이면 LoginRequired."""
        assert self._ctx is not None
        resp = await self._ctx.request.get(self._url("/project/home"), timeout=30_000)
        text = await resp.text()
        if page_kind(resp.url, text) == "LOGIN" or not resp.ok:
            raise LoginRequired("프로젝트 홈을 열 수 없습니다. 로그인이 필요합니다")
        return text

    async def show_login_page(self) -> None:
        """LabelOn 홈으로 이동한다. 로그인은 사용자가 직접 한다(홈의 로그인 메뉴/알림창)."""
        await self.goto("/")

    async def wait_for_login(self, timeout_s: int = 1800, poll_s: float = 2.0) -> None:
        """사용자가 직접 로그인할 때까지 대기. 사용자의 화면을 이동시키지 않고 요청 API 로만 확인한다."""
        waited = 0.0
        while waited < timeout_s:
            if not self.is_alive():
                raise LoginRequired("브라우저 창이 닫혔습니다")
            if await self.is_logged_in():
                log.info("login detected")
                return
            await asyncio.sleep(poll_s)
            waited += poll_s
        raise LoginRequired("로그인 대기 시간이 초과되었습니다")

    async def open_job_page(self, dataset_id: int) -> tuple[str, str]:
        """작업 화면 열기 → (page_kind, html). 열면 LabelOn 이 건을 할당한다."""
        await self.goto(f"/job/ucle/annotator?datasetId={dataset_id}")
        try:
            await self.page.wait_for_load_state("networkidle", timeout=15_000)
        except Exception:
            pass
        html = await self.content()
        return page_kind(self.page.url, html), html

    async def fetch_bytes(self, url: str) -> bytes:
        assert self._ctx is not None
        resp = await self._ctx.request.get(url, timeout=60_000)
        if not resp.ok:
            raise OSError(f"이미지 다운로드 실패 {resp.status}: {url}")
        return await resp.body()
