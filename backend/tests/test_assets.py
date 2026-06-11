"""文档资产上传与静态构建测试"""
import os

import pytest
from httpx import AsyncClient


async def _create_project_and_get_starter(client: AsyncClient, headers: dict) -> tuple[str, str]:
    resp = await client.post(
        "/api/v1/projects",
        json={"name": "Asset Project", "slug": "asset-project"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    project_id = resp.json()["data"]["id"]

    resp = await client.get(f"/api/v1/projects/{project_id}/versions", headers=headers)
    assert resp.status_code == 200
    version_id = resp.json()["data"][0]["id"]

    resp = await client.get(f"/api/v1/versions/{version_id}/documents", headers=headers)
    assert resp.status_code == 200
    starter = next(d for d in resp.json()["data"] if d["slug"] == "getting-started")
    return version_id, starter["id"]


@pytest.mark.asyncio
async def test_upload_asset_and_build_rewrites_to_static_path(client: AsyncClient, admin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}
    version_id, doc_id = await _create_project_and_get_starter(client, headers)

    upload = await client.post(
        f"/api/v1/versions/{version_id}/assets",
        files={"file": ("screenshot.png", b"\x89PNG\r\n\x1a\nopendocx", "image/png")},
        headers=headers,
    )
    assert upload.status_code == 201, upload.text
    asset = upload.json()["data"]
    assert asset["kind"] == "image"
    assert asset["file_url"] == f"/api/v1/assets/{asset['id']}/file"
    assert asset["markdown"] == f"![screenshot.png](/api/v1/assets/{asset['id']}/file)"

    listed = await client.get(f"/api/v1/versions/{version_id}/assets", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["data"][0]["id"] == asset["id"]

    file_resp = await client.get(asset["file_url"])
    assert file_resp.status_code == 200
    assert file_resp.content.startswith(b"\x89PNG")

    update = await client.put(
        f"/api/v1/documents/{doc_id}",
        json={
            "content": f"# Asset Demo\n\n{asset['markdown']}\n",
            "status": "published",
        },
        headers=headers,
    )
    assert update.status_code == 200, update.text

    build = await client.post(f"/api/v1/build/{version_id}", headers=headers)
    assert build.status_code == 200, build.text
    assert build.json()["data"]["status"] == "success"

    from app.config import get_settings

    settings = get_settings()
    build_dir = os.path.join(settings.data_dir, "builds", "asset-project", "v1.0")
    html_path = os.path.join(build_dir, "getting-started.html")
    copied_asset = os.path.join(build_dir, asset["public_path"])
    assert os.path.exists(html_path)
    assert os.path.exists(copied_asset)

    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()
    assert "/api/v1/assets/" not in html
    assert f'src="{asset["public_path"]}"' in html
