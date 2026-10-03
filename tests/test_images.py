import io
import os
import time

from PIL import Image

from labelon_reviewer.images import ImageService, resize_bytes, target_size


def _jpeg(w, h):
    buf = io.BytesIO()
    Image.new("RGB", (w, h), "white").save(buf, format="JPEG")
    return buf.getvalue()


def test_target_size():
    assert target_size(4000, 3000, 1568) == (1568, 1176)
    assert target_size(800, 600, 1568) == (800, 600)


def test_resize_bytes_downscales():
    out = resize_bytes(_jpeg(4000, 3000), 1568)
    with Image.open(io.BytesIO(out)) as im:
        assert im.size == (1568, 1176)


async def test_fetch_and_cleanup(tmp_path, sample_item):
    svc = ImageService(tmp_path / "cache", tmp_path / "resized", 400)
    calls = []

    async def fetcher(url):
        calls.append(url)
        return _jpeg(1200, 900)

    paths = await svc.fetch(fetcher, sample_item)
    assert os.path.exists(paths.original) and os.path.exists(paths.resized)
    with Image.open(paths.resized) as im:
        assert im.size == (400, 300)
    await svc.fetch(fetcher, sample_item)  # 캐시 재사용
    assert len(calls) == 1

    old = time.time() - 10 * 86400
    os.utime(paths.original, (old, old))
    os.utime(paths.resized, (old, old))
    assert svc.cleanup(7) == 2
    assert svc.cleanup(0) == 0
