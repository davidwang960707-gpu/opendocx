"""API 集成测试"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    resp = await client.post("/api/v1/auth/login", json={"email": "no@user.com", "password": "bad"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_projects_crud(client: AsyncClient, admin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Create
    resp = await client.post("/api/v1/projects", json={
        "name": "Test Project", "slug": "test-proj", "description": "A test"
    }, headers=headers)
    assert resp.status_code == 201
    project_id = resp.json()["data"]["id"]

    # List
    resp = await client.get("/api/v1/projects", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()["data"]) >= 1

    # Get
    resp = await client.get(f"/api/v1/projects/{project_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["name"] == "Test Project"

    # Update
    resp = await client.put(f"/api/v1/projects/{project_id}", json={"description": "Updated"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["description"] == "Updated"

    # Delete
    resp = await client.delete(f"/api/v1/projects/{project_id}", headers=headers)
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_unauthenticated_access(client: AsyncClient):
    resp = await client.get("/api/v1/projects")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_stats(client: AsyncClient, admin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = await client.get("/api/v1/stats", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "project_count" in data
    assert "document_count" in data
    assert "published_count" in data


@pytest.mark.asyncio
async def test_document_revision_conflict_returns_409(client: AsyncClient, admin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}

    project_resp = await client.post(
        "/api/v1/projects",
        json={"name": "Conflict Project", "slug": "conflict-project"},
        headers=headers,
    )
    assert project_resp.status_code == 201
    version_id = project_resp.json()["data"]["default_version_id"]

    create_resp = await client.post(
        f"/api/v1/versions/{version_id}/documents",
        json={"title": "Conflict Doc", "slug": "conflict-doc", "content": "base"},
        headers=headers,
    )
    assert create_resp.status_code == 201
    doc = create_resp.json()["data"]
    assert doc["revision"] == 1

    first_save = await client.put(
        f"/api/v1/documents/{doc['id']}",
        json={"content": "alice edit", "base_revision": 1},
        headers=headers,
    )
    assert first_save.status_code == 200
    assert first_save.json()["data"]["revision"] == 2

    stale_save = await client.put(
        f"/api/v1/documents/{doc['id']}",
        json={"content": "bob edit", "base_revision": 1},
        headers=headers,
    )
    assert stale_save.status_code == 409
    detail = stale_save.json()["detail"]
    assert detail["code"] == "document_conflict"
    assert detail["latest_revision"] == 2
    assert detail["latest_content"] == "alice edit"
    assert detail["draft_content"] == "bob edit"
