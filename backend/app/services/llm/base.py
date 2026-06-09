"""LLM 抽象层 — base + registry

P0-B-1: 4 个核心动作（续写/改写/Q&A/总结）都走这个接口。
新增 provider = 写一个继承 LLMProvider 的类，在 registry 注册。
"""
from abc import ABC, abstractmethod
from typing import AsyncGenerator
from app.services.llm.config import LLMConfig


class LLMProvider(ABC):
    """LLM 提供方抽象接口"""

    @abstractmethod
    async def complete(self, messages: list[dict], **kwargs) -> str:
        """非流式：返回完整文本"""
        ...

    @abstractmethod
    async def stream(self, messages: list[dict], **kwargs) -> AsyncGenerator[str, None]:
        """流式：每 yield 一段 delta 文本"""
        ...

    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        """向量化（单文本，复用搜索升级）"""
        ...


# ── Provider 注册表 ─────────────────────────────────────────
_providers: dict[str, type[LLMProvider]] = {}


def register(name: str):
    """装饰器：注册一个 provider 类"""
    def deco(cls: type[LLMProvider]) -> type[LLMProvider]:
        _providers[name] = cls
        return cls
    return deco


def get_provider() -> LLMProvider:
    """根据 LLM_PROVIDER env 取一个实例"""
    cfg = LLMConfig.from_env()
    name = cfg.provider
    if name not in _providers:
        raise RuntimeError(
            f"Unknown LLM_PROVIDER={name!r}. "
            f"Available: {list(_providers.keys())}. "
            f"Did you forget to import the provider module?"
        )
    return _providers[name](cfg)


# 触发 provider 自注册（import 副作用）
from app.services.llm.openai_provider import OpenAIProvider  # noqa: E402
from app.services.llm.hermes_provider import HermesProvider  # noqa: E402
