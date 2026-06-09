"""嵌入服务 — 文本转向量"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.config import get_settings
from app.models.document import Document
from app.models.document_embedding import DocumentEmbedding

settings = get_settings()

# 延迟加载模型（首次调用时加载，后续复用）
_model = None


def _get_model():
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _model = SentenceTransformer(settings.embedding_model, device=settings.embedding_device)
        except Exception:
            # 如果模型加载失败，返回 None（降级为关键词搜索）
            _model = None
    return _model


def is_model_available() -> bool:
    """检查 embedding 模型是否可用"""
    return _get_model() is not None


def get_embedding(text: str) -> list[float]:
    """将文本转换为向量。如果模型不可用，返回空列表。"""
    model = _get_model()
    if model is None:
        return []
    embedding = model.encode(text, normalize_embeddings=True)
    return embedding.tolist()


def get_embeddings(texts: list[str]) -> list[list[float]]:
    """批量文本转向量。"""
    model = _get_model()
    if model is None:
        return [[] for _ in texts]
    embeddings = model.encode(texts, normalize_embeddings=True, batch_size=32)
    return [e.tolist() for e in embeddings]


async def embed_document(db: AsyncSession, document_id: str) -> bool:
    """为单个文档生成 embedding 并存入数据库。

    Args:
        db: 数据库 session
        document_id: 文档 ID

    Returns:
        True 如果成功生成并保存，False 如果模型不可用或文档不存在
    """
    if not is_model_available():
        return False

    # 获取文档
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if doc is None:
        return False

    # 拼接 title + content 生成 embedding
    text = f"{doc.title}\n{doc.content or ''}".strip()
    if not text:
        return False

    embedding = get_embedding(text)
    if not embedding:
        return False

    # upsert：存在则更新，不存在则插入
    result = await db.execute(
        select(DocumentEmbedding).where(DocumentEmbedding.document_id == document_id)
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.embedding = embedding
    else:
        new_embedding = DocumentEmbedding(document_id=document_id, embedding=embedding)
        db.add(new_embedding)

    await db.commit()
    return True
