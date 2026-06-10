"""文档管理路由（含版本管理）"""
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
import re
import yaml
from app.database import get_db
from app.models import Project, Version, Document, User, VersionStatus, DocStatus
from pydantic import BaseModel
from app.schemas import (
    VersionCreate, VersionOut,
    DocumentCreate, DocumentUpdate, DocumentOut, DocumentTreeOut,
    ApiResponse, ReorderRequest,
)
from app.utils.auth import get_current_user, require_role
from app.utils.audit import write_audit

router = APIRouter(prefix="/api/v1", tags=["文档管理"])


# ── 版本管理 ──────────────────────────────────────────

@router.get("/projects/{pid}/versions", response_model=ApiResponse)
async def list_versions(
    pid: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Version).where(Version.project_id == pid).order_by(Version.created_at.desc())
    )
    versions = result.scalars().all()
    return ApiResponse(data=[VersionOut.model_validate(v) for v in versions])


@router.post("/projects/{pid}/versions", response_model=ApiResponse, status_code=201)
async def create_version(
    pid: str,
    req: VersionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "editor")),
):
    # 验证项目存在
    project = await db.execute(select(Project).where(Project.id == pid))
    if not project.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="项目不存在")

    version = Version(
        project_id=pid,
        version=req.version,
        is_default=req.is_default,
    )
    db.add(version)
    await db.commit()
    await db.refresh(version)
    await write_audit(actor=current_user, action="version.create",
                      target_type="version", target_id=version.id,
                      payload={"project_id": pid, "version": version.version,
                               "is_default": version.is_default})
    return ApiResponse(data=VersionOut.model_validate(version))


# R6 反馈 2: 版本管理 — 归档 / 设为默认
@router.put("/versions/{vid}/archive", response_model=ApiResponse)
async def archive_version(
    vid: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "editor")),
):
    """归档版本 (软删除, status=archived, is_default=false)"""
    r = await db.execute(select(Version).where(Version.id == vid))
    v = r.scalar_one_or_none()
    if not v:
        raise HTTPException(status_code=404, detail="版本不存在")
    if v.is_default:
        raise HTTPException(status_code=400, detail="默认版本不能归档")
    v.status = VersionStatus.archived
    v.is_default = False
    await db.commit()
    await db.refresh(v)
    await write_audit(actor=current_user, action="version.archive",
                      target_type="version", target_id=v.id,
                      payload={"version": v.version, "project_id": v.project_id})
    return ApiResponse(data=VersionOut.model_validate(v))


@router.put("/versions/{vid}/default", response_model=ApiResponse)
async def set_default_version(
    vid: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "editor")),
):
    """设为项目默认版本 (同时清掉同项目其他默认)"""
    r = await db.execute(select(Version).where(Version.id == vid))
    v = r.scalar_one_or_none()
    if not v:
        raise HTTPException(status_code=404, detail="版本不存在")
    # 取消同项目其他默认
    others = await db.execute(
        select(Version).where(
            Version.project_id == v.project_id,
            Version.id != vid,
            Version.is_default.is_(True),
        )
    )
    for o in others.scalars().all():
        o.is_default = False
    v.is_default = True
    await db.commit()
    await db.refresh(v)
    await write_audit(actor=current_user, action="version.set_default",
                      target_type="version", target_id=v.id,
                      payload={"version": v.version, "project_id": v.project_id})
    return ApiResponse(data=VersionOut.model_validate(v))


# ── 文档 CRUD ─────────────────────────────────────────

@router.get("/versions/{vid}/documents", response_model=ApiResponse)
async def list_documents(
    vid: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取版本下的文档树"""
    result = await db.execute(
        select(Document)
        .where(Document.version_id == vid)
        .order_by(Document.sort_order, Document.created_at)
    )
    docs = result.scalars().all()

    # 构建树形结构
    # is_folder 计算规则: 节点 content 为空字符串/None 且 后续会被挂子节点 → folder
    # 先一次性构建 id->children 计数 + content 是否空, 第二次遍历判定
    children_count: dict[str, int] = {}
    for d in docs:
        if d.parent_id:
            children_count[d.parent_id] = children_count.get(d.parent_id, 0) + 1
    def _is_folder(d) -> bool:
        # 约定: content 为空 (None / '' / 仅空白) → folder-only
        c = d.content
        return (not c) or (isinstance(c, str) and c.strip() == '')

    doc_map: dict[str, DocumentTreeOut] = {}
    for d in docs:
        c = d.content or ""
        content_len = len(c)
        node = DocumentTreeOut(
            id=d.id, title=d.title, slug=d.slug,
            status=d.status.value, sort_order=d.sort_order,
            is_folder=_is_folder(d) or children_count.get(d.id, 0) > 0,
            content_len=content_len,
            has_content=content_len > 0,
            children=[],
        )
        doc_map[d.id] = node
    roots: list[DocumentTreeOut] = []
    for d in docs:
        node = doc_map[d.id]
        if d.parent_id and d.parent_id in doc_map:
            doc_map[d.parent_id].children.append(node)
        else:
            roots.append(node)

    return ApiResponse(data=[r.model_dump() for r in roots])


@router.post("/versions/{vid}/documents", response_model=ApiResponse, status_code=201)
async def create_document(
    vid: str,
    req: DocumentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "editor")),
):
    """创建文档"""
    # 验证版本存在
    version = await db.execute(select(Version).where(Version.id == vid))
    if not version.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="版本不存在")

    # 验证 slug 在同 version 唯一 (避免 DB IntegrityError 暴露为 500)
    slug_dup = await db.execute(
        select(Document.id).where(
            Document.version_id == vid,
            Document.slug == req.slug,
        )
    )
    if slug_dup.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail=f"URL 标识「{req.slug}」已被使用, 请换一个",
        )

    doc = Document(
        version_id=vid,
        title=req.title,
        slug=req.slug,
        content=req.content,
        parent_id=req.parent_id,
        sort_order=req.sort_order,
        created_by=current_user.id,
    )
    try:
        db.add(doc)
        await db.commit()
        await db.refresh(doc)
    except IntegrityError as e:
        await db.rollback()
        # 并发场景: 另一请求刚刚插入了同 slug
        if "documents" in str(e.orig).lower() and ("slug" in str(e.orig).lower() or "unique" in str(e.orig).lower()):
            raise HTTPException(
                status_code=400,
                detail=f"URL 标识「{req.slug}」已被使用, 请换一个",
            )
        raise HTTPException(status_code=400, detail=f"数据库约束冲突: {e.orig}")
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"创建文档失败: {type(e).__name__}: {e}")

    await write_audit(actor=current_user, action="document.create",
                      target_type="document", target_id=doc.id,
                      payload={"title": doc.title, "slug": doc.slug,
                               "version_id": str(doc.version_id),
                               "status": doc.status})
    return ApiResponse(data=DocumentOut.model_validate(doc))


@router.get("/documents/{did}", response_model=ApiResponse)
async def get_document(
    did: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取文档详情"""
    result = await db.execute(select(Document).where(Document.id == did))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    return ApiResponse(data=DocumentOut.model_validate(doc))


@router.put("/documents/{did}", response_model=ApiResponse)
async def update_document(
    did: str,
    req: DocumentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "editor")),
):
    """更新文档"""
    result = await db.execute(select(Document).where(Document.id == did))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    update_data = req.model_dump(exclude_unset=True)
    base_revision = update_data.pop("base_revision", None)
    if "content" in update_data and base_revision is not None and doc.revision != base_revision:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "document_conflict",
                "message": "文档已被其他人保存, 请对比差异后合并",
                "document_id": doc.id,
                "base_revision": base_revision,
                "latest_revision": doc.revision,
                "latest_content": doc.content or "",
                "draft_content": update_data.get("content") or "",
                "latest_updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
            },
        )
    before = {k: getattr(doc, k) for k in update_data.keys() if k != "content"}
    for key, value in update_data.items():
        setattr(doc, key, value)
    if update_data:
        doc.revision = (doc.revision or 1) + 1

    await db.commit()
    await db.refresh(doc)
    after = {k: getattr(doc, k) for k in update_data.keys() if k != "content"}
    await write_audit(actor=current_user, action="document.update",
                      target_type="document", target_id=doc.id,
                      payload={"title": doc.title, "slug": doc.slug,
                               "status": doc.status,
                               "changed_fields": list(update_data.keys()),
                               "diff": [
                                   {"field": k, "before": before.get(k), "after": after.get(k)}
                                   for k in update_data.keys() if k != "content"
                               ]})
    return ApiResponse(data=DocumentOut.model_validate(doc))


@router.delete("/documents/{did}", status_code=204)
async def delete_document(
    did: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "editor")),
):
    """删除文档"""
    result = await db.execute(select(Document).where(Document.id == did))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    snapshot = {"title": doc.title, "slug": doc.slug, "id": str(doc.id),
                "version_id": str(doc.version_id)}
    await db.delete(doc)
    await db.commit()
    await write_audit(actor=current_user, action="document.delete",
                      target_type="document", target_id=snapshot["id"],
                      payload=snapshot)


# ── 批量发布 (R15 预构建弹窗用) ─────────────────────────────
class BatchPublishRequest(BaseModel):
    """批量发布请求
    - ids: 必填, 至少 1 个 doc id
    - skip_empty: True 时跳过 content 为空的 doc (folder-only 节点不该发布)
    """
    ids: list[str]
    skip_empty: bool = True


@router.post("/documents/batch-publish", response_model=ApiResponse)
async def batch_publish_documents(
    req: BatchPublishRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "editor")),
):
    """批量发布 — R15 预构建弹窗的核心

    行为:
    - 验证 ids 非空
    - 逐个查 doc, 不存在 / 跨 version 的不报 500, 而是记到 errors
    - skip_empty=True 时跳过 content 为空的 (folder-only 节点)
    - status 已经是 published 的也算成功 (幂等)
    - 一次 commit 所有更新 (事务)

    返回:
    - published: 成功发布的 id 列表
    - skipped: 跳过的 (空内容 / 已 published / 跨 version)
    - errors: 出错的 id + message
    """
    if not req.ids:
        raise HTTPException(status_code=400, detail="ids 不能为空")

    result = await db.execute(
        select(Document).where(Document.id.in_(req.ids))
    )
    docs = {d.id: d for d in result.scalars().all()}

    published: list[str] = []
    skipped: list[dict] = []
    errors: list[dict] = []

    for did in req.ids:
        doc = docs.get(did)
        if not doc:
            errors.append({"id": did, "message": "文档不存在"})
            continue
        # 幂等: 已经是 published 的算 skipped
        if doc.status.value == "published":
            skipped.append({"id": did, "reason": "已是 published"})
            continue
        # skip_empty: content 为空 (folder) 不发布
        if req.skip_empty:
            c = doc.content
            if not c or (isinstance(c, str) and c.strip() == ""):
                skipped.append({"id": did, "reason": "内容为空 (folder)"})
                continue
        doc.status = DocStatus.published
        published.append(did)

    if published:
        await db.commit()
        # 审计: 一次操作
        await write_audit(
            actor=current_user, action="document.batch_publish",
            target_type="document", target_id=None,
            payload={"count": len(published), "ids": published,
                     "skipped": len(skipped), "errors": len(errors)}
        )

    return ApiResponse(data={
        "published": published,
        "skipped": skipped,
        "errors": errors,
    })


# ── 拖拽排序 (R6 反馈 5) ────────────────────────────────

@router.post("/documents/reorder", response_model=ApiResponse)
async def reorder_documents(
    req: ReorderRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "editor")),
):
    """批量重排文档的 parent_id / sort_order。

    客户端把整棵树拖拽后的新位置打平 (id, parent_id, sort_order) 发上来。
    服务端用单事务批量更新, 减少抖动。循环检测: parent_id 不能引用自己或后代。
    """
    # 一次性把所有 doc 拿出来
    result = await db.execute(
        select(Document).where(Document.version_id == req.version_id)
    )
    all_docs = {d.id: d for d in result.scalars().all()}

    # 校验: 所有 id 必须存在且属于该 version
    for item in req.items:
        if item.id not in all_docs:
            raise HTTPException(status_code=400, detail=f"文档不存在: {item.id}")
        if item.parent_id and item.parent_id not in all_docs:
            raise HTTPException(status_code=400, detail=f"parent 不存在: {item.parent_id}")

    # 循环检测: 父链不能回到自己 (DFS)
    def has_cycle(start_id: str, target_parent: str | None) -> bool:
        if not target_parent:
            return False
        seen: set[str] = set()
        cur = target_parent
        while cur:
            if cur == start_id:
                return True
            if cur in seen:
                return True
            seen.add(cur)
            cur = all_docs[cur].parent_id
        return False

    for item in req.items:
        if has_cycle(item.id, item.parent_id):
            raise HTTPException(
                status_code=400,
                detail=f"parent 链循环: {item.id} → {item.parent_id}"
            )
        all_docs[item.id].parent_id = item.parent_id
        all_docs[item.id].sort_order = item.sort_order

    await db.commit()
    return ApiResponse(data={"updated": len(req.items)})


# ── 批量导入（本地 Markdown 上传）──────────────────────────

FRONTMATTER_RE = re.compile(r"\A\s*---\s*\n(.*?)\n---\s*\n?", re.DOTALL)


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """解析 ---\\nkey: val\\n---\\n 格式的 frontmatter。
    返回 (meta_dict, 剩余内容)。无 frontmatter 返回 ({}, 原文)。"""
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    raw = m.group(1)
    rest = text[m.end():]
    try:
        meta = yaml.safe_load(raw) or {}
        if not isinstance(meta, dict):
            meta = {}
    except yaml.YAMLError:
        meta = {}
    return meta, rest


def _slugify(name: str) -> str:
    """文件名 → slug：小写、非字母数字转 -、去首尾 -。"""
    s = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]+", "-", name.lower())
    s = re.sub(r"-+", "-", s).strip("-")
    return s or "doc"


async def _unique_slug(db: AsyncSession, version_id: str, base: str) -> str:
    """slug 在 version 内唯一，冲突追加 -2, -3..."""
    slug = base
    n = 2
    while True:
        r = await db.execute(
            select(Document.id).where(Document.version_id == version_id, Document.slug == slug)
        )
        if not r.scalar_one_or_none():
            return slug
        slug = f"{base}-{n}"
        n += 1


@router.post("/versions/{vid}/documents/import", response_model=ApiResponse, status_code=201)
async def import_markdown(
    vid: str,
    files: list[UploadFile] = File(..., description="多个 .md 文件"),
    # R7 反馈: import 端点默认 status=draft, 上游 (脚本/AI agent) 看不到就不知所措
    # 新增 2 选 1: ?publish=true 一律发布, ?auto_publish=true 按 frontmatter published 字段决定
    publish: bool = Query(False, description="强制设 status=published"),
    auto_publish: bool = Query(False, description="读 frontmatter published 字段 (true/false) 决定"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "editor")),
):
    """批量导入本地 Markdown — 解析 frontmatter，自动 slug、冲突重命名。

    成功导入返回 {data: {imported: [{id, title, slug, status}], errors: [{filename, message}]}}
    """
    # 验证版本
    r = await db.execute(select(Version).where(Version.id == vid))
    if not r.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="版本不存在")

    imported: list[dict] = []
    errors: list[dict] = []
    for f in files:
        try:
            # 读内容（限制 1MB 防止滥用）
            content_bytes = await f.read(1024 * 1024 + 1)
            if len(content_bytes) > 1024 * 1024:
                raise ValueError("文件超过 1MB 限制")
            text = content_bytes.decode("utf-8", errors="replace")

            meta, body = _parse_frontmatter(text)
            # 标题：frontmatter title > 文件名（去后缀）
            raw_name = f.filename or "untitled.md"
            base_name = re.sub(r"\.md$", "", raw_name, flags=re.IGNORECASE)
            title = str(meta.get("title") or base_name).strip() or base_name
            # slug：frontmatter slug > 文件名 slugify
            base_slug = str(meta.get("slug") or _slugify(base_name)).strip() or _slugify(base_name)
            slug = await _unique_slug(db, vid, base_slug)
            # 排序：取 max + 1
            rmax = await db.execute(
                select(func.coalesce(func.max(Document.sort_order), 0))
                .where(Document.version_id == vid)
            )
            sort_order = (rmax.scalar() or 0) + 1 + len(imported)

            # R7 反馈: 决定 status (优先级: ?publish > ?auto_publish+frontmatter > draft)
            from app.models.document import DocStatus
            if publish:
                doc_status = DocStatus.published
            elif auto_publish and str(meta.get("published", "")).lower() in ("true", "1", "yes"):
                doc_status = DocStatus.published
            else:
                doc_status = DocStatus.draft

            doc = Document(
                version_id=vid,
                title=title[:500],
                slug=slug[:200],
                content=body,
                sort_order=sort_order,
                status=doc_status,
                created_by=current_user.id,
            )
            db.add(doc)
            await db.flush()  # 拿 id 但不入 commit（最后统一提交）
            imported.append({
                "id": doc.id,
                "title": doc.title,
                "slug": doc.slug,
                "status": doc.status.value,
                "content_len": len(body),
                "sort_order": doc.sort_order,
            })
        except Exception as e:
            errors.append({"filename": f.filename, "message": str(e)})

    if imported:
        await db.commit()
    return ApiResponse(data={"imported": imported, "errors": errors})
