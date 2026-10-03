"""브라우저 세션 C-02: 도구 전용 Chrome 프로필로 LabelOn 페이지 유지. 비밀번호를 다루지 않는다."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from ..config import AppConfig
from ..domain import LoginRequired
from .parser import page_kind

log = logging.getLogger(__name__)


class BrowserSession:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self._pw = None
        self._ctx = None
        self.page = None
        self._closed = True

    # ----------------------------------------------------------- 생명주기
    async def start(self, headless: bool = False) -> None:
        from playwright.async_api import async_playwright

        self._pw = await async_playwright().start()
        kwargs: dict[str, Any] = {
            "user_data_dir": str(self.config.profile_dir), "headless": headless, "viewport": None,
            "args": ["--start-maximized", "--disable-blink-features=AutomationControlled"],
            "ignore_default_args": ["--enable-automation"],
        }
        if self.config.chrome.channel != "chromium":
            kwargs["channel"] = self.config.chrome.channel
        self._ctx = await self._pw.chromium.launch_persistent_context(**kwargs)
        self.page = self._ctx.pages[0] if self._ctx.pages else await self._ctx.new_page()
        self._closed = False
        self._ctx.on("close", lambda: self._on_close())
        log.info("browser started (channel=%s, profile=%s)", self.config.chrome.channel, self.config.profile_dir)

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
