"""编辑器 AI 路由 — P0-B-2

4 个核心动作（续写 / 改写 / Q&A / 总结）走 /api/v1/editor/ai
请求参数 action + 上下文，返回 SSE 流（Server-Sent Events）
前端 EventSource / fetch+ReadableStream 都能接。

SSE 事件类型:
  event: token        data: {"delta": "..."}         增量文本
  event: meta         data: {"action": "...", "model": "..."}  头部
  event: done         data: {"ok": true}             结束
  event: error        data: {"message": "..."}       错误

注：业务逻辑（prompt 组装、上下文管理）放到 services/editor_ai_actions.py，
路由只负责鉴权 + 流转发。
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import json
import logging

from app.utils.auth import get_current_user
from app.models import User
from app.services.llm import get_provider
from app.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/editor", tags=["编辑器 AI"])


class AIRequest(BaseModel):
    """AI 编辑器请求体"""
    action: str = Field(..., description="动作: continue / rewrite / qa / summarize")
    content: str = Field(default="", description="当前文档内容（全文或选中片段）")
    selection: Optional[str] = Field(default=None, description="选中的文本片段（改写/解释时用）")
    question: Optional[str] = Field(default=None, description="Q&A 模式的问题")
    context: Optional[dict] = Field(default=None, description="上下文：project_id / version_id / title 等")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2048, ge=64, le=8192)


def _sse(event: str, data: dict) -> str:
    """格式化一个 SSE 事件"""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/ai")
async def editor_ai(
    req: AIRequest,
    current_user: User = Depends(get_current_user),
):
    """编辑器 AI 入口 — SSE 流式

    用 StreamingResponse 返回 text/event-stream，前端用 EventSource
    监听 token / done / error 事件。
    """
    # 1. 校验 action
    valid_actions = {"continue", "rewrite", "qa", "summarize", "explain", "polish"}
    if req.action not in valid_actions:
        raise HTTPException(status_code=400, detail=f"action 必须是 {valid_actions} 之一")

    # 2. 校验内容
    if req.action in ("continue", "rewrite", "explain", "polish") and not req.content.strip():
        raise HTTPException(status_code=400, detail=f"{req.action} 需要 content")
    if req.action == "qa" and not req.question:
        raise HTTPException(status_code=400, detail="qa 需要 question")

    # 3. 调业务层组装 messages
    from app.services.editor_ai_actions import build_messages
    messages = build_messages(req)

    # 4. 拿到 LLM provider
    try:
        provider = get_provider()
    except (RuntimeError, ValueError) as e:
        # R12: ValueError 来自 LLMConfig.__post_init__ 的 api_key fail-fast
        # (空 / 占位符 / URL 片段 / 长度不足), 给前端清晰提示
        logger.warning(f"LLM provider init failed: {e}")
        raise HTTPException(
            status_code=503,
            detail={
                "error": "llm_not_configured",
                "message": str(e),
                "hint": "在 backend/.env 设置 LLM_API_KEY=sk-... 格式的 OpenAI / 兼容服务 key",
            },
        )

    # 5. 异步生成器 → SSE
    async def event_stream():
        try:
            yield _sse("meta", {
                "action": req.action,
                "model": provider.model,
            })
            async for delta in provider.stream(
                messages,
                temperature=req.temperature,
                max_tokens=req.max_tokens,
            ):
                yield _sse("token", {"delta": delta})
            yield _sse("done", {"ok": True})
        except Exception as e:
            logger.exception("editor_ai stream failed")
            # R12: Illegal header value 说明 LLM_API_KEY 含 httpx 不接受的字符
            # (换行/非 ASCII 等). 提示用户检查 .env
            err_msg = str(e)
            if "Illegal header value" in err_msg:
                err_msg = (
                    f"LLM_API_KEY 配置导致 httpx 拒绝 header: {err_msg}. "
                    "请检查 .env 中 LLM_API_KEY 是否含换行/非 ASCII 字符。"
                )
            yield _sse("error", {"message": err_msg})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # nginx 关闭缓冲
        },
    )


@router.get("/actions")
async def list_actions(current_user: User = Depends(get_current_user)):
    """返回支持的 AI 动作清单（前端 AI 弹出层用）"""
    return {
        "actions": [
            {"id": "continue", "label": "续写", "icon": "edit", "needs": ["content"]},
            {"id": "rewrite",  "label": "改写", "icon": "sync", "needs": ["selection"]},
            {"id": "explain",  "label": "解释", "icon": "question", "needs": ["selection"]},
            {"id": "qa",       "label": "问答", "icon": "chat", "needs": ["question", "content"]},
            {"id": "summarize","label": "总结", "icon": "compress", "needs": ["content"]},
            {"id": "polish",   "label": "润色", "icon": "sparkle", "needs": ["selection"]},
        ]
    }


@router.get("/health")
async def editor_health():
    """检查 LLM provider 配置是否可用（不真发请求）"""
    try:
        provider = get_provider()
        return {"ok": True, "provider": provider.__class__.__name__, "model": provider.model}
    except (RuntimeError, ValueError) as e:
        return {"ok": False, "error": str(e)}


# ── P1-UI-6 高级 AI 卡：文档静态分析 ──────────────────────

class AnalyzeRequest(BaseModel):
    """P1-UI-6 分析请求体"""
    content: str = Field(..., description="当前文档 markdown 全文")
    version_id: Optional[str] = Field(default=None, description="用于查同版本其他文档标题，做知识关联匹配")
    doc_id: Optional[str] = Field(default=None, description="当前文档 id（用于排除自身）")


@router.post("/analyze")
async def editor_analyze(
    req: AnalyzeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """P1-UI-6: 高级 AI 卡数据源

    返回：
      {
        summary: {text, confidence},
        health: {score, grade, breakdown, stats},
        terminology: {terms: [{term, count}], issues: []},
        interface: {endpoints: [{method, path}], error_codes: [], issues: []},
        knowledge: {related: [{id, title, match_count, matched_terms}]}
      }

    不调 LLM，纯规则分析（毫秒级响应）。
    """
    from app.services.ai_analyzer import analyze_document
    from app.models import Document

    # 拉同版本其他文档标题（用于知识关联匹配）
    other_docs: list[dict] = []
    if req.version_id:
        stmt = select(Document.id, Document.title).where(
            Document.version_id == req.version_id
        )
        if req.doc_id:
            stmt = stmt.where(Document.id != req.doc_id)
        stmt = stmt.limit(50)
        rows = (await db.execute(stmt)).all()
        other_docs = [{"id": str(r[0]), "title": r[1]} for r in rows]

    result = analyze_document(
        content=req.content,
        other_doc_titles=other_docs,
        current_doc_id=req.doc_id,
    )
    return result
