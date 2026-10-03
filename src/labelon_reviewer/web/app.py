"""FastAPI 앱 C-13: localhost 바인딩, Origin 검사, SSE, 동작 엔드포인트, 이력 조회."""

from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel

from .. import __version__
from ..domain import IllegalTransition, ItemExpired, ReviewItem, SubmitError, utcnow
from ..services import (
    AppContext,
    ConfigService,
    DatasetService,
    DeadlineService,
    EditService,
    FetchAndAnalyzeService,
    HistoryService,
    SessionService,
    SubmitService,
)

log = logging.getLogger(__name__)
STATIC = Path(__file__).parent / "static"
HEARTBEAT_SECONDS = 30


# ------------------------------------------------------------------ SSE 브로드캐스터
class Broadcaster:
    def __init__(self) -> None:
        self._subs: set[asyncio.Queue[str]] = set()

    def subscribe(self) -> asyncio.Queue[str]:
        q: asyncio.Queue[str] = asyncio.Queue(maxsize=100)
        self._subs.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue[str]) -> None:
        self._subs.discard(q)

    def publish(self, event: str, data: dict[str, Any]) -> None:
        msg = f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"
        for q in list(self._subs):
            try:
                q.put_nowait(msg)
            except asyncio.QueueFull:
                self.unsubscribe(q)


def snapshot_payload(item: ReviewItem, summary: dict[str, Any] | None = None, datasets: dict[str, Any] | None = None) -> dict[str, Any]:
    data = item.model_dump(mode="json")
    data["server_now"] = utcnow().isoformat()
    data["server_version"] = __version__  # 화면이 서버 재시작(버전 변경)을 감지해 스스로 새로고침
    data["remaining_seconds"] = item.remaining_seconds()
    if summary is not None:
        data["summary"] = summary
    if datasets is not None:
        data.update(datasets)
    return data


# ------------------------------------------------------------------ 요청 모델
class DraftEdit(BaseModel):
    field: str
    value: str


class RevertField(BaseModel):
    field: str


class ImpossibleBody(BaseModel):
    reason: str


class DatasetSelectBody(BaseModel):
    dataset_id: int


# ------------------------------------------------------------------ 앱 팩토리
def create_app(ctx: AppContext, *, manage_browser: bool = True, open_browser: bool = False) -> FastAPI:
    broadcaster = Broadcaster()
    session = SessionService(ctx)
    fetcher = FetchAndAnalyzeService(ctx)
    editor = EditService(ctx)
    submitter = SubmitService(ctx)
    deadline = DeadlineService(ctx)
    history = HistoryService(ctx)
    cfgsvc = ConfigService(ctx.config)
    datasets = DatasetService(ctx)

    async def on_state(item: ReviewItem) -> None:
        # 사이클 7: 전이마다 집계를 실어 보내 제출 직후 헤더 건수가 갱신되게 한다
        try:
            summary = await history.summary()
        except Exception as e:  # 집계 실패가 상태 전달을 막지 않도록
            log.warning("summary for SSE failed: %s", e)
            summary = None
        broadcaster.publish("state", snapshot_payload(item, summary, datasets.snapshot()))

    ctx.sm.subscribe(on_state)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if manage_browser:
            try:
                await ctx.browser.start()
                ctx.background.append(asyncio.create_task(session.ensure_login(), name="ensure-login"))
            except Exception as e:
                log.exception("browser start failed")
                ctx.sm.set_flags(browser_alive=False)
                ctx.sm.add_warning(f"브라우저 시작 실패: {e}")
            ctx.background.append(asyncio.create_task(session.liveness_loop(), name="liveness"))
        ctx.background.append(asyncio.create_task(deadline.loop(), name="deadline"))
        ctx.background.append(asyncio.create_task(history.cleanup_loop(), name="cleanup"))
        if open_browser:
            import webbrowser

            webbrowser.open(f"http://127.0.0.1:{ctx.config.ui_port}")
        try:
            yield
        finally:
            ctx.shutdown_event.set()
            await fetcher.cancel()
            await history.on_shutdown()
            for t in ctx.background:
                t.cancel()
            if manage_browser:
                try:
                    await ctx.browser.close()
                except Exception:  # pragma: no cover
                    log.exception("browser close failed")
            await asyncio.to_thread(ctx.repo.close)

    app = FastAPI(title="labelon-reviewer", lifespan=lifespan, docs_url=None, redoc_url=None)
    app.state.ctx = ctx
    app.state.broadcaster = broadcaster

    # -------------------------------------------------------------- Origin 검사 (NFR S-2)
    allowed_hosts = {f"127.0.0.1:{ctx.config.ui_port}", f"localhost:{ctx.config.ui_port}", "testserver"}

    @app.middleware("http")
    async def origin_guard(request: Request, call_next):
        if request.method in ("POST", "PUT", "DELETE", "PATCH"):
            origin = request.headers.get("origin")
            host = request.headers.get("host", "")
            if origin:
                origin_host = origin.split("://", 1)[-1].rstrip("/")
                if origin_host not in allowed_hosts:
                    return JSONResponse({"detail": "허용되지 않은 Origin"}, status_code=403)
            elif host not in allowed_hosts:
                return JSONResponse({"detail": "허용되지 않은 Host"}, status_code=403)
        return await call_next(request)

    def error_response(e: Exception) -> JSONResponse:
        if isinstance(e, IllegalTransition):
            return JSONResponse({"detail": str(e)}, status_code=409)
        if isinstance(e, ItemExpired):
            return JSONResponse({"detail": str(e), "expired": True}, status_code=410)
        if isinstance(e, SubmitError):
            return JSONResponse({"detail": str(e)}, status_code=422)
        log.exception("unhandled")
        return JSONResponse({"detail": f"내부 오류: {e}"}, status_code=500)

    # -------------------------------------------------------------- 정적·상태
    NO_CACHE = {"Cache-Control": "no-cache, must-revalidate"}

    @app.get("/")
    async def index():
        # 브라우저가 옛 app.js/style.css 를 쓰지 않도록 버전 쿼리를 붙이고 캐시를 금지한다 (2026-10-01)
        html = (STATIC / "index.html").read_text(encoding="utf-8")
        html = html.replace('href="/static/style.css"', f'href="/static/style.css?v={__version__}"')
        html = html.replace('src="/static/app.js"', f'src="/static/app.js?v={__version__}"')
        return HTMLResponse(html, headers=NO_CACHE)

    @app.get("/static/{name}")
    async def static_file(name: str):
        p = (STATIC / name).resolve()
        if p.parent != STATIC.resolve() or not p.exists():
            raise HTTPException(404)
        return FileResponse(p, headers=NO_CACHE)

    @app.get("/state")
    async def state():
        return snapshot_payload(ctx.sm.snapshot(), await history.summary(), datasets.snapshot())

    @app.get("/config")
    async def config():
        return cfgsvc.public()

    @app.get("/events")
    async def events(request: Request):
        q = broadcaster.subscribe()

        async def gen():
            try:
                yield f"event: state\ndata: {json.dumps(snapshot_payload(ctx.sm.snapshot(), await history.summary(), datasets.snapshot()), ensure_ascii=False, default=str)}\n\n"
                while True:
                    if await request.is_disconnected():
                        break
                    try:
                        msg = await asyncio.wait_for(q.get(), timeout=HEARTBEAT_SECONDS)
                        yield msg
                    except TimeoutError:
                        yield ": ping\n\n"
            finally:
                broadcaster.unsubscribe(q)

        return StreamingResponse(gen(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    # -------------------------------------------------------------- 동작
    @app.post("/actions/fetch", status_code=202)
    async def action_fetch():
        try:
            fetcher.start()
        except Exception as e:
            return error_response(e)
        return {"started": True}

    @app.put("/draft")
    async def put_draft(body: DraftEdit):
        try:
            item = await editor.edit(body.field, body.value)
        except Exception as e:
            return error_response(e)
        return snapshot_payload(item)

    @app.post("/actions/revert-field")
    async def action_revert_field(body: RevertField):
        try:
            item = await editor.revert_field(body.field)
        except Exception as e:
            return error_response(e)
        return snapshot_payload(item)

    @app.post("/actions/revert")
    async def action_revert():
        try:
            item = await editor.revert()
        except Exception as e:
            return error_response(e)
        return snapshot_payload(item)

    @app.post("/actions/approve")
    async def action_approve():
        try:
            item = await submitter.approve()
        except Exception as e:
            return error_response(e)
        return snapshot_payload(item)

    @app.post("/actions/impossible")
    async def action_impossible(body: ImpossibleBody):
        try:
            item = await submitter.impossible(body.reason)
        except Exception as e:
            return error_response(e)
        return snapshot_payload(item)

    @app.post("/actions/reanalyze", status_code=202)
    async def action_reanalyze():
        try:
            fetcher.start_reanalyze()
        except Exception as e:
            return error_response(e)
        return {"started": True}

    @app.post("/actions/skip")
    async def action_skip():
        try:
            item = await submitter.skip()
        except Exception as e:
            return error_response(e)
        return snapshot_payload(item)

    @app.post("/actions/reopen-browser")
    async def action_reopen():
        try:
            await session.reopen_browser()
        except Exception as e:
            return error_response(e)
        return {"ok": True}

    @app.post("/actions/shutdown")
    async def action_shutdown():
        ctx.shutdown_event.set()
        if ctx.login_watch_task and not ctx.login_watch_task.done():
            ctx.login_watch_task.cancel()
        loop = asyncio.get_running_loop()
        loop.call_later(0.5, _request_exit)
        return {"ok": True}

    # -------------------------------------------------------------- 데이터셋 (cycle 2)
    @app.get("/datasets")
    async def datasets_get():
        return datasets.snapshot()

    @app.post("/datasets/refresh")
    async def datasets_refresh():
        await datasets.refresh()
        return datasets.snapshot()

    @app.put("/datasets/selected")
    async def datasets_select(body: DatasetSelectBody):
        try:
            datasets.select(body.dataset_id)
        except IllegalTransition as e:
            return JSONResponse({"detail": str(e)}, status_code=409)
        except ValueError as e:
            return JSONResponse({"detail": str(e)}, status_code=422)
        return datasets.snapshot()

    # -------------------------------------------------------------- 이력
    @app.get("/history")
    async def history_list(limit: int = 50):
        return {"items": await history.list_recent(limit), "unfinished": await history.unfinished()}

    @app.get("/history/summary")
    async def history_summary():
        return await history.summary()

    @app.get("/history/{item_id}")
    async def history_detail(item_id: int):
        d = await history.detail(item_id)
        if d is None:
            raise HTTPException(404)
        return d

    @app.get("/images/{item_id}")
    async def image(item_id: int):
        name = await asyncio.to_thread(ctx.repo.file_name_for, item_id)
        if not name:
            raise HTTPException(404)
        p = (ctx.images.cache_dir / Path(name).name).resolve()
        if p.parent != ctx.images.cache_dir.resolve() or not p.exists():
            raise HTTPException(404)
        return FileResponse(p)

    return app


def _request_exit() -> None:
    import os
    import signal

    os.kill(os.getpid(), signal.SIGINT)
