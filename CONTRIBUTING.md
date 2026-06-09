# 贡献指南

感谢你愿意参与 OpenDocX。这个项目还在 v0.x 阶段，最需要的是清晰的问题反馈、真实使用场景、可复现的 bug 和小步稳定的改进。

## 开始之前

请先阅读：

- [README](README.md)
- [用户指南](docs/USER-GUIDE.md)
- [架构说明](docs/ARCHITECTURE.md)
- [安全策略](SECURITY.md)

## 本地开发

准备环境：

```bash
cp .env.example .env
```

后端：

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
cd ..
bash scripts/seed_demo.sh
bash backend/scripts/start-backend.sh
```

前端：

```bash
cd frontend
npm ci
npx vite --host 0.0.0.0 --port 3077
```

默认账号：

```text
admin@opendocx.local / admin123
```

## 分支与提交

建议分支命名：

```text
feat/<name>
fix/<name>
docs/<name>
test/<name>
```

提交信息建议：

```text
feat: 增加文档移动到文件夹功能
fix: 修复审计日志列宽计算
docs: 更新中文用户指南
test: 增加构建前确认用例
```

## PR 要求

提交 PR 前请确认：

- 改动范围尽量聚焦。
- 没有提交 `.env`、本地数据、缓存、构建产物和个人路径。
- 涉及界面改动时提供截图。
- 涉及接口或行为改动时更新文档。
- 说明你实际跑过哪些验证。

PR 描述建议包含：

```text
## 改动

## 验证

## 截图

## 风险
```

## 测试

后端：

```bash
cd backend
source venv/bin/activate
pytest
```

前端：

```bash
cd frontend
npx tsc --noEmit
```

如果没有跑完某项测试，请在 PR 中说明原因。

## 设计与前端贡献

OpenDocX 的界面原则：

- 后台优先清晰、高效、可扫描。
- 浅色主题保持统一和克制。
- 项目主题色用于强调，不要破坏整体阅读秩序。
- 列表、表格、表单要优先保证密度、对齐和可读性。
- 关键操作需要连续状态反馈。

界面改动最好附带：

- 改动前后截图。
- 桌面端和窄屏端截图。
- 关键交互说明。

## 安全问题

请不要把安全漏洞直接公开在 Issue 中。处理方式见 [安全策略](SECURITY.md)。

## 协议

提交到本仓库的代码默认采用 [Apache License 2.0](LICENSE)。
