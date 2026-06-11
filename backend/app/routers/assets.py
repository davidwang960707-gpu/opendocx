"""文档资产路由"""
import mimetypes
import os
import re
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models import AssetKind, DocumentAsset, User, Version
from app.schemas import ApiResponse, AssetOut
from app.utils.auth import get_current_user, require_role
from app.utils.audit import write_audit

router = APIRouter(prefix="/api/v1", tags=["文档资产"])
settings = get_settings()

MAX_ASSET_BYTES = 20 * 1024 * 1024
ALLOWED_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp",
    ".mp4", ".webm", ".mov",
    ".pdf", ".zip", ".txt", ".csv", ".xlsx", ".docx", ".pptx",
}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov"}


def _safe_filename(name: str) -> str:
    base = Path(name or "asset").name
    base = re.sub(r"[^a-zA-Z0-9._\-\u4e00-\u9fff]+", "-", base).strip(".-")
    return base or "asset"


def _asset_kind(ext: str, content_type: str) -> AssetKind:
    if ext in IMAGE_EXTENSIONS or content_type.startswith("image/"):
        return AssetKind.image
    if ext in VIDEO_EXTENSIONS or content_type.startswith("video/"):
        return AssetKind.video
    return AssetKind.file


def _asset_out(asset: DocumentAsset) -> AssetOut:
    file_url = f"/api/v1/assets/{asset.id}/file"
    if asset.kind == AssetKind.image:
        markdown = f"![{asset.original_filename}]({file_url})"
    else:
        markdown = f"[{asset.original_filename}]({file_url})"
    return AssetOut(
        id=asset.id,
        version_id=asset.version_id,
        original_filename=asset.original_filename,
        stored_filename=asset.stored_filename,
        content_type=asset.content_type,
        size_bytes=asset.size_bytes,
        kind=asset.kind.value,
        public_path=asset.public_path,
        file_url=file_url,
        markdown=markdown,
        created_at=asset.created_at,
    )


@router.get("/versions/{vid}/assets", response_model=ApiResponse)
async def list_assets(
    vid: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """列出版本资产库。"""
    version = (await db.execute(select(Version.id).where(Version.id == vid))).scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=404, detail="版本不存在")
    result = await db.execute(
        select(DocumentAsset)
        .where(DocumentAsset.version_id == vid)
        .order_by(DocumentAsset.created_at.desc())
    )
    return ApiResponse(data=[_asset_out(a).model_dump() for a in result.scalars().all()])


@router.post("/versions/{vid}/assets", response_model=ApiResponse, status_code=201)
async def upload_asset(
    vid: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "editor")),
):
    """上传图片、视频或附件到版本资产库。"""
    version = (await db.execute(select(Version.id).where(Version.id == vid))).scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=404, detail="版本不存在")

    original_filename = _safe_filename(file.filename or "asset")
    ext = Path(original_filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型: {ext or '无扩展名'}")

    content = await file.read(MAX_ASSET_BYTES + 1)
    if len(content) > MAX_ASSET_BYTES:
        raise HTTPException(status_code=400, detail="文件超过 20MB 限制")
    if not content:
        raise HTTPException(status_code=400, detail="文件为空")

    asset_id = str(uuid.uuid4())
    content_type = file.content_type or mimetypes.guess_type(original_filename)[0] or "application/octet-stream"
    kind = _asset_kind(ext, content_type)
    stored_filename = f"{asset_id}{ext}"
    storage_rel = os.path.join("assets", vid, stored_filename)
    storage_abs = os.path.join(settings.data_dir, storage_rel)
    os.makedirs(os.path.dirname(storage_abs), exist_ok=True)
    with open(storage_abs, "wb") as f:
        f.write(content)

    asset = DocumentAsset(
        id=asset_id,
        version_id=vid,
        original_filename=original_filename,
        stored_filename=stored_filename,
        content_type=content_type,
        size_bytes=len(content),
        kind=kind,
        storage_path=storage_rel,
        public_path=f"assets/{stored_filename}",
        uploaded_by=current_user.id,
    )
    db.add(asset)
    await db.commit()
    await db.refresh(asset)
    await write_audit(
        actor=current_user,
        action="asset.upload",
        target_type="asset",
        target_id=asset.id,
        payload={
            "version_id": vid,
            "filename": asset.original_filename,
            "kind": asset.kind.value,
            "size_bytes": asset.size_bytes,
        },
    )
    return ApiResponse(data=_asset_out(asset).model_dump())


@router.get("/assets/{aid}/file")
async def get_asset_file(
    aid: str,
    db: AsyncSession = Depends(get_db),
):
    """读取资产文件。UUID 地址用于编辑器预览和静态站构建前引用。"""
    asset = (await db.execute(select(DocumentAsset).where(DocumentAsset.id == aid))).scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="资产不存在")
    storage_abs = os.path.join(settings.data_dir, asset.storage_path)
    if not os.path.exists(storage_abs):
        raise HTTPException(status_code=404, detail="资产文件不存在")
    return FileResponse(
        storage_abs,
        media_type=asset.content_type,
        filename=asset.original_filename,
    )


@router.delete("/assets/{aid}", status_code=204)
async def delete_asset(
    aid: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "editor")),
):
    """删除资产记录和本地文件。已插入文档的引用不会自动清理。"""
    asset = (await db.execute(select(DocumentAsset).where(DocumentAsset.id == aid))).scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="资产不存在")
    snapshot = {
        "version_id": asset.version_id,
        "filename": asset.original_filename,
        "storage_path": asset.storage_path,
    }
    storage_abs = os.path.join(settings.data_dir, asset.storage_path)
    await db.delete(asset)
    await db.commit()
    if os.path.exists(storage_abs):
        try:
            os.remove(storage_abs)
        except OSError:
            pass
    await write_audit(
        actor=current_user,
        action="asset.delete",
        target_type="asset",
        target_id=aid,
        payload=snapshot,
    )
