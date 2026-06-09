"""构建部署路由"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import BuildLog, User
from app.schemas import BuildOut, ApiResponse
from app.utils.auth import get_current_user, require_role
from app.services.build_service import build_docusaurus
from app.config import get_settings

router = APIRouter(prefix="/api/v1/build", tags=["构建部署"])

settings = get_settings()


@router.post("/{vid}", response_model=ApiResponse)
async def trigger_build(
    vid: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "editor")),
):
    """触发文档构建"""
    # 获取版本信息
    from app.models import Version
    version = (await db.execute(select(Version).where(Version.id == vid))).scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=404, detail="版本不存在")

    build = await build_docusaurus(
        db=db,
        project_id=version.project_id,
        version_id=vid,
        triggered_by=current_user.id,
    )
    return ApiResponse(data=BuildOut.model_validate(build))


@router.get("/{bid}/status", response_model=ApiResponse)
async def get_build_status(
    bid: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """查询构建状态"""
    result = await db.execute(select(BuildLog).where(BuildLog.id == bid))
    build = result.scalar_one_or_none()
    if not build:
        raise HTTPException(status_code=404, detail="构建记录不存在")
    return ApiResponse(data=BuildOut.model_validate(build))


@router.get("/logs", response_model=ApiResponse)
async def list_build_logs(
    project_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取构建日志列表"""
    query = select(BuildLog).order_by(BuildLog.created_at.desc()).limit(50)
    if project_id:
        query = query.where(BuildLog.project_id == project_id)
    result = await db.execute(query)
    logs = result.scalars().all()
    return ApiResponse(data=[BuildOut.model_validate(b) for b in logs])


@router.get("/latest", response_model=ApiResponse)
async def get_latest_build(
    project_id: str = Query(..., description="项目 ID"),
    version_id: Optional[str] = Query(None, description="版本 ID（可选，不传则取该项目的最新一次）"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取某项目/版本的最新一次构建

    返回包含可直接访问的 `url` 字段（基于 project slug + version）。
    """
    from app.models import Project, Version
    # 验证项目存在 + 拿 slug
    proj = (await db.execute(select(Project).where(Project.id == project_id))).scalar_one_or_none()
    if not proj:
        raise HTTPException(status_code=404, detail="项目不存在")

    q = select(BuildLog).where(BuildLog.project_id == project_id)
    if version_id:
        q = q.where(BuildLog.version_id == version_id)
    q = q.order_by(desc(BuildLog.created_at)).limit(1)
    build = (await db.execute(q)).scalar_one_or_none()

    if not build:
        return ApiResponse(data=None, meta={"has_build": False, "project_slug": proj.slug})

    # 查 version 拼 URL
    ver = (await db.execute(select(Version).where(Version.id == build.version_id))).scalar_one_or_none()
    version_str = ver.version if ver else "unknown"
    url = f"/docs/{proj.slug}/{version_str}/{slugify_index(proj.slug, version_str)}"

    out = BuildOut.model_validate(build).model_dump()
    out["url"] = url
    out["project_slug"] = proj.slug
    out["version"] = version_str
    return ApiResponse(data=out, meta={"has_build": True})


@router.get("/manifest", response_model=ApiResponse)
async def get_build_manifest(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """已发布站点清单 — 给前端 /published 页用

    对每个 (project_id, version_id) 取最新一次 successful 构建，附带 URL。
    顺便从文件系统读出 doc_count（每版本目录下的 .html 文件数）。
    created_at 强制带 Z 后缀（UTC），避免前端 JS 解析时区错乱。
    """
    import os
    from datetime import timezone
    from app.models import Project, Version
    rows = (await db.execute(
        select(BuildLog)
        .where(BuildLog.status == "success")
        .order_by(desc(BuildLog.created_at))
        .limit(200)
    )).scalars().all()

    # 去重：(project_id, version_id) 只留最新
    seen: set[tuple[str, str]] = set()
    manifest: list[dict] = []
    for b in rows:
        key = (b.project_id, b.version_id)
        if key in seen:
            continue
        seen.add(key)
        proj = (await db.execute(select(Project).where(Project.id == b.project_id))).scalar_one_or_none()
        ver = (await db.execute(select(Version).where(Version.id == b.version_id))).scalar_one_or_none()
        if not proj or not ver:
            continue
        # 数 doc_count：从 data/builds/{slug}/{ver} 数 .html
        build_dir = os.path.join(settings.data_dir, "builds", proj.slug, ver.version)
        doc_count = 0
        if os.path.isdir(build_dir):
            doc_count = sum(1 for fn in os.listdir(build_dir) if fn.endswith(".html"))
        # 强制转 UTC + Z 后缀（关键：避免前端 JS 把 naive datetime 解析错位）
        built_at = b.created_at
        if built_at.tzinfo is None:
            built_at = built_at.replace(tzinfo=timezone.utc)
        built_at_iso = built_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        manifest.append({
            "project_id": b.project_id,
            "project_name": proj.name,
            "project_slug": proj.slug,
            "brand_color": proj.brand_color,
            "version_id": b.version_id,
            "version": ver.version,
            "build_id": b.id,
            "built_at": built_at_iso,
            "duration": b.duration,
            "doc_count": doc_count,
            "url": f"/docs/{proj.slug}/{ver.version}/index.html",
        })

    return ApiResponse(data=manifest, meta={"count": len(manifest)})


def slugify_index(slug: str, version: str) -> str:
    """构造 index URL 的辅助函数"""
    return "index.html"
