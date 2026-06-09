---

<!--
项目协作规则 v3 #3: 修+验证 一次 commit 收
项目协作规则 v3 #6: PR 描述必含真根因 + 验证证据 (反例: "啥也不是")
-->

## 描述

<简明描述这次 PR 改了什么, 解决什么问题>

## 真根因 (1 句话)

<这是项目协作规则 v3 #6 核心要求, 列出 1 句话说清真根因, 而非"修了个 bug">

例:
- Bug 13 真根因: 后端 `_build_qa` 完全没读 `req.selection`, 选区被静默丢弃
- Bug 14 真根因: 接受替换走 `indexOf` 二次匹配, trim 后 text 跟 start..end 长度对不上, 经常 -1 兜底到末尾追加

## 改动 (Files Changed)

- `path/to/file.py` (+N / -M): <为什么改>
- `path/to/component.tsx` (+N): <新组件, 做什么>

## 验证 (Verification)

> 项目协作规则 v3 #6: 0 mock 数据, TestClient + 浏览器 E2E 真实数据驱动

### 后端 (如适用)

```text
pytest tests/test_<x>.py -v
# 输出: N passed in Xs
```

- [ ] TestClient 单测通过 (列出 case 数)
- [ ] DB 真实状态验证 (附 SQL / screenshot)

### 前端 (如适用)

```text
npx tsc --noEmit
# 输出: 0 errors
```

- [ ] `npx tsc --noEmit` 0 错
- [ ] 浏览器 E2E 验证 (描述步骤 + screenshot 链接)

### 端到端 (如适用)

- [ ] 真实 API + 真实 DB 验证
- [ ] 截图 / GIF

## 风险

- **潜在副作用 1**: <描述>
- **潜在副作用 2**: <描述>
- **回滚方法**: <1 句话说怎么回滚>

## 截图 / 演示 (如适用)

| Before | After |
|---|---|
|  |  |

## 关联 Issue

- Closes #xxx
- Related to #yyy

## Checklist

- [ ] 真根因列了
- [ ] 验证证据列了 (TestClient / tsc / E2E)
- [ ] 0 mock 数据
- [ ] 0 emoji (UI 文本)
- [ ] 文档同步更新 (CHANGELOG.md / 用户可见行为)
- [ ] Self-review 完成
- [ ] 没遗留"修+没测"或"测+没修"的拆 commit
