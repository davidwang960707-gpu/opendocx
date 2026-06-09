# OpenDocX 开源检查清单

这份清单用于 v0.1.0-alpha 开源前自查。目标不是宣称生产完备，而是确保新用户能理解产品、跑起项目、看到主链路，并且不会暴露内部数据。

## 代码与数据

- [x] 使用干净仓库导出，不携带内部 Git 历史。
- [x] 不提交 `.env`、数据库、本地构建产物、缓存和个人路径。
- [x] 提供 `.env.example`。
- [x] Demo seed 使用公开示例数据。
- [x] 默认账号为 `admin@opendocx.local / admin123`。
- [x] 敏感信息扫描无命中。

## 文档

- [x] README 中文化。
- [x] 用户指南中文化。
- [x] 架构说明中文化。
- [x] 路线图中文化。
- [x] API 参考中文化。
- [x] 贡献指南、安全策略、行为准则中文化。
- [x] GitHub Issue / PR 模板中文化。
- [x] Markdown 渲染能力示例加入开源版。

## 截图

- [x] 使用当前 OpenDocX 环境重新截图。
- [x] 删除或不再引用旧品牌、旧布局、旧主题截图。
- [x] README 只引用当前可代表 v0.1.0-alpha 的核心截图。

## 功能

- [x] 登录。
- [x] 项目管理。
- [x] 版本和文档树。
- [x] Markdown 编辑。
- [x] AI 辅助。
- [x] 发布确认。
- [x] 静态站构建。
- [x] 反馈审核。
- [x] 用户管理。
- [x] 审计日志。

## 验证

- [ ] 在干净数据库上执行 `bash scripts/seed_demo.sh`。
- [ ] 后端测试通过。
- [ ] 前端 TypeScript 检查通过。
- [ ] Docker Compose 跑通。
- [ ] 构建 demo 静态站并确认 `/published` 与 `/docs` 可访问。

## 发布

- [x] Apache 2.0 协议。
- [x] 初始 tag：`v0.1.0-alpha`。
- [ ] 创建公开 GitHub 仓库。
- [ ] 推送 main 分支和 tag。
- [ ] 发布第一版 release notes。
