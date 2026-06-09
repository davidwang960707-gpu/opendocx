"""项目管理路由"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import Project, User
from app.schemas import ProjectCreate, ProjectUpdate, ProjectOut, ApiResponse, PaginatedMeta
from app.utils.auth import get_current_user, require_role
from app.utils.audit import write_audit

router = APIRouter(prefix="/api/v1/projects", tags=["项目管理"])


async def _enrich_project(db: AsyncSession, p: Project, out: ProjectOut) -> None:
    """P1-UI-1/2: 注入 status / default_version_id / doc_count / last_activity_at
    直接修改 out 对象（in-place）。"""
    from app.models import Version, Document

    # 默认版本：去重修复 (R10 后置)：DB 中可能因 import/seed 历史包袱存在
    # 多个 is_default=True 的同 version 号 (e.g. llm-causal-zh 同时有 published + draft 两行 v1.0,
    # insight 有 6 个 v1.1-test 全 archived 默认)。取 created_at 最新的那个 (实际 DB 探查确认:
    # llm-causal-zh 2 行 v1.0 中 draft 那行是后期 seed/import 误生成,取最新 = draft 反而错)。
    # 因此走更安全策略:不依赖时间, 用 .scalars().all() 拿全,自己 Python 端选 published 优先,
    # 同 status 取最新。这样无论 SQLAlchemy 怎么序列 VersionStatus enum 都能正确比较。
    v_result = await db.execute(
        select(Version).where(Version.project_id == p.id, Version.is_default.is_(True))
    )
    all_default_vers = v_result.scalars().all()
    if all_default_vers:
        # Python 端排序: published 优先, 然后 created_at desc
        # 不用 reverse=True: 直接构造正序 (1=pub 优先位, 然后 created_at 倒序按时间戳)
        # sorted() 默认升序: published (1) > non-pub (0) 自动排前, 同 priority 用 -ts 倒序
        def _ver_score(v):
            st = v.status
            st_str = str(st).lower() if st else ""
            is_pub = "publish" in st_str
            return (1 if is_pub else 0, -v.created_at.timestamp())  # 负号 = desc
        sorted_vers = sorted(all_default_vers, key=_ver_score)  # 默认升序 = 想要的顺序
        default_ver = sorted_vers[0]
    else:
        default_ver = None

    # 文档数 + 最近文档更新时间
    doc_count = 0
    last_doc_updated = None
    if default_ver:
        dc_result = await db.execute(
            select(func.count(Document.id), func.max(Document.updated_at))
            .where(Document.version_id == default_ver.id)
        )
        doc_count, last_doc_updated = dc_result.one()
        doc_count = doc_count or 0

    # 状态：P1-W2-P2 优先用 p.status 真值, fallback 推导 (1.0 老数据)
    #   1) p.status 真值 (新创建/手动改后) → 直接用
    #   2) p.status 为 None (1.0 兜底推导)
    #      published + 有文档 → active
    #      published + 无文档 → paused
    #      draft     + 有文档 → active
    #      draft     + 无文档 → draft
    #      无 default version → paused
    if p.status and p.status in ("active", "paused", "draft", "archived"):
        out.status = p.status
    elif not default_ver:
        out.status = "paused"
    elif doc_count > 0:
        out.status = "active"
    else:
        out.status = default_ver.status if default_ver.status in ("paused", "draft") else "paused"

    last_activity = last_doc_updated or (default_ver.created_at if default_ver else p.created_at)

    out.default_version_id = default_ver.id if default_ver else None
    out.doc_count = doc_count
    out.last_activity_at = last_activity


@router.get("", response_model=ApiResponse)
async def list_projects(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取项目列表（分页）"""

    # 总数
    count_result = await db.execute(select(func.count(Project.id)))
    total = count_result.scalar() or 0

    # 分页查询
    offset = (page - 1) * page_size
    result = await db.execute(
        select(Project).order_by(Project.created_at.desc()).offset(offset).limit(page_size)
    )
    projects = result.scalars().all()

    enriched = []
    for p in projects:
        out = ProjectOut.model_validate(p)
        await _enrich_project(db, p, out)
        enriched.append(out)

    return ApiResponse(
        data=enriched,
        meta=PaginatedMeta(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=(total + page_size - 1) // page_size,
        ).model_dump(),
    )


@router.post("", response_model=ApiResponse, status_code=201)
async def create_project(
    req: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """创建项目（管理员）

    顺手建一个默认 v1.0 版本 + 一个"快速入门"示例文档，
    新用户建项目后能直接进入写文档，不需要先建 version。
    """
    from app.models import Version, Document
    # 检查 slug 唯一性
    existing = await db.execute(select(Project).where(Project.slug == req.slug))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="项目标识已存在")

    project = Project(
        name=req.name,
        slug=req.slug,
        description=req.description,
        brand_color=req.brand_color,
        created_by=current_user.id,
    )
    db.add(project)
    await db.flush()  # 拿到 project.id

    # 自动建默认版本 v1.0
    version = Version(
        project_id=project.id,
        version="v1.0",
        is_default=True,
        status="published",
    )
    db.add(version)
    await db.flush()

    # 自动建一个示例"快速入门"文档（draft 状态，用户可以编辑/发布/删除）
    starter_doc = Document(
        version_id=version.id,
        title="快速入门",
        slug="getting-started",
        content=(
            f"# {req.name}\n\n"
            f"{req.description or '欢迎使用 OpenDocX。'}\n\n"
            "## 写点什么\n\n"
            "这是一个示例文档，你可以编辑、发布、删除它。\n\n"
            "## 后续步骤\n\n"
            "- 点击右上角\"构建\"按钮生成静态站点\n"
            "- 在\"已发布站点\"页面查看构建结果\n"
            "- 切换到其他版本管理多套文档\n"
        ),
        status="draft",
        sort_order=0,
        created_by=current_user.id,
    )
    db.add(starter_doc)
    await db.flush()

    # 自动建一个 `slug="index"` 的首页配置文档 (Phase 5 段 C)
    # - draft 状态, 不出现在侧栏 / 章节页 / 最近更新
    # - 管理员可以编辑 markdown, 点"发布"后构建时 Hero 内容由此 doc 决定
    # - 未发布时 build 走默认 hardcode hero (不破坏现有体验)
    index_doc = Document(
        version_id=version.id,
        title=req.name,  # 默认用 project name 当 hero H1
        slug="index",
        content=(
            f"# {req.name}\n\n"
            f"{req.description or '面向开发者的 API 参考与集成指南'}\n\n"
            "## 快速开始\n\n"
            "从第一篇文档开始, 按章节顺序阅读。\n\n"
        ),
        status="draft",
        sort_order=-1,  # sort_order=-1 让 sidebar 排序时它排到最前, 但 build_service 过滤
        created_by=current_user.id,
    )
    db.add(index_doc)
    await db.commit()
    await db.refresh(project)
    out = ProjectOut.model_validate(project)
    await _enrich_project(db, project, out)
    await write_audit(actor=current_user, action="project.create",
                      target_type="project", target_id=project.id,
                      payload={"name": project.name, "slug": project.slug})
    return ApiResponse(data=out)


@router.get("/{project_id}", response_model=ApiResponse)
async def get_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取项目详情"""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    out = ProjectOut.model_validate(project)
    await _enrich_project(db, project, out)
    return ApiResponse(data=out)


@router.put("/{project_id}", response_model=ApiResponse)
async def update_project(
    project_id: str,
    req: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """更新项目"""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    update_data = req.model_dump(exclude_unset=True)
    before = {k: getattr(project, k) for k in update_data.keys()}
    for key, value in update_data.items():
        setattr(project, key, value)

    await db.commit()
    await db.refresh(project)
    out = ProjectOut.model_validate(project)
    await _enrich_project(db, project, out)
    after = {k: getattr(project, k) for k in update_data.keys()}
    await write_audit(actor=current_user, action="project.update",
                      target_type="project", target_id=project.id,
                      payload={"changes": [
                          {"field": k, "before": before.get(k), "after": after.get(k)}
                          for k in update_data.keys()
                      ]})
    return ApiResponse(data=out)


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """删除项目"""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    snapshot = {"name": project.name, "slug": project.slug, "id": project.id}
    await db.delete(project)
    await db.commit()
    await write_audit(actor=current_user, action="project.delete",
                      target_type="project", target_id=snapshot["id"],
                      payload=snapshot)
