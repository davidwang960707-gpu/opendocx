"""AI 语义搜索路由"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import Document, Version, Project, User, DocumentEmbedding
from app.schemas import SearchRequest, ApiResponse
from app.utils.auth import get_current_user
from app.services.embed_service import (
    get_embedding,
    embed_document,
    is_model_available,
)

router = APIRouter(prefix="/api/v1/search", tags=["AI 搜索"])


async def _vector_search(
    db: AsyncSession, query_text: str, project_id: str | None, limit: int
) -> list[dict]:
    """使用 pgvector 进行向量相似度搜索"""
    query_embedding = get_embedding(query_text)
    if not query_embedding:
        return []

    # pgvector cosine distance: 1 - cosine_similarity
    # 使用 raw SQL 计算 cosine similarity (1 - cosine_distance)
    cosine_sim = 1 - DocumentEmbedding.embedding.cosine_distance(query_embedding)

    query = (
        select(
            Document,
            Version.version.label("ver_slug"),
            Project.slug.label("proj_slug"),
            cosine_sim.label("score"),
        )
        .join(DocumentEmbedding, Document.id == DocumentEmbedding.document_id)
        .join(Version, Document.version_id == Version.id)
        .join(Project, Version.project_id == Project.id)
        .where(Document.status == "published")
        .order_by(cosine_sim.desc())
        .limit(limit)
    )

    if project_id:
        query = query.where(Version.project_id == project_id)

    result = await db.execute(query)
    rows = result.all()

    results = []
    for doc, ver_slug, proj_slug, score in rows:
        content_snippet = ""
        if doc.content:
            content_snippet = doc.content[:200] + "..." if len(doc.content) > 200 else doc.content

        results.append({
            "document_id": doc.id,
            "title": doc.title,
            "content_snippet": content_snippet,
            "score": round(float(score), 4),
            "project_slug": proj_slug,
            "version": ver_slug,
        })

    return results


async def _ilike_search(
    db: AsyncSession, query_text: str, project_id: str | None, limit: int
) -> list[dict]:
    """降级方案：使用 ILIKE 关键词搜索"""
    query = (
        select(Document, Version.version.label("ver_slug"), Project.slug.label("proj_slug"))
        .join(Version, Document.version_id == Version.id)
        .join(Project, Version.project_id == Project.id)
    )

    if project_id:
        query = query.where(Version.project_id == project_id)

    search_term = f"%{query_text}%"
    query = query.where(
        Document.content.ilike(search_term) | Document.title.ilike(search_term)
    ).limit(limit)

    result = await db.execute(query)
    rows = result.all()

    results = []
    for doc, ver_slug, proj_slug in rows:
        content_snippet = ""
        if doc.content:
            content_snippet = doc.content[:200] + "..." if len(doc.content) > 200 else doc.content

        results.append({
            "document_id": doc.id,
            "title": doc.title,
            "content_snippet": content_snippet,
            "score": 0.85,
            "project_slug": proj_slug,
            "version": ver_slug,
        })

    return results


@router.post("", response_model=ApiResponse)
async def semantic_search(
    req: SearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """语义搜索文档 — 优先使用向量搜索，模型不可用时降级到 ILIKE"""
    if is_model_available():
        results = await _vector_search(db, req.query, req.project_id, req.limit)
        if results:
            return ApiResponse(data=results, meta={"method": "vector"})

    # 降级到 ILIKE
    results = await _ilike_search(db, req.query, req.project_id, req.limit)
    return ApiResponse(data=results, meta={"method": "ilike"})


@router.post("/reindex", response_model=ApiResponse)
async def reindex_embeddings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """批量为所有已发布文档生成 embeddings"""
    if not is_model_available():
        raise HTTPException(
            status_code=503,
            detail="Embedding 模型不可用，无法执行 reindex",
        )

    # 查询所有已发布的文档
    result = await db.execute(
        select(Document).where(Document.status == "published")
    )
    documents = result.scalars().all()

    success_count = 0
    fail_count = 0
    for doc in documents:
        ok = await embed_document(db, doc.id)
        if ok:
            success_count += 1
        else:
            fail_count += 1

    return ApiResponse(
        data={
            "total": len(documents),
            "success": success_count,
            "failed": fail_count,
        }
    )
