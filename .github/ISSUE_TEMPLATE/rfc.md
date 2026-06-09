---
name: 提案 / RFC
about: 重大架构 / API / 设计方向讨论
title: "[RFC] <一句话描述>"
labels: rfc, needs-discussion
assignees: ''
---

## 摘要 (1 段)

<用 1 段话说明这个 RFC 想解决什么, 改什么>

## 动机 (Why?)

<为什么要做这个? 不做会怎样? 用户的痛点是什么?>

## 详细方案 (What?)

<具体设计, 接口签名, 数据流, 状态变化, 用户交互>

### API 变化 (如有)

```python
# 新增
POST /api/v1/<endpoint>
Request: { ... }
Response: { ... }
```

### 数据模型 (如有)

```sql
ALTER TABLE <x> ADD COLUMN <y> <type>;
```

### 前端组件 (如有)

```tsx
<NewComponent prop={value} />
```

## 替代方案 (What else?)

### 不做的代价

<列 3-5 条具体后果>

### 备选方案 A

...

### 备选方案 B

...

## 风险与代价

- **复杂度**: <新增多少代码 / 概念>
- **向后兼容**: <破坏性 / 非破坏性>
- **测试成本**: <需要哪些新测试>
- **文档成本**: <需要哪些文档更新>
- **维护负担**: <是否需要长期维护>

## 开放问题 (待讨论)

- [ ] 问题 1
- [ ] 问题 2
- [ ] 问题 3

## 时间线

- 提案: 2026-XX-XX
- 讨论期: 1-2 周
- 实现期: <估时>
- 发布: v0.X.0

## 参考

- 相关 issue: #xxx
- 业界参考: <Docusaurus / Notion / GitBook 的类似设计>
- 内部文档: <链接>
