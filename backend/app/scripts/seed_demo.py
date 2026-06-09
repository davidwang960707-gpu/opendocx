"""为新用户写入中文 Demo 数据。

用法:
    cd backend && source venv/bin/activate
    python -m app.scripts.seed_demo

创建:
    - 1 个管理员账号 (admin@opendocx.local / admin123)
    - 1 个中文示例项目 "OpenDocX 入门示例"
    - 3 篇中文示例文档:
        * getting-started.md (OpenDocX 快速入门)
        * ai-floating-tip-demo.md (AI 浮层示例)
        * render-showcase.md (静态站 Markdown 渲染能力速查)
    - 1 个默认反馈模板 (空)

这些数据仅用于本地试用，不包含任何内部项目或私有数据。
"""
import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.project import Project
from app.models.version import Version
from app.models.document import Document
from app.utils.auth import hash_password


# Compatibility: PostgreSQL TIMESTAMP WITHOUT TIME ZONE 列要 naive datetime
# (OpenAtlas P3.11 Bug 9 同源, R9 fix 统一用 .replace(tzinfo=None))
def _now() -> datetime:
    """Naive UTC datetime for TIMESTAMP WITHOUT TIME ZONE columns."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ===== Demo data constants =====

DEMO_ADMIN_EMAIL = "admin@opendocx.local"
DEMO_ADMIN_PASSWORD = "admin123"  # noqa: S105  - 公开 demo 凭据, README 写明

DEMO_PROJECT_NAME = "OpenDocX 入门示例"
DEMO_PROJECT_SLUG = "welcome-to-opendocx"
DEMO_PROJECT_DESC = "用于体验 OpenDocX 主链路的中文示例项目。你可以编辑、发布、构建，也可以在试用后删除。"

DEMO_VERSION_NAME = "v1.0"
DEMO_VERSION_DESC = "默认示例版本"

GETTING_STARTED_CONTENT = """# OpenDocX 快速入门

欢迎来到 OpenDocX 中文示例项目。这是一个可以放心试用的演示空间，用来体验项目文档从编辑到发布的完整链路。

## 你可以先试这几件事

### 1. 体验 AI 浮层

在编辑器里选中任意一段文字，旁边会出现 AI 浮层入口。你可以让 AI 帮你：

- 总结选中内容。
- 改写表达。
- 翻译文字。
- 解释概念。
- 根据选区回答问题。

### 2. 体验发布前确认

点击右上角的“构建”按钮，系统会先弹出发布前确认，而不是直接生成站点。这个弹窗会告诉你哪些文档会发布，哪些文档还停留在草稿状态。

### 3. 构建静态站

确认发布内容后再次开始构建，OpenDocX 会把数据库里的已发布文档生成纯静态站点。默认输出目录是：

```text
data/builds/welcome-to-opendocx/v1.0/
```

### 4. 使用命令面板

按下 `Cmd+K` 或 `Ctrl+K` 可以打开命令面板，快速跳转到项目、文档、发布和设置。

### 5. 切换主题

点击右上角头像，可以切换浅色和深色主题。

## Markdown 能力

OpenDocX 支持：

- 常见 Markdown 语法。
- 表格、任务列表、删除线。
- 代码块和语法高亮。
- 信息、提示、警告、危险等提示块。
- Mermaid 与公式的容器级样式。

## 下一步

- 修改这篇文档并观察预览。
- 在左侧文档树中新建文档。
- 发布文档并构建静态站。
- 查看反馈审核和审计日志。
"""

AI_TIP_DEMO_CONTENT = """# AI 浮层示例

这篇文档用于展示 OpenDocX 的 AI 浮层。请在编辑器中选中任意段落，观察选区旁边出现的操作入口。

## AI 浮层是什么？

AI 浮层是编辑器里的轻量辅助入口。当你选中文字后，它会提供一组常用动作：

1. **总结**：把选区压缩成更短的摘要。
2. **扩写**：为选区补充更多细节。
3. **翻译**：把选区翻译成目标语言。
4. **问答**：围绕选区回答问题。
5. **分析**：指出结构、风险或可改进点。
6. **改写**：提升表达清晰度和可读性。

## 如何使用

1. 用鼠标选中一段文字。
2. 等待选区附近出现 AI 入口。
3. 点击入口并选择一个动作。
4. 查看流式返回结果。
5. 如果满意，接受结果；如果不满意，直接丢弃。

## 可以试选这段文字

> OpenDocX 把项目文档的草稿、编辑、发布、静态站构建、反馈和审计放在同一个工作台里，适合用 AI 快速生成项目后补齐交付文档。

选中后可以尝试“总结”或“改写”，观察 AI 如何处理选区上下文。

## 隐私说明

AI 功能会把选区内容发送到你在 `.env` 中配置的 LLM 服务。请不要在未确认配置的情况下处理敏感数据。
"""


def _load_markdown_showcase() -> str:
    """从 examples/ 读取公开 Markdown 渲染示例。"""
    repo_root = Path(__file__).resolve().parents[3]
    showcase = repo_root / "examples" / "markdown-rendering-showcase.md"
    if showcase.exists():
        return showcase.read_text(encoding="utf-8")
    return """# OpenDocX 静态站渲染能力速查

仅当 `examples/markdown-rendering-showcase.md` 缺失时才会使用这段兜底内容。公开仓库应包含完整示例文件。
"""


MARKDOWN_RENDERING_SHOWCASE_CONTENT = _load_markdown_showcase()


# ===== Seed functions =====


async def seed_admin(db: AsyncSession) -> User:
    """创建或获取 Demo 管理员。"""
    result = await db.execute(
        select(User).where(User.email == DEMO_ADMIN_EMAIL)
    )
    admin = result.scalar_one_or_none()
    if admin:
        print(f"  - admin user already exists: {admin.email}")
        return admin

    admin = User(
        email=DEMO_ADMIN_EMAIL,
        name="OpenDocX Admin",
        password_hash=hash_password(DEMO_ADMIN_PASSWORD),
        role="admin",
        is_active=True,
    )
    db.add(admin)
    await db.flush()
    print(f"  + created admin: {admin.email} / {DEMO_ADMIN_PASSWORD}")
    return admin


async def seed_project(db: AsyncSession, admin: User) -> Project:
    """创建或获取中文 Demo 项目。"""
    result = await db.execute(
        select(Project).where(Project.slug == DEMO_PROJECT_SLUG)
    )
    project = result.scalar_one_or_none()
    if project:
        print(f"  - project already exists: {project.name}")
        return project

    project = Project(
        name=DEMO_PROJECT_NAME,
        slug=DEMO_PROJECT_SLUG,
        description=DEMO_PROJECT_DESC,
        created_by=admin.id,
        created_at=_now(),
    )
    db.add(project)
    await db.flush()
    print(f"  + created project: {project.name}")
    return project


async def seed_version(db: AsyncSession, project: Project) -> Version:
    """创建或获取默认版本 v1.0。"""
    result = await db.execute(
        select(Version).where(
            Version.project_id == project.id,
            Version.version == DEMO_VERSION_NAME,
        )
    )
    version = result.scalar_one_or_none()
    if version:
        print(f"  - version already exists: {version.version}")
        return version

    version = Version(
        project_id=project.id,
        version=DEMO_VERSION_NAME,
        is_default=True,
        created_at=_now(),
    )
    db.add(version)
    await db.flush()
    print(f"  + created version: {version.version}")
    return version


async def seed_documents(
    db: AsyncSession, version: Version, admin: User
) -> None:
    """创建中文 Demo 文档。"""
    docs_to_seed = [
        {
            "slug": "getting-started",
            "title": "OpenDocX 快速入门",
            "content": GETTING_STARTED_CONTENT,
            "sort_order": 1,
        },
        {
            "slug": "ai-floating-tip-demo",
            "title": "AI 浮层示例",
            "content": AI_TIP_DEMO_CONTENT,
            "sort_order": 2,
        },
        {
            "slug": "render-showcase",
            "title": "OpenDocX 静态站渲染能力速查",
            "content": MARKDOWN_RENDERING_SHOWCASE_CONTENT,
            "sort_order": 3,
        },
    ]

    for doc_data in docs_to_seed:
        result = await db.execute(
            select(Document).where(
                Document.version_id == version.id,
                Document.slug == doc_data["slug"],
            )
        )
        doc = result.scalar_one_or_none()
        if doc:
            print(f"  - 文档已存在: {doc_data['title']}")
            continue

        doc = Document(
            version_id=version.id,
            created_by=admin.id,
            slug=doc_data["slug"],
            title=doc_data["title"],
            content=doc_data["content"],
            status="published",
            sort_order=doc_data["sort_order"],
            created_at=_now(),
            updated_at=_now(),
        )
        db.add(doc)
        print(f"  + 已创建文档: {doc_data['title']}")

    await db.flush()


# ===== Main =====


async def main() -> None:
    print("=" * 60)
    print("OpenDocX 中文 Demo 数据初始化")
    print("=" * 60)
    print()
    print("此脚本只会在你的本地数据库中创建公开示例数据。")
    print("不会写入任何内部项目或私有数据。")
    print()

    async for db in get_db():
        try:
            print("[1/4] 创建管理员账号...")
            admin = await seed_admin(db)

            print("[2/4] 创建示例项目...")
            project = await seed_project(db, admin)

            print("[3/4] 创建默认版本...")
            version = await seed_version(db, project)

            print("[4/4] 创建示例文档...")
            await seed_documents(db, version, admin)

            await db.commit()
            print()
            print("=" * 60)
            print("中文 Demo 数据初始化完成。")
            print("=" * 60)
            print()
            print("下一步:")
            print("  1. 启动后端: bash backend/scripts/start-backend.sh")
            print("  2. 启动前端: cd frontend && npx vite --port 3077")
            print("  3. 打开: http://localhost:3077")
            print(f"  4. 登录: {DEMO_ADMIN_EMAIL} / {DEMO_ADMIN_PASSWORD}")
            print()

        except Exception as e:
            await db.rollback()
            print(f"\nERROR: {e}", file=sys.stderr)
            raise
        finally:
            await db.close()


if __name__ == "__main__":
    asyncio.run(main())
