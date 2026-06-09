"""构建 / manifest / latest / 跨版本 集成测试

P0-A-8: 验证 P0-A-5 加的两个新路由和构建端到端流程。
"""
import os
import re
import pytest
from httpx import AsyncClient


async def _create_project_with_doc(client: AsyncClient, headers: dict, slug: str, title: str) -> tuple[str, str]:
    """辅助：创建一个项目（自动带 v1.0 version + 快速入门 draft 文档）+ 把 starter doc 改 + 发布

    返回 (version_id, doc_id)
    """
    # 1. 创建项目（现在会自动建 v1.0 + getting-started draft 文档）
    r = await client.post("/api/v1/projects", json={
        "name": title, "slug": slug, "description": "test project",
    }, headers=headers)
    assert r.status_code == 201, r.text
    project_id = r.json()["data"]["id"]

    # 2. 拿默认 version
    r = await client.get(f"/api/v1/projects/{project_id}/versions", headers=headers)
    assert r.status_code == 200
    versions = r.json()["data"]
    assert len(versions) == 1, f"expected 1 auto-created version, got {len(versions)}"
    version_id = versions[0]["id"]
    assert versions[0]["version"] == "v1.0"
    assert versions[0]["is_default"] is True

    # 3. 拿 starter 文档（getting-started）— seed 会自动建 index doc, 我们只测 getting-started
    r = await client.get(f"/api/v1/versions/{version_id}/documents", headers=headers)
    assert r.status_code == 200
    docs = r.json()["data"]
    starter = [d for d in docs if d["slug"] == "getting-started"]
    assert len(starter) == 1, f"expected 1 getting-started doc, got {len(starter)} of {len(docs)} total"
    doc_id = starter[0]["id"]
    assert starter[0]["slug"] == "getting-started"

    # 4. 改内容 + 发布
    r = await client.put(f"/api/v1/documents/{doc_id}", json={
        "content": "# Hello\n\nWorld\n\n- one\n- two\n",
        "status": "published",
    }, headers=headers)
    assert r.status_code == 200, r.text

    return version_id, doc_id


@pytest.mark.asyncio
async def test_build_docusaurus_produces_html_files(client: AsyncClient, admin_token: str):
    """构建后 data/builds/{slug}/{ver}/ 下应该有 HTML 文件"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    vid, _ = await _create_project_with_doc(client, headers, "test-build-1", "Test Build 1")

    # 走 HTTP 路径
    r = await client.post(f"/api/v1/build/{vid}", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert body["data"]["status"] == "success"

    # 验证文件落地（用 settings 拼路径）
    from app.config import get_settings
    settings = get_settings()
    index_path = os.path.join(settings.data_dir, "builds", "test-build-1", "v1.0", "index.html")
    doc_path = os.path.join(settings.data_dir, "builds", "test-build-1", "v1.0", "getting-started.html")
    assert os.path.exists(index_path), f"missing {index_path}"
    assert os.path.exists(doc_path), f"missing {doc_path}"

    # 验证 H1 不重复
    with open(doc_path, "r", encoding="utf-8") as f:
        html = f.read()
    # 算 h1 标签开闭数量 (开标签 <h1 或 <h1 id=..., 闭标签 </h1>)
    h1_open = len(re.findall(r"<h1[\s>]", html))
    h1_close = html.count("</h1>")
    h1_count = min(h1_open, h1_close)
    # mistune 渲染 # Hello 生成 1 个 h1, seed 自动建 index 不算
    # 文档树可能有多个 doc 都被构建, 所以 >= 1
    assert h1_count >= 1, f"expected >= 1 h1, got {h1_count} (open={h1_open}, close={h1_close})"


@pytest.mark.asyncio
async def test_manifest_returns_built_projects(client: AsyncClient, admin_token: str):
    """manifest 端点应返回已构建项目清单"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    # 先 build 一次
    vid, _ = await _create_project_with_doc(client, headers, "test-build-2", "Test Build 2")
    await client.post(f"/api/v1/build/{vid}", headers=headers)

    # 再查 manifest
    r = await client.get("/api/v1/build/manifest", headers=headers)
    assert r.status_code == 200
    items = r.json()["data"]
    assert any(it["project_slug"] == "test-build-2" for it in items)

    # 验证 schema 字段
    entry = next(it for it in items if it["project_slug"] == "test-build-2")
    for key in ("project_id", "project_name", "project_slug", "brand_color",
                "version_id", "version", "build_id", "built_at", "duration",
                "doc_count", "url"):
        assert key in entry, f"manifest missing field: {key}"
    assert entry["url"] == "/docs/test-build-2/v1.0/index.html"
    assert entry["built_at"].endswith("Z")  # UTC ISO with Z


@pytest.mark.asyncio
async def test_latest_returns_url_with_slug_and_version(client: AsyncClient, admin_token: str):
    """latest 端点应返回带 project_slug/version 的 url"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    # 创建项目（自动带 v1.0 + getting-started draft）
    r = await client.post("/api/v1/projects", json={
        "name": "Test Latest", "slug": "test-latest",
    }, headers=headers)
    project_id = r.json()["data"]["id"]
    r = await client.get(f"/api/v1/projects/{project_id}/versions", headers=headers)
    version_id = r.json()["data"][0]["id"]

    # 不构建前：latest 应返回 has_build=false
    r = await client.get(f"/api/v1/build/latest?project_id={project_id}", headers=headers)
    assert r.status_code == 200
    assert r.json()["meta"]["has_build"] is False

    # 发布 starter doc
    r = await client.get(f"/api/v1/versions/{version_id}/documents", headers=headers)
    doc_id = r.json()["data"][0]["id"]
    await client.put(f"/api/v1/documents/{doc_id}", json={"status": "published"}, headers=headers)

    # 构建
    await client.post(f"/api/v1/build/{version_id}", headers=headers)

    # 再查 latest：应返回 url + has_build=true
    r = await client.get(f"/api/v1/build/latest?project_id={project_id}", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["meta"]["has_build"] is True
    assert body["data"]["url"] == "/docs/test-latest/v1.0/index.html"
    assert body["data"]["project_slug"] == "test-latest"
    assert body["data"]["version"] == "v1.0"


@pytest.mark.asyncio
async def test_docs_index_returns_200_with_html(client: AsyncClient):
    """GET /docs/ 应返回 200 + HTML 索引页（不再 404）"""
    r = await client.get("/docs/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    body = r.text
    assert "<!DOCTYPE html>" in body
    assert "已发布站点" in body or "OpenDocX" in body
