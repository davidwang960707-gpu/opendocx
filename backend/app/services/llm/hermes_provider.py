"""Hermes Provider — 复用 OpenAI 协议

Hermes 的 API Server 走 OpenAI 兼容协议，所以可以直接继承 OpenAIProvider，
只换 URL/KEY/模型名。
"""
from app.services.llm.base import register
from app.services.llm.openai_provider import OpenAIProvider


@register("hermes")
class HermesProvider(OpenAIProvider):
    """Hermes 私有部署（默认 /v1/chat/completions）"""
    pass
