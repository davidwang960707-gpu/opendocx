"""Editor AI 路由测试 — P0-B-2/3

不真发 LLM 请求 — 用 monkeypatch 替换 provider.stream。
覆盖：4 个 action / 鉴权 / action 校验 / SSE 事件格式。

使用 conftest 的 admin_token fixture 和 AsyncClient。
"""
import os
import json
import pytest
from fastapi.testclient import TestClient
from app.main import app


def _parse_sse(text: str) -> list[dict]:
    """把 SSE 文本解析成 [{event, data}]"""
    events = []
    cur = {}
    for line in text.split("\n"):
        if line.startswith("event: "):
            cur["event"] = line[7:]
        elif line.startswith("data: "):
            cur["data"] = json.loads(line[6:])
        elif line == "" and cur:
            events.append(cur)
            cur = {}
    return events


@pytest.fixture
def mock_provider(monkeypatch):
    """替换 endpoint 里实际 import 的 get_provider，模拟 LLM 流式输出"""
    class FakeProvider:
        model = "fake-model"
        async def stream(self, messages, **kwargs):
            for chunk in ["这是", "一段", "测试", "输出"]:
                yield chunk
    import app.routers.editor as editor_module
    monkeypatch.setattr(editor_module, "get_provider", lambda: FakeProvider())


# ── 公开端点 ──────────────────────────────────────────

def test_health_returns_provider():
    os.environ["LLM_API_KEY"] = "test-openai-key-000000000000"
    c = TestClient(app)
    r = c.get("/api/v1/editor/health")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert "provider" in body
    assert "model" in body
    os.environ.pop("LLM_API_KEY", None)


# ── AI 端点鉴权 ──────────────────────────────────────────

def test_ai_requires_auth():
    c = TestClient(app)
    r = c.post("/api/v1/editor/ai", json={"action": "continue", "content": "x"})
    assert r.status_code == 401


def test_actions_requires_auth():
    c = TestClient(app)
    r = c.get("/api/v1/editor/actions")
    assert r.status_code == 401


# ── AI 端点校验 ──────────────────────────────────────────

def test_ai_rejects_unknown_action(admin_token):
    from httpx import AsyncClient, ASGITransport
    import asyncio
    async def run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.post(
                "/api/v1/editor/ai",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={"action": "foo", "content": "x"},
            )
            return r
    r = asyncio.run(run())
    assert r.status_code == 400
    assert "action 必须是" in r.json()["detail"]


def test_ai_requires_content_for_continue(admin_token):
    from httpx import AsyncClient, ASGITransport
    import asyncio
    async def run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.post(
                "/api/v1/editor/ai",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={"action": "continue", "content": ""},
            )
            return r
    r = asyncio.run(run())
    assert r.status_code == 400


def test_ai_requires_question_for_qa(admin_token):
    from httpx import AsyncClient, ASGITransport
    import asyncio
    async def run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.post(
                "/api/v1/editor/ai",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={"action": "qa", "content": "x"},
            )
            return r
    r = asyncio.run(run())
    assert r.status_code == 400


# ── AI 端点功能（mock） ──────────────────────────────────────────

def _post_ai(token, body):
    from httpx import AsyncClient, ASGITransport
    import asyncio
    async def run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.post(
                "/api/v1/editor/ai",
                headers={"Authorization": f"Bearer {token}"},
                json=body,
            )
            return r
    return asyncio.run(run())


@pytest.mark.parametrize("action", ["continue", "rewrite", "explain", "qa", "summarize", "polish"])
def test_ai_returns_sse_stream(admin_token, mock_provider, action):
    print(f"\n>>> test_ai_returns_sse_stream[{action}] admin_token type={type(admin_token)} len={len(admin_token) if admin_token else 0!r}")
    body = {"action": action, "content": "这是测试内容。", "selection": "测试"}
    if action == "qa":
        body["question"] = "什么是 X？"
    r = _post_ai(admin_token, body)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/event-stream")

    events = _parse_sse(r.text)
    event_types = [e["event"] for e in events]
    assert "meta" in event_types
    assert "done" in event_types
    tokens = [e for e in events if e["event"] == "token"]
    assert len(tokens) >= 1
    full = "".join(t["data"]["delta"] for t in tokens)
    assert "测试" in full


def test_ai_meta_includes_action_and_model(admin_token, mock_provider):
    r = _post_ai(admin_token, {"action": "summarize", "content": "一些内容"})
    events = _parse_sse(r.text)
    meta = next(e for e in events if e["event"] == "meta")
    assert meta["data"]["action"] == "summarize"
    assert "model" in meta["data"]


# ── actions 端点 ──────────────────────────────────────────

def test_actions_returns_6(admin_token):
    from httpx import AsyncClient, ASGITransport
    import asyncio
    async def run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.get(
                "/api/v1/editor/actions",
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            return r
    r = asyncio.run(run())
    assert r.status_code == 200
    actions = r.json()["actions"]
    assert len(actions) == 6
    ids = {a["id"] for a in actions}
    assert ids == {"continue", "rewrite", "explain", "qa", "summarize", "polish"}
