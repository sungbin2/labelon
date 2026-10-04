import pytest
from fastapi.testclient import TestClient

from labelon_reviewer.web.app import create_app
from tests.conftest import judge_raw_all_true
from tests.test_services import make_ctx


@pytest.fixture
def client(config, tmp_path, job_page_html):
    ctx = make_ctx(config, tmp_path, job_page_html, judge_raw=judge_raw_all_true())
    app = create_app(ctx, manage_browser=False, open_browser=False)
    with TestClient(app) as c:
        c.ctx = ctx
        yield c


def test_state_and_config(client):
    r = client.get("/state")
    assert r.status_code == 200 and r.json()["state"] == "READY" and "summary" in r.json()
    c = client.get("/config").json()
    assert c["dataset_id"] == 688 and c["threshold"] == 40


def test_origin_guard(client):
    r = client.post("/actions/fetch", headers={"origin": "https://evil.example"})
    assert r.status_code == 403
    r = client.post("/actions/revert", headers={"host": "192.168.0.5:8765"})
    assert r.status_code == 403


def test_approve_wrong_state_409(client):
    r = client.post("/actions/approve", headers={"origin": "http://testserver"})
    assert r.status_code == 409


def test_index_busts_static_cache(client):
    """옛 app.js 캐시로 편집 지연 변경이 반영되지 않던 문제 (2026-10-01)."""
    from labelon_reviewer import __version__

    r = client.get("/")
    assert r.status_code == 200 and f'/static/app.js?v={__version__}' in r.text and "no-cache" in r.headers["cache-control"]
    assert client.get("/state").json()["server_version"] == __version__  # 화면 자동 새로고침 근거
    s = client.get("/static/app.js?v=x")
    assert s.status_code == 200 and "no-cache" in s.headers["cache-control"]


def test_fetch_then_edit_and_submit(client):
    import time

    r = client.post("/actions/fetch", headers={"origin": "http://testserver"})
    assert r.status_code == 202
    # 백그라운드 태스크 완료 대기
    for _ in range(50):
        s = client.get("/state").json()
        if s["state"] in ("REVIEW", "ERROR"):
            break
        time.sleep(0.05)
    assert s["state"] == "REVIEW", s.get("error")
    dup = client.post("/actions/fetch", headers={"origin": "http://testserver"})
    assert dup.status_code == 409

    r = client.put("/draft", json={"field": "scene", "value": "수정된 장면."}, headers={"origin": "http://testserver"})
    assert r.status_code == 200 and r.json()["final"]["scene"] == "수정된 장면."
    r = client.put("/draft", json={"field": "turn_1_user", "value": "바뀐 질문"}, headers={"origin": "http://testserver"})  # 사이클 6
    assert r.status_code == 200 and r.json()["final"]["dialogue"]["turns"][0]["user"] == "바뀐 질문"
    assert client.get("/config").json()["edit_delay_ms"] == 1500
    assert "일상지원" in client.get("/config").json()["archetype_templates"]  # 사이클 7
    r = client.put("/draft", json={"field": "task", "value": "사람이 고친 task"}, headers={"origin": "http://testserver"})
    assert r.status_code == 200 and r.json()["final"]["instruction"]["task"] == "사람이 고친 task"
    assert any(d["field"] == "task" and d["changed"] for d in r.json()["diffs"])
    r = client.post("/actions/revert-field", json={"field": "task"}, headers={"origin": "http://testserver"})  # 사이클 8
    assert r.status_code == 200 and not any(d["field"] == "task" and d["changed"] for d in r.json()["diffs"])
    assert r.json()["final"]["scene"] == "수정된 장면." and r.json()["final"]["dialogue"]["turns"][0]["user"] == "바뀐 질문"
    r = client.post("/actions/revert", headers={"origin": "http://testserver"})
    assert r.json()["final"]["scene"] != "수정된 장면."

    # 픽스처 마감은 과거 → 410 EXPIRED
    r = client.post("/actions/approve", headers={"origin": "http://testserver"})
    assert r.status_code == 410 and client.get("/state").json()["state"] == "EXPIRED"


def test_image_and_history_404(client):
    assert client.get("/images/999").status_code == 404
    assert client.get("/history/999").status_code == 404
    assert client.get("/static/../pyproject.toml").status_code in (404, 400)
    assert client.get("/history").json()["items"] == []


def test_datasets_endpoints(client):
    import time

    r = client.post("/datasets/refresh", headers={"origin": "http://testserver"})
    assert r.status_code == 200 and [d["dataset_id"] for d in r.json()["datasets"]] == [688, 687, 686, 685, 684, 682]
    assert client.get("/datasets").json()["selected_dataset_id"] == 688
    r = client.put("/settings/ai", json={"enabled": False}, headers={"origin": "http://testserver"})  # 사이클 11
    assert r.status_code == 200 and r.json()["ai_enabled"] is False and client.get("/state").json()["ai_enabled"] is False
    client.put("/settings/ai", json={"enabled": True}, headers={"origin": "http://testserver"})
    assert client.get("/state").json()["selected_dataset_name"].endswith("(어린이3)")
    r = client.put("/datasets/selected", json={"dataset_id": 684}, headers={"origin": "http://testserver"})
    assert r.status_code == 200 and r.json()["selected_dataset_id"] == 684
    assert client.put("/datasets/selected", json={"dataset_id": 1}, headers={"origin": "http://testserver"}).status_code == 422
    client.post("/actions/fetch", headers={"origin": "http://testserver"})
    for _ in range(50):
        s = client.get("/state").json()
        if s["state"] in ("REVIEW", "ERROR"):
            break
        time.sleep(0.05)
    assert s["state"] == "REVIEW" and client.ctx.browser.opened == [684]
    assert client.put("/datasets/selected", json={"dataset_id": 688}, headers={"origin": "http://testserver"}).status_code == 409
