"""反馈 / 评论区路由 — 公开 API,无需登录,访客用 visitor_id 区分

设计:
- POST /api/v1/feedbacks              创建反馈 (like/dislike/bookmark/comment)
- GET  /api/v1/feedbacks/{doc_id}/reactions   统计 + 当前访客反应
- GET  /api/v1/feedbacks/{doc_id}/comments    评论列表 (含嵌套回复)
- DELETE /api/v1/feedbacks/{id}       删除自己 (按 visitor_id 校验) 的反馈
- GET  /api/v1/feedbacks/admin/list   admin 审核: 全量评论 (任意 doc)
- DELETE /api/v1/feedbacks/admin/{id} admin 审核: 任意删 (绕开 visitor_id 校验)
"""
import uuid
from datetime import timezone
from fastapi import APIRouter, Depends, HTTPException, Header, Query
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import DocumentFeedback, FeedbackKind, Document, User
from app.schemas import (
    FeedbackCreate, FeedbackReactionOut, CommentsListOut, CommentOut, ApiResponse
)
from app.utils.audit import write_audit
from app.utils.auth import get_current_user
from app.utils.anti_spam import (
    validate_comment_body,
    check_nesting_depth_async,
    get_visitor_limiter,
)

router = APIRouter(prefix="/api/v1/feedbacks", tags=["读者反馈"])


async def _get_visitor_id(
    x_visitor_id: str = Header(..., alias="X-Visitor-Id", description="前端 localStorage 中持久化的访客 uuid")
) -> str:
    if not x_visitor_id or len(x_visitor_id) > 64:
        raise HTTPException(status_code=400, detail="visitor_id 必填,长度 1-64")
    return x_visitor_id


def _to_comment_out(row: DocumentFeedback, replies: list[DocumentFeedback]) -> CommentOut:
    return CommentOut(
        id=row.id,
        document_id=row.document_id,
        parent_id=row.parent_id,
        user_id=row.user_id,
        user_name=row.user_name or "匿名读者",
        body=row.body,
        # Postgres `now()` 返 timestamptz (UTC), asyncpg 读出丢 tzinfo 变 naive.
        # 显式 attach UTC tzinfo, Pydantic dump 时输出 '...+00:00' 格式,
        # 浏览器按 UTC 解读后再 convert 到 local 渲染 (与服务器 0 偏差)
        created_at=_attach_utc(row.created_at),
        replies=[_to_comment_out(r, []) for r in replies],
    )


def _attach_utc(dt):
    """naive datetime → 加 UTC tzinfo. Pydantic 序列化时自动 append +00:00.

    Postgres `now()` 返回 timestamptz (UTC), asyncpg 读出丢 tzinfo 变 naive.
    前端 new Date() 默认按 local tz 解析, 与服务器差 8h.
    修法: 显式 attach UTC tzinfo, Pydantic dump 时输出 '...+00:00' 格式,
    浏览器按 UTC 解读后再 convert 到 local 渲染.

    历史: 早版叫 _attach_cst, 名实不符 (实则加 UTC, 不是 CST) 误导开发者.
          v0.1.10 rename 为 _attach_utc.
    """
    if dt is None or dt.tzinfo is not None:
        return dt
    return dt.replace(tzinfo=timezone.utc)


@router.post("", response_model=ApiResponse)
async def create_feedback(
    payload: FeedbackCreate,
    visitor_id: str = Depends(_get_visitor_id),
    db: AsyncSession = Depends(get_db),
):
    """创建反馈

    - like/dislike/bookmark: 同 (document, visitor, kind) 只能存在一行, 重复提交 = noop
    - comment: 必须带 body, 可选 parent_id
    """
    try:
        kind_enum = FeedbackKind(payload.kind)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"kind 必须是 like/dislike/bookmark/comment, 收到: {payload.kind}")

    if kind_enum == FeedbackKind.comment:
        if not payload.body or not payload.body.strip():
            raise HTTPException(status_code=400, detail="评论 body 必填")
        # F2: 4 件套校验 (长度 + 关键词 + 链接数)
        ok, reason = validate_comment_body(payload.body)
        if not ok:
            raise HTTPException(status_code=400, detail=reason)
        # F2: 嵌套深度 ≤ 2 层
        ok, reason = await check_nesting_depth_async(db, payload.parent_id)
        if not ok:
            raise HTTPException(status_code=400, detail=reason)

    # F2: 访客级限流 (comment 5/min, reaction 30/min)
    limiter = get_visitor_limiter()
    if kind_enum == FeedbackKind.comment:
        if not limiter.check(visitor_id, "comment", max_count=5, window_seconds=60):
            raise HTTPException(status_code=429, detail="评论过于频繁 (5 条/分钟), 请稍后再试")
    else:
        if not limiter.check(visitor_id, "reaction", max_count=30, window_seconds=60):
            raise HTTPException(status_code=429, detail="操作过于频繁 (30 次/分钟), 请稍后再试")

    # 验证 doc/version 存在
    doc = (await db.execute(select(Document).where(Document.id == payload.document_id))).scalar_one_or_none()
    if not doc or doc.version_id != payload.version_id:
        raise HTTPException(status_code=404, detail="文档或版本不存在")

    if kind_enum != FeedbackKind.comment:
        # 反应类: upsert 语义 — 同 (doc, visitor, kind) 已存在则返回
        existing = (await db.execute(
            select(DocumentFeedback).where(
                DocumentFeedback.document_id == payload.document_id,
                DocumentFeedback.visitor_id == visitor_id,
                DocumentFeedback.kind == kind_enum,
            )
        )).scalar_one_or_none()
        if existing:
            return ApiResponse(data={"id": existing.id, "noop": True})

    # 如果切换反应 (从 like 改 dislike), 不在这里处理, 简化: 让前端先 DELETE 再 POST
    fb = DocumentFeedback(
        id=str(uuid.uuid4()),
        document_id=payload.document_id,
        version_id=payload.version_id,
        kind=kind_enum,
        visitor_id=visitor_id,
        user_name=(payload.user_name or "匿名读者")[:100],
        body=payload.body.strip() if payload.body else None,
        parent_id=payload.parent_id,
    )
    db.add(fb)
    await db.commit()
    await db.refresh(fb)
    await write_audit(actor=None, action="feedback.create",
                      target_type="document", target_id=str(fb.document_id),
                      actor_email=f"visitor:{visitor_id[:12]}",
                      payload={"kind": fb.kind.value, "has_body": bool(fb.body),
                               "parent_id": fb.parent_id,
                               "user_name": fb.user_name})
    return ApiResponse(data={"id": fb.id, "noop": False, "created_at": fb.created_at.isoformat()})


@router.get("/{doc_id}/reactions", response_model=ApiResponse)
async def get_reactions(
    doc_id: str,
    visitor_id: str = Depends(_get_visitor_id),
    db: AsyncSession = Depends(get_db),
):
    """获取某 doc 的反应统计 + 当前访客的反应"""
    # 三种 kind 的 count
    counts = {}
    for k in [FeedbackKind.like, FeedbackKind.dislike, FeedbackKind.bookmark]:
        c = (await db.execute(
            select(func.count(DocumentFeedback.id))
            .where(
                DocumentFeedback.document_id == doc_id,
                DocumentFeedback.kind == k,
            )
        )).scalar() or 0
        counts[k.value] = c

    # 当前访客的反应 (kind + id 都查, id 用于 toggle DELETE)
    my_rows = (await db.execute(
        select(DocumentFeedback.id, DocumentFeedback.kind)
        .where(
            DocumentFeedback.document_id == doc_id,
            DocumentFeedback.visitor_id == visitor_id,
            DocumentFeedback.kind.in_([FeedbackKind.like, FeedbackKind.dislike, FeedbackKind.bookmark]),
        )
    )).all()

    return ApiResponse(data=FeedbackReactionOut(
        like_count=counts["like"],
        dislike_count=counts["dislike"],
        bookmark_count=counts["bookmark"],
        my_reaction=my_rows[0].kind.value if my_rows else None,
        my_reaction_id=my_rows[0].id if my_rows else None,
    ).model_dump())


@router.get("/{doc_id}/comments", response_model=ApiResponse)
async def get_comments(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
):
    """获取某 doc 的评论列表 (顶级 + 嵌套回复)"""
    # 拉所有评论 (扁平), 在内存里构树
    rows = (await db.execute(
        select(DocumentFeedback)
        .where(
            DocumentFeedback.document_id == doc_id,
            DocumentFeedback.kind == FeedbackKind.comment,
        )
        .order_by(DocumentFeedback.created_at.asc())
        .limit(limit * 4)  # 多拉一些, 留点余量给回复
    )).scalars().all()

    by_parent: dict[str | None, list[DocumentFeedback]] = {}
    for r in rows:
        by_parent.setdefault(r.parent_id, []).append(r)

    def build(parent_id: str | None) -> list[CommentOut]:
        out = []
        for r in by_parent.get(parent_id, [])[:limit]:
            out.append(_to_comment_out(r, build(r.id)))
        return out

    top_level = build(None)
    return ApiResponse(data=CommentsListOut(items=top_level, total=len(rows)).model_dump())


@router.delete("/{feedback_id}", response_model=ApiResponse)
async def delete_feedback(
    feedback_id: str,
    visitor_id: str = Depends(_get_visitor_id),
    db: AsyncSession = Depends(get_db),
):
    """删除自己 (按 visitor_id 校验) 的反馈"""
    fb = (await db.execute(
        select(DocumentFeedback).where(DocumentFeedback.id == feedback_id)
    )).scalar_one_or_none()
    if not fb:
        raise HTTPException(status_code=404, detail="反馈不存在")
    if fb.visitor_id != visitor_id:
        raise HTTPException(status_code=403, detail="只能删除自己提交的反馈")
    await db.delete(fb)
    await db.commit()
    await write_audit(actor=None, action="feedback.delete",
                      target_type="feedback", target_id=feedback_id,
                      actor_email=f"visitor:{visitor_id[:12]}",
                      payload={"kind": fb.kind.value, "had_body": bool(fb.body)})
    return ApiResponse(data={"deleted": feedback_id})


@router.get("/admin/list", response_model=ApiResponse)
async def admin_list_feedbacks(
    kind: str = Query(None, description="按 kind 过滤: like/dislike/bookmark/comment"),
    document_id: str = Query(None, description="按 document 过滤"),
    user_email: str = Query(None, description="按 visitor_id/user_name 模糊搜索"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """admin 审核: 全量反馈列表 + 多维过滤

    公开评论审核 — admin/editor 角色可访问
    """
    if current_user.role not in ("admin", "editor"):
        raise HTTPException(status_code=403, detail="需要 admin/editor 角色")
    q = select(DocumentFeedback)
    if kind:
        try:
            q = q.where(DocumentFeedback.kind == FeedbackKind(kind))
        except ValueError:
            raise HTTPException(status_code=400, detail="kind 必须是 like/dislike/bookmark/comment")
    if document_id:
        q = q.where(DocumentFeedback.document_id == document_id)
    if user_email:
        # 模糊搜 visitor_id / user_name
        q = q.where(or_(
            DocumentFeedback.visitor_id.ilike(f"%{user_email}%"),
            DocumentFeedback.user_name.ilike(f"%{user_email}%"),
        ))
    # 拉总数
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar() or 0
    # 拉分页
    rows = (await db.execute(
        q.order_by(DocumentFeedback.created_at.desc()).offset(offset).limit(limit)
    )).scalars().all()
    return ApiResponse(data={
        "items": [{
            "id": r.id,
            "document_id": r.document_id,
            "version_id": r.version_id,
            "kind": r.kind.value,
            "visitor_id": r.visitor_id[:16] + "..." if len(r.visitor_id) > 16 else r.visitor_id,
            "user_id": r.user_id,
            "user_name": r.user_name,
            "body": r.body,
            "parent_id": r.parent_id,
            "created_at": _attach_utc(r.created_at).isoformat() if r.created_at else None,
        } for r in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    })


@router.delete("/admin/{feedback_id}", response_model=ApiResponse)
async def admin_delete_feedback(
    feedback_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """admin 审核: 任意删 (绕开 visitor_id 校验)"""
    if current_user.role not in ("admin", "editor"):
        raise HTTPException(status_code=403, detail="需要 admin/editor 角色")
    fb = (await db.execute(
        select(DocumentFeedback).where(DocumentFeedback.id == feedback_id)
    )).scalar_one_or_none()
    if not fb:
        raise HTTPException(status_code=404, detail="反馈不存在")
    await db.delete(fb)
    await db.commit()
    await write_audit(actor=current_user, action="feedback.admin_delete",
                      target_type="feedback", target_id=feedback_id,
                      actor_email=current_user.email,
                      payload={"kind": fb.kind.value, "had_body": bool(fb.body),
                               "original_visitor": fb.visitor_id[:16]})
    return ApiResponse(data={"deleted": feedback_id, "by_admin": current_user.email})
