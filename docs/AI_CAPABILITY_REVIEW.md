# OpenDocX AI 能力确认

本文用于记录 v0.1.0-alpha 的 AI 能力边界，避免把规则分析、占位入口或未来规划误写成已经完成的大模型能力。

## 1. 能力分类

| 能力 | 类型 | 是否调用 LLM | v0.1.0-alpha 状态 |
| --- | --- | --- | --- |
| 编辑器 AI 浮层 | 生成式 AI | 是 | 已完成 |
| 文档 Insight 面板 | 规则分析 | 否 | 已完成 |
| 语义搜索 | Embedding / 向量检索 | 取决于配置 | 已完成基础能力 |
| 生成 OpenAPI 规范 | 生成式 AI | 应调用 LLM | 后续规划 |
| 生成 SDK / 测试 | 生成式 AI | 应调用 LLM | 后续规划 |
| 静态站读者问答 | 生成式 AI | 应调用 LLM | 后续规划 |

## 2. 编辑器 AI 浮层

入口：`POST /api/v1/editor/ai`

实现：

- 后端在 `backend/app/services/editor_ai_actions.py` 里集中组装 prompt。
- 路由在 `backend/app/routers/editor.py` 中通过 SSE 返回 `meta`、`token`、`done` 和 `error`。
- Provider 在 `backend/app/services/llm/` 中抽象，默认兼容 OpenAI 风格 Chat Completions。
- 前端 `AIFloatingActions.tsx` 只展示真实接入后端的 6 个动作。

已确认动作：

| action | 中文名称 | 说明 |
| --- | --- | --- |
| `continue` | 续写 | 根据当前文档上下文自然续写 |
| `rewrite` | 改写 | 改写选区，保留原意 |
| `explain` | 解释 | 解释选区含义、关键点和常见误区 |
| `qa` | 问答 | 基于选区或全文回答问题 |
| `summarize` | 总结 | 输出摘要和要点 |
| `polish` | 润色 | 改善语言流畅度和可读性 |

## 3. Prompt 设计原则

当前 prompt 应满足：

- 明确角色：技术文档、产品文档、API 文档、知识库助手。
- 明确输出格式：Markdown，可直接插入编辑器。
- 明确事实边界：不编造数据、接口、版本号；不确定时说明不确定。
- 明确上下文：项目、版本、文档标题会进入 prompt。
- 明确用户确认：AI 输出只进入对比弹窗，用户确认后才应用。
- 控制输入长度：根据动作截断到 1500、3000 或 4000 字，降低成本和延迟。

## 4. 文档 Insight 面板

入口：`POST /api/v1/editor/analyze`

实现：

- 由 `backend/app/services/ai_analyzer.py` 做确定性规则分析。
- 不调用 LLM，不把结果描述成大模型生成。
- 输出摘要、健康度、术语一致性、接口一致性和相关文档。

设计边界：

- 这不是生成式 AI。
- 置信度是规则分析评分，不是模型置信概率。
- 相关文档来自同版本文档标题匹配，不是向量召回。

## 5. v0.1.0-alpha 已移除的假入口

为避免误导，v0.1.0-alpha 不展示这些尚未真实实现的动作：

- 生成测试。
- 生成 OpenAPI 规范。
- 生成 SDK。

这些能力后续进入 v0.5.0 AI 工作流深化，需要独立 prompt、上下文输入、结果确认和测试覆盖。

## 6. 发布前确认项

- README、PRD、用户指南和 API 文档必须区分“LLM 生成”和“规则分析”。
- UI 不应展示未接入真实后端的生成式 AI 按钮。
- 测试中允许 mock provider，但产品文案不得把测试 mock 写成真实能力。
- `.env.example` 只能提供占位配置，运行时必须对空 key、占位 key 和异常 key fail-fast。
