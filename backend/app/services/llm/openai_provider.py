"""OpenAI 兼容 Provider

通用实现，支持任何 OpenAI Chat Completions API 兼容服务
（包括 OpenAI 官方、Azure OpenAI、本地 vLLM、Ollama 等）。
"""
import json
import httpx
from typing import AsyncGenerator
from app.services.llm.base import LLMProvider, register


@register("openai")
class OpenAIProvider(LLMProvider):
    """OpenAI / OpenAI-compatible chat completions"""

    def __init__(self, cfg):
        # cfg 是 LLMConfig dataclass
        self.base_url = cfg.base_url.rstrip("/")
        self.api_key = cfg.api_key
        self.model = cfg.model
        self.timeout = httpx.Timeout(cfg.timeout, connect=10.0)

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _payload(self, messages: list[dict], stream: bool, **kwargs) -> dict:
        p = {
            "model": self.model,
            "messages": messages,
            "stream": stream,
            "temperature": kwargs.get("temperature", 0.7),
        }
        if "max_tokens" in kwargs:
            p["max_tokens"] = kwargs["max_tokens"]
        return p

    async def complete(self, messages: list[dict], **kwargs) -> str:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=self._payload(messages, stream=False, **kwargs),
            )
            r.raise_for_status()
            data = r.json()
            return data["choices"][0]["message"]["content"]

    async def stream(self, messages: list[dict], **kwargs) -> AsyncGenerator[str, None]:
        # 用 SSE 流式增量返回
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=self._payload(messages, stream=True, **kwargs),
            ) as r:
                r.raise_for_status()
                async for line in r.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    payload = line[6:]  # 去掉 "data: "
                    if payload == "[DONE]":
                        break
                    try:
                        chunk = json.loads(payload)
                    except json.JSONDecodeError:
                        continue
                    choices = chunk.get("choices") or []
                    if not choices:
                        continue
                    delta = choices[0].get("delta") or {}
                    content = delta.get("content")
                    if content:
                        yield content

    async def embed(self, text: str) -> list[float]:
        """OpenAI 兼容的 embedding 端点（默认 /v1/embeddings）"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.post(
                f"{self.base_url}/embeddings",
                headers=self._headers(),
                json={"model": self.model, "input": text},
            )
            r.raise_for_status()
            data = r.json()
            return data["data"][0]["embedding"]
