"""이미지 서비스 C-04: 다운로드(주입된 fetcher), 캐시, 축소, 정리."""

from __future__ import annotations

import asyncio
import io
import logging
import time
from collections.abc import Awaitable, Callable
from pathlib import Path

from PIL import Image, ImageOps

from .domain import ImagePaths, SourceItem

log = logging.getLogger(__name__)

Fetcher = Callable[[str], Awaitable[bytes]]


def resize_bytes(data: bytes, max_side: int, quality: int = 85) -> bytes:
    with Image.open(io.BytesIO(data)) as im:
        im = ImageOps.exif_transpose(im)
        im = im.convert("RGB")
        w, h = im.size
        scale = min(1.0, max_side / max(w, h))
        if scale < 1.0:
            im = im.resize((max(1, round(w * scale)), max(1, round(h * scale))), Image.LANCZOS)
        out = io.BytesIO()
        im.save(out, format="JPEG", quality=quality, optimize=True)
        return out.getvalue()


def target_size(w: int, h: int, max_side: int) -> tuple[int, int]:
    scale = min(1.0, max_side / max(w, h))
    return (max(1, round(w * scale)), max(1, round(h * scale)))


class ImageService:
    def __init__(self, cache_dir: Path, resized_dir: Path, max_side: int) -> None:
        self.cache_dir = Path(cache_dir)
        self.resized_dir = Path(resized_dir)
        self.max_side = max_side
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.resized_dir.mkdir(parents=True, exist_ok=True)

    def _name(self, item: SourceItem) -> str:
        n = item.file_name or item.image_url.rsplit("/", 1)[-1] or f"{item.job_id}.jpg"
        return Path(n).name

    async def fetch(self, fetcher: Fetcher, item: SourceItem) -> ImagePaths:
        name = self._name(item)
        original = self.cache_dir / name
        resized = self.resized_dir / (Path(name).stem + ".jpg")
        if not original.exists():
            data = await fetcher(item.image_url)
            await asyncio.to_thread(original.write_bytes, data)
        if not resized.exists():
            data = await asyncio.to_thread(original.read_bytes)
            small = await asyncio.to_thread(resize_bytes, data, self.max_side)
            await asyncio.to_thread(resized.write_bytes, small)
        return ImagePaths(original=str(original.resolve()), resized=str(resized.resolve()))

    def cleanup(self, retention_days: int) -> int:
        if retention_days <= 0:
            return 0
        cutoff = time.time() - retention_days * 86400
        removed = 0
        for d in (self.cache_dir, self.resized_dir):
            for p in d.iterdir():
                if p.is_file() and p.stat().st_mtime < cutoff:
                    try:
                        p.unlink()
                        removed += 1
                    except OSError as e:  # pragma: no cover
                        log.warning("cache cleanup failed %s: %s", p, e)
        return removed
