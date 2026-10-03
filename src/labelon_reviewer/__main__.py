"""진입점: python -m labelon_reviewer --config config.yaml"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from . import __version__
from .config import AppConfig, load
from .domain import ConfigError
from .history import HistoryRepository
from .images import ImageService
from .judge import JudgeStage
from .labelon.browser import BrowserSession
from .labelon.parser import field_locators
from .labelon.submitter import Submitter
from .model import make_client
from .revise import ReviseStage
from .services import AppContext
from .state import ReviewStateMachine


def setup_logging(cfg: AppConfig, debug: bool) -> None:
    cfg.logs_dir.mkdir(parents=True, exist_ok=True)
    level = logging.DEBUG if debug else logging.INFO
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    root = logging.getLogger()
    root.setLevel(level)
    fh = RotatingFileHandler(cfg.logs_dir / "app.log", maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8")
    fh.setFormatter(fmt)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    root.handlers[:] = [fh, sh]
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def build_context(cfg: AppConfig) -> AppContext:
    model = make_client(cfg)
    return AppContext(
        config=cfg, sm=ReviewStateMachine(), repo=HistoryRepository(cfg.db_path), browser=BrowserSession(cfg),
        images=ImageService(cfg.cache_dir, cfg.resized_dir, cfg.image_max_side),
        judge=JudgeStage(cfg, model), revise=ReviseStage(cfg, model), submitter=Submitter(field_locators()),
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="labelon-reviewer", description="LabelOn UC-LE 초안 검토 도구")
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--debug", action="store_true")
    ap.add_argument("--no-browser", action="store_true", help="검토 화면을 기본 브라우저로 자동 열지 않음")
    ap.add_argument("--no-chrome", action="store_true", help="LabelOn Chrome 창을 띄우지 않음(UI 개발용)")
    ap.add_argument("--version", action="version", version=__version__)
    args = ap.parse_args(argv)

    try:
        cfg = load(args.config)
    except ConfigError as e:
        print(str(e), file=sys.stderr)
        return 2
    cfg.ensure_dirs()
    setup_logging(cfg, args.debug)
    log = logging.getLogger("labelon_reviewer")
    log.info("labelon-reviewer %s starting (dataset=%s, backend=%s)", __version__, cfg.dataset_id, cfg.model_backend)
    if os.environ.get("ANTHROPIC_API_KEY") and cfg.model_backend == "claude_cli":
        log.warning("ANTHROPIC_API_KEY 가 설정되어 있습니다. Claude Code 는 로그인 대신 이 키를 사용합니다")

    import uvicorn

    from .web.app import create_app

    ctx = build_context(cfg)
    app = create_app(ctx, manage_browser=not args.no_chrome, open_browser=not args.no_browser)
    try:
        uvicorn.run(app, host="127.0.0.1", port=cfg.ui_port, log_level="warning")
    except OSError as e:
        log.error("서버 시작 실패 (포트 %d 사용 중?): %s. config.yaml 의 ui_port 를 바꾸세요", cfg.ui_port, e)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
