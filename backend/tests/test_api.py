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
