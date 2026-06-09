"""LLM 抽象层测试

P0-B-1: 验证 provider 注册、配置加载、provider 切换。
不真发请求（需要真 key），只验证接口契约。
"""
import os
import pytest
from app.services.llm import get_provider
from app.services.llm.base import _providers, LLMProvider
from app.services.llm.config import LLMConfig


def test_openai_provider_registered():
    assert "openai" in _providers
    from app.services.llm.openai_provider import OpenAIProvider
    assert _providers["openai"] is OpenAIProvider


def test_hermes_provider_registered():
    assert "hermes" in _providers
    from app.services.llm.hermes_provider import HermesProvider
    assert _providers["hermes"] is HermesProvider
    # HermesProvider 应是 OpenAIProvider 的子类（OpenAI 协议兼容）
    from app.services.llm.openai_provider import OpenAIProvider
    assert issubclass(_providers["hermes"], OpenAIProvider)


def test_config_from_env_defaults():
    """R12+: 不设 key 应 fail-fast, 避免运行时神秘 LLM 错误"""
    for k in ("LLM_PROVIDER", "LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL"):
        os.environ.pop(k, None)
    with pytest.raises(ValueError, match="LLM_API_KEY 环境变量未配置"):
        LLMConfig.from_env()


def test_config_from_env_override():
    """env 覆盖应生效"""
    os.environ["LLM_PROVIDER"] = "hermes"
    os.environ["LLM_BASE_URL"] = "http://127.0.0.1:8642/v1"
    os.environ["LLM_API_KEY"] = "test-openai-key-000000000000"
    os.environ["LLM_MODEL"] = "hermes-agent"
    cfg = LLMConfig.from_env()
    assert cfg.provider == "hermes"
    assert cfg.base_url == "http://127.0.0.1:8642/v1"
    assert cfg.api_key == "test-openai-key-000000000000"
    assert cfg.model == "hermes-agent"
    # 清理
    for k in ("LLM_PROVIDER", "LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL"):
        os.environ.pop(k, None)


def test_get_provider_returns_correct_instance():
    """get_provider 应根据 env 返回对应实例"""
    os.environ["LLM_PROVIDER"] = "openai"
    os.environ["LLM_API_KEY"] = "test-openai-key-000000000000"
    p = get_provider()
    assert isinstance(p, LLMProvider)
    from app.services.llm.openai_provider import OpenAIProvider
    assert isinstance(p, OpenAIProvider)

    os.environ["LLM_PROVIDER"] = "hermes"
    p = get_provider()
    from app.services.llm.hermes_provider import HermesProvider
    assert isinstance(p, HermesProvider)
    for k in ("LLM_PROVIDER", "LLM_API_KEY"):
        os.environ.pop(k, None)


def test_unknown_provider_raises():
    os.environ["LLM_PROVIDER"] = "nonexistent"
    os.environ["LLM_API_KEY"] = "test-openai-key-000000000000"
    with pytest.raises(RuntimeError, match="Unknown LLM_PROVIDER"):
        get_provider()
    for k in ("LLM_PROVIDER", "LLM_API_KEY"):
        os.environ.pop(k, None)
