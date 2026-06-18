"""编辑器 AI prompt 边界测试。

这些测试不调用 LLM，只确认 v0.1.0-alpha 暴露的 6 个动作都有明确、
客观的 system/user prompt，避免 UI 入口和 prompt 能力漂移。
"""
from types import SimpleNamespace

import pytest

from app.services.editor_ai_actions import build_messages


def _req(action: str, **kwargs):
    base = {
        "action": action,
        "content": "# 快速开始\n\nOpenDocX 用于管理项目文档。",
        "selection": "OpenDocX 用于管理项目文档。",
        "question": "这段话说明了什么？",
        "context": {
            "project_name": "OpenDocX Demo",
            "version": "v1.0",
            "doc_title": "快速开始",
        },
    }
    base.update(kwargs)
    return SimpleNamespace(**base)


@pytest.mark.parametrize("action", ["continue", "rewrite", "explain", "qa", "summarize", "polish"])
def test_editor_ai_prompts_have_guardrails(action: str):
    messages = build_messages(_req(action))
    assert [m["role"] for m in messages] == ["system", "user"]

    system = messages[0]["content"]
    user = messages[1]["content"]

    assert "Markdown" in system
    assert "中文输出" in system
    assert "不编造数据、接口、版本号" in system
    assert "OpenDocX Demo" in user
    assert "v1.0" in user
    assert "快速开始" in user


def test_qa_prompt_with_selection_stays_on_selection():
    messages = build_messages(_req("qa"))
    user = messages[1]["content"]
    assert "请只基于选中的片段回答" in user
    assert "片段信息不足" in user


def test_unknown_editor_ai_action_is_rejected():
    with pytest.raises(ValueError):
        build_messages(_req("generate-openapi"))
