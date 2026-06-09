"""P1-UI-6 高级 AI 卡 — /api/v1/editor/analyze 端点集成测试"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_analyze_requires_auth(client: AsyncClient):
    r = await client.post("/api/v1/editor/analyze", json={"content": "x"})
    assert r.status_code in (401, 403)  # 401 = no token, 403 = invalid


@pytest.mark.asyncio
async def test_analyze_returns_all_sections(client: AsyncClient, admin_token: str):
    """正常返回 5 个 section + 真实分析数据"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    body = {
        "content": """# API 参考

## 鉴权

调用 API。错误码 401 表示未授权。

### GET /api/v1/users

获取用户列表。
""",
    }
    r = await client.post("/api/v1/editor/analyze", json=body, headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert "summary" in data
    assert "health" in data
    assert "terminology" in data
    assert "interface" in data
    assert "knowledge" in data
    assert data["interface"]["endpoints"] == [
        {"method": "GET", "path": "/api/v1/users"}
    ]
    assert 401 in data["interface"]["error_codes"]


@pytest.mark.asyncio
async def test_analyze_with_version_id_finds_related(client: AsyncClient, admin_token: str):
    """传 version_id 时应拉同版本其他文档做知识关联"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    # 先建项目 → 自动有 v1.0 + 快速入门（"getting-started"）文档
    r = await client.post("/api/v1/projects", json={
        "name": "Analyze Test", "slug": "analyze-test",
    }, headers=headers)
    assert r.status_code == 201
    pid = r.json()["data"]["id"]
    # 拿 v1.0
    r = await client.get(f"/api/v1/projects/{pid}/versions", headers=headers)
    vid = r.json()["data"][0]["id"]

    # 改快速入门 doc 标题为 "RAGFlow 入门"，方便关联匹配
    r = await client.get(f"/api/v1/versions/{vid}/documents", headers=headers)
    did = r.json()["data"][0]["id"]
    r = await client.put(f"/api/v1/documents/{did}", json={
        "title": "RAGFlow 架构设计",
    }, headers=headers)
    assert r.status_code == 200

    # 新建第二个 doc，内容包含 RAGFlow
    r = await client.post(f"/api/v1/versions/{vid}/documents", json={
        "title": "部署指南", "slug": "deploy-guide",
        "content": "本文档介绍 RAGFlow 系统的部署流程。",
    }, headers=headers)
    assert r.status_code == 201
    new_doc_id = r.json()["data"]["id"]

    # 现在调 analyze，version_id=vid, doc_id=新 doc
    body = {
        "content": "本文档介绍 RAGFlow 系统的部署、配置和监控。系统采用分布式架构。",
        "version_id": vid,
        "doc_id": new_doc_id,
    }
    r = await client.post("/api/v1/editor/analyze", json=body, headers=headers)
    assert r.status_code == 200
    data = r.json()
    related = data["knowledge"]["related"]
    # 应当能找到 "RAGFlow 架构设计"
    assert any(rel["title"] == "RAGFlow 架构设计" for rel in related)
