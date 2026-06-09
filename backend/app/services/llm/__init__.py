"""LLM 抽象层 — OpenAI / Hermes / 自托管 provider 集合

用法：
    from app.services.llm import get_provider
    provider = get_provider()
    text = await provider.complete([{"role": "user", "content": "hi"}])
    async for chunk in provider.stream(messages):
        ...
"""
from app.services.llm.base import LLMProvider, get_provider, register

__all__ = ["LLMProvider", "get_provider", "register"]
