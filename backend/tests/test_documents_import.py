"""Markdown 批量导入测试 — P1-UI-3

复用 conftest 的 admin_token 和 client fixture
"""
import io
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


def _md(content: str, filename: str):
    return (filename, io.BytesIO(content.encode("utf-8")))


@pytest.fixture
async def version_id(admin_token):
    """建项目 + 拿 version id（admin_token 只创建 user，没项目）"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post(
            "/api/v1/projects",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"name": "Import Test", "slug": "import-test", "description": "test"},
        )
        assert r.status_code == 201, f"create project failed: {r.text}"
        pid = r.json()["data"]["id"]
        r = await ac.get(
            f"/api/v1/projects/{pid}/versions",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        return r.json()["data"][0]["id"]


@pytest.mark.asyncio
async def test_import_requires_auth(version_id):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post(
            f"/api/v1/versions/{version_id}/documents/import",
            files=[("files", ("a.md", io.BytesIO(b"# A\n")))],
        )
        assert r.status_code == 401


@pytest.mark.asyncio
async def test_import_404_version(admin_token):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post(
            "/api/v1/versions/nonexistent/documents/import",
            headers={"Authorization": f"Bearer {admin_token}"},
            files=[("files", ("a.md", io.BytesIO(b"# A\n")))],
        )
        assert r.status_code == 404


@pytest.mark.asyncio
async def test_import_single_no_frontmatter(admin_token, version_id):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post(
            f"/api/v1/versions/{version_id}/documents/import",
            headers={"Authorization": f"Bearer {admin_token}"},
            files=[("files", _md("# Hello World\n\n这是内容", "hello-world.md"))],
        )
        assert r.status_code == 201
        body = r.json()["data"]
        assert len(body["imported"]) == 1
        assert body["imported"][0]["title"] == "hello-world"
        assert body["imported"][0]["slug"] == "hello-world"
        assert body["errors"] == []


@pytest.mark.asyncio
async def test_import_with_frontmatter(admin_token, version_id):
    fm = "---\ntitle: 快速入门\nslug: quickstart\n---\n# 快速入门\n\n正文"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post(
            f"/api/v1/versions/{version_id}/documents/import",
            headers={"Authorization": f"Bearer {admin_token}"},
            files=[("files", _md(fm, "01-quickstart.md"))],
        )
        assert r.status_code == 201
        doc = r.json()["data"]["imported"][0]
        assert doc["title"] == "快速入门"
        assert doc["slug"] == "quickstart"
        r2 = await ac.get(f"/api/v1/documents/{doc['id']}", headers={"Authorization": f"Bearer {admin_token}"})
        full = r2.json()["data"]["content"]
        assert "---" not in full.split("\n\n")[0]
        assert "# 快速入门" in full


@pytest.mark.asyncio
async def test_import_slug_conflict_renames(admin_token, version_id):
    fm = "---\nslug: same-slug\n---\n# Doc"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r1 = await ac.post(
            f"/api/v1/versions/{version_id}/documents/import",
            headers={"Authorization": f"Bearer {admin_token}"},
            files=[("files", _md(fm, "a.md"))],
        )
        assert r1.status_code == 201
        assert r1.json()["data"]["imported"][0]["slug"] == "same-slug"

        r2 = await ac.post(
            f"/api/v1/versions/{version_id}/documents/import",
            headers={"Authorization": f"Bearer {admin_token}"},
            files=[("files", _md(fm, "b.md"))],
        )
        assert r2.json()["data"]["imported"][0]["slug"] == "same-slug-2"


@pytest.mark.asyncio
async def test_import_batch_multiple_files(admin_token, version_id):
    files = [_md("# First\n", "first.md"), _md("# Second\n", "second.md"), _md("# Third\n", "third.md")]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post(
            f"/api/v1/versions/{version_id}/documents/import",
            headers={"Authorization": f"Bearer {admin_token}"},
            files=[("files", f) for f in files],
        )
        assert r.status_code == 201
        body = r.json()["data"]
        assert len(body["imported"]) == 3
        assert {d["slug"] for d in body["imported"]} == {"first", "second", "third"}


@pytest.mark.asyncio
async def test_import_chinese_filename(admin_token, version_id):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post(
            f"/api/v1/versions/{version_id}/documents/import",
            headers={"Authorization": f"Bearer {admin_token}"},
            files=[("files", _md("# 快速入门", "快速入门.md"))],
        )
        assert r.status_code == 201
        doc = r.json()["data"]["imported"][0]
        assert "快速入门" in doc["slug"] or doc["slug"] == "doc"
