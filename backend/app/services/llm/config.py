"""LLM 配置 — 独立模块，绕开 config.py redaction 问题

不依赖 app.config，直接 os.environ.get()，默认值是 OpenAI 兼容。
切到 Hermes：env 里设 LLM_PROVIDER=hermes + 改 base_url/api_key/model。
"""
import os
import re
from dataclasses import dataclass


# 已知非法 api_key 模式 (R12 修复): 防止误把 URL/placeholder 当 key 传
#   1. 字面 *** /  *** (常见占位符)
#   2. 空字符串
#   3. 包含 / \ 或 : 等 URI 片段字符 (说明误填了 URL 的一部分)
#   4. 长度 < 20 (sk-... 至少 51 字符)
_PLACEHOLDER_PATTERNS = re.compile(r"^(\*+|<.*?>|\$\{.*?\})$")
_URI_FRAGMENT_CHARS = re.compile(r"[/:\\]")


@dataclass(frozen=True)
class LLMConfig:
    provider: str  # "openai" | "hermes"
    base_url: str
    api_key: str
    model: str
    timeout: float

    def __post_init__(self):
        """R12 修复: api_key 启动时 fail-fast, 避免运行时神秘 Illegal header value"""
        if not self.api_key or self.api_key.strip() == "":
            raise ValueError(
                f"LLM_API_KEY 环境变量未配置 (provider={self.provider!r}, model={self.model!r}). "
                "请在 backend/.env 设 LLM_API_KEY=sk-... 格式的 OpenAI / Azure / 兼容服务 key。"
            )
        if _PLACEHOLDER_PATTERNS.match(self.api_key):
            raise ValueError(
                f"LLM_API_KEY 仍为占位符 ({self.api_key!r}). "
                "请把 .env 里 LLM_API_KEY=*** 改成真正的 OpenAI / 兼容服务 key。"
            )
        if _URI_FRAGMENT_CHARS.search(self.api_key):
            raise ValueError(
                f"LLM_API_KEY 含 URL 片段字符 (/ : \\) ({self.api_key[:8]!r}...). "
                "看起来误把 base_url 一部分当 key 填了。请检查 .env 配置。"
            )
        if len(self.api_key) < 20:
            raise ValueError(
                f"LLM_API_KEY 长度仅 {len(self.api_key)} 字符, 正常 OpenAI key 至少 51 字符. "
                "请检查 .env 配置是否正确。"
            )

    @classmethod
    def from_env(cls) -> "LLMConfig":
        return cls(
            provider=os.environ.get("LLM_PROVIDER", "openai"),
            base_url=os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1"),
            api_key=os.environ.get("LLM_API_KEY", ""),
            model=os.environ.get("LLM_MODEL", "gpt-4o-mini"),
            timeout=float(os.environ.get("LLM_TIMEOUT", "60")),
        )
