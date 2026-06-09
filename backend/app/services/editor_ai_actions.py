"""编辑器 AI 业务逻辑 — 4 个核心动作的 prompt 组装

P0-B-3: 把每个 action 的 system + user prompt 模板集中在这里。
路由只负责鉴权 + SSE 流转发，不写 prompt。

设计原则:
  - prompt 用中文，技术文档场景
  - 输出严格遵循 Markdown 格式（前端直接插入编辑器）
  - 上下文：项目标题 / 版本号 / 文档标题让 LLM 知道场景
  - 不超过 4000 token 输入（控制成本 + 延迟）
"""
from app.routers.editor import AIRequest


# ── 系统提示模板 ──────────────────────────────────────────

SYS_BASE = (
    "你是 OpenDocX 的文档 AI 助手，专门帮技术团队写产品文档、API 文档、知识库。"
    "输出用 Markdown，可直接贴进编辑器。"
    "中文输出，除非用户问英文。"
    "简洁有力，少用「综上所述」「值得注意的是」这种废话。"
    "不编造数据、接口、版本号；不确定就说不确定。"
)


def _ctx_prefix(req):
    """上下文前缀：项目 / 版本 / 文档"""
    ctx = req.context or {}
    bits = []
    if ctx.get("project_name"):
        bits.append(f"项目：{ctx['project_name']}")
    if ctx.get("version"):
        bits.append(f"版本：{ctx['version']}")
    if ctx.get("doc_title"):
        bits.append(f"文档：{ctx['doc_title']}")
    return ("（" + " / ".join(bits) + "）\n\n") if bits else ""


# ── 续写 ──────────────────────────────────────────

def _build_continue(req):
    ctx = _ctx_prefix(req)
    sys_p = SYS_BASE + " 你的任务：根据已有内容自然续写下一段。保持语气、风格、结构一致。"
    user_p = (
        f"{ctx}当前文档内容（可能截断到最近 3000 字）：\n\n"
        "---\n"
        f"{req.content[-3000:]}\n"
        "---\n\n"
        "请续写下一段。不重复已有内容；如需分点用 1. 2. 3. 编号；"
        "代码块用 ``` 包裹并标语言。直接输出续写内容，不要「好的我来续写」之类的开场白。"
    )
    return [
        {"role": "system", "content": sys_p},
        {"role": "user", "content": user_p},
    ]


# ── 改写 ──────────────────────────────────────────

def _build_rewrite(req):
    target = (req.selection or req.content)[-1500:]
    ctx = _ctx_prefix(req)
    sys_p = (
        SYS_BASE
        + " 你的任务：把选中片段改写得更清晰、更专业，但保留原意。"
        "改写原则：同义替换用更精准的技术词；长句拆短，嵌套扁平化；"
        "去掉「进行了」「实现了」等空动词；保留关键术语和数字不替换。"
    )
    user_p = (
        f"{ctx}原文：\n\n```\n{target}\n```\n\n"
        "请直接输出改写后的 Markdown，不要加「改写后：」前缀或解释。"
    )
    return [
        {"role": "system", "content": sys_p},
        {"role": "user", "content": user_p},
    ]


# ── 解释 ──────────────────────────────────────────

def _build_explain(req):
    target = (req.selection or req.content)[-1500:]
    ctx = _ctx_prefix(req)
    sys_p = SYS_BASE + " 你的任务：用 1-3 段解释选中片段在做什么、为什么这样设计、有什么坑。"
    user_p = (
        f"{ctx}需要解释的片段：\n\n```\n{target}\n```\n\n"
        "请按下面结构输出：\n\n"
        "**这段在做什么**：（一句话）\n\n"
        "**关键点**：（2-4 条要点）\n\n"
        "**常见误区**：（1-2 条，可选）"
    )
    return [
        {"role": "system", "content": sys_p},
        {"role": "user", "content": user_p},
    ]


# ── 问答 ─────────────────────────────────────────────

def _build_qa(req):
    ctx = _ctx_prefix(req)
    sys_p = (
        SYS_BASE
        + " 你的任务：基于用户提供的文档内容回答问题。"
        "如果文档没提到，明确说「文档中未提及」。"
        "引用原文用 > 引用块；不要编造文档外的事实。"
    )
    # R13 fix: 区分"基于选区问答"和"基于全文问答"
    # 之前无论有没有 selection, 都把 content 全文塞进 prompt, LLM 答"全文讲什么"
    # 现在: 有 selection → 只基于选中片段答, 没 selection → 用全文
    if req.selection and req.selection.strip():
        user_p = (
            f"{ctx}文档全文（参考, 截断到 3000 字）：\n\n"
            "---\n"
            f"{req.content[-3000:]}\n"
            "---\n\n"
            f"用户选中的片段：\n"
            f"「{req.selection}」\n\n"
            f"问题：{req.question}\n\n"
            "请只基于选中的片段回答。引用原句用 > 引用块。"
            "如果选中片段不足以回答, 明确说「片段信息不足」, 不要扩展到全文。"
        )
    else:
        user_p = (
            f"{ctx}文档内容（截断到 4000 字）：\n\n"
            "---\n"
            f"{req.content[-4000:]}\n"
            "---\n\n"
            f"问题：{req.question}\n\n"
            "请回答。如果文档信息不足，诚实说明。"
        )
    return [
        {"role": "system", "content": sys_p},
        {"role": "user", "content": user_p},
    ]


# ── 总结 ──────────────────────────────────────────

def _build_summarize(req):
    ctx = _ctx_prefix(req)
    sys_p = SYS_BASE + " 你的任务：把文档压成 5 行内的摘要 + 3-5 个要点列表。"
    user_p = (
        f"{ctx}文档内容（截断到 4000 字）：\n\n"
        "---\n"
        f"{req.content[-4000:]}\n"
        "---\n\n"
        "请输出：\n\n"
        "**摘要**：（3-5 句覆盖核心目的、对象、关键决策）\n\n"
        "**要点**：\n"
        "- 要点 1\n- 要点 2\n- 要点 3\n（最多 5 条）"
    )
    return [
        {"role": "system", "content": sys_p},
        {"role": "user", "content": user_p},
    ]


# ── 润色 ──────────────────────────────────────────

def _build_polish(req):
    target = (req.selection or req.content)[-1500:]
    ctx = _ctx_prefix(req)
    sys_p = (
        SYS_BASE
        + " 你的任务：润色选中片段让语言更流畅、可读性更好。"
        "改语病、不改意思；加必要的过渡词；适合产品文档语气（专业但不生硬）。"
    )
    user_p = (
        f"{ctx}原文：\n\n```\n{target}\n```\n\n"
        "请输出润色后的 Markdown。"
    )
    return [
        {"role": "system", "content": sys_p},
        {"role": "user", "content": user_p},
    ]


# ── 调度器 ──────────────────────────────────────────

_BUILDERS = {
    "continue":  _build_continue,
    "rewrite":   _build_rewrite,
    "explain":   _build_explain,
    "qa":        _build_qa,
    "summarize": _build_summarize,
    "polish":    _build_polish,
}


def build_messages(req):
    """根据 action 选 builder，返回 OpenAI 协议 messages 列表"""
    builder = _BUILDERS.get(req.action)
    if not builder:
        raise ValueError(f"Unsupported action: {req.action}")
    return builder(req)
