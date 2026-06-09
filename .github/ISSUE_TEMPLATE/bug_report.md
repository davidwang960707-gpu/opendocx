---
name: Bug Report
about: 报告 OpenDocX 的一切 bug (前端 / 后端 / LLM / 静态站 / 部署)
title: "[Bug] <一句话描述>"
labels: bug
assignees: ''
---

## Bug 描述

<清晰说明 bug 是什么, 一句话>

## 复现步骤

1. <步骤 1>
2. <步骤 2>
3. <步骤 3>
4. <看到 bug>

## 期望行为

<应该发生什么>

## 实际行为

<实际发生什么>

## 截图 / GIF (强烈推荐)

<如果是 UI bug, 截图能省 90% 沟通成本>

## 环境信息

- **OS**: [例: macOS 14.5 / Ubuntu 22.04 / Windows 11]
- **浏览器**: [例: Chrome 126 / Safari 17]
- **Python**: [例: 3.12.7]
- **Node.js**: [例: 18.19.0]
- **PostgreSQL**: [例: 16.3 (pgvector 0.7.0)]
- **OpenDocX 版本**: [例: v0.1.0 / commit hash / branch]

## 后端日志 (如有)

```text
<paste relevant logs, especially 5xx errors or traceback>
```

注: R12+ 起, LLM 错误会返回清晰中文 503, 完整 message 复制进 logs 即可。

## LLM 配置 (如涉及 AI 功能)

- **LLM_PROVIDER**: [openai / hermes]
- **LLM_BASE_URL**: [https://... (脱敏)]
- **LLM_MODEL**: [gpt-4o-mini / mimo-v2.5-pro / ...]
- **是否真实测试过**: [是 / 否 / 用 mock]

## 项目协作规则 v3 #4: 真根因 + 方案 3 选 1 (贡献者必填)

> 这是本仓库社区公约的一部分, 详见 CONTRIBUTING.md。

### 你的初步根因分析 (1 句话)

<猜一下根因, 即使猜错也是好的起点>

### 修复方案 3 选 1

**方案 A: <描述>**
- 工作量: [0.1d / 0.5d / 1d]
- 优点: ...
- 缺点: ...

**方案 B: <描述>**
- 工作量: ...
- 优点: ...
- 缺点: ...

**方案 C: 暂不修 / 关闭 issue**
- 原因: ...

**推荐方案**: A / B / C
**理由**: <1 句话>

## 严重性

- [ ] Blocker (核心功能不可用)
- [ ] Critical (数据丢失 / 安全)
- [ ] Major (功能受损, 有 workaround)
- [ ] Minor (UI / 体验问题, 不影响功能)
- [ ] Trivial (typo / 注释 / 文档)
