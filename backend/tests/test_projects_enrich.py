"""P1-UI-1/2: ProjectOut enrich 注入测试
验证 list / get / create / update 4 个项目接口都正确注入
status / default_version_id / doc_count / last_activity_at。
"""
import pytest
from httpx import AsyncClient


async def _create_project(client: AsyncClient, headers: dict, slug: str, name: str) -> dict:
    r = await client.post("/api/v1/projects", json={
        "name": name, "slug": slug, "description": "test",
    }, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()["data"]


@pytest.mark.asyncio
async def test_create_project_enriches_status_and_counts(client: AsyncClient, admin_token: str):
    """新建项目后应自动有 1 个 draft 文档 → status=active（draft version + 有文档）。"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    proj = await _create_project(client, headers, "test-enrich-1", "Enrich Test 1")
    assert proj["status"] == "active", f"expected active, got {proj['status']}"
    # 1.0 自动建 getting-started draft + seed 自动建 index doc, 所以 doc_count 应 >= 1
    assert proj["doc_count"] >= 1, f"expected >= 1 doc, got {proj['doc_count']}"
    assert proj["default_version_id"] is not None
    assert proj["last_activity_at"] is not None


@pytest.mark.asyncio
async def test_list_projects_includes_enrichment(client: AsyncClient, admin_token: str):
    """列表接口也应 enrich 每个项目。"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    await _create_project(client, headers, "test-enrich-2", "Enrich Test 2")
    r = await client.get("/api/v1/projects", headers=headers)
    assert r.status_code == 200
    items = r.json()["data"]
    assert len(items) >= 1
    for p in items:
        assert "status" in p
        assert "doc_count" in p
        assert "default_version_id" in p
        assert "last_activity_at" in p


@pytest.mark.asyncio
async def test_get_project_enriches(client: AsyncClient, admin_token: str):
    """单个 get 也 enrich。"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    proj = await _create_project(client, headers, "test-enrich-3", "Enrich Test 3")
    r = await client.get(f"/api/v1/projects/{proj['id']}", headers=headers)
    assert r.status_code == 200
    p = r.json()["data"]
    assert p["status"] in ("active", "paused", "draft")
    assert isinstance(p["doc_count"], int)
    assert p["default_version_id"] is not None


@pytest.mark.asyncio
async def test_update_project_enriches(client: AsyncClient, admin_token: str):
    """update 路径也 enrich。"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    proj = await _create_project(client, headers, "test-enrich-4", "Enrich Test 4")
    r = await client.put(f"/api/v1/projects/{proj['id']}", json={
        "description": "updated",
    }, headers=headers)
    assert r.status_code == 200
    p = r.json()["data"]
    assert p["status"] in ("active", "paused", "draft")
    assert p["description"] == "updated"
