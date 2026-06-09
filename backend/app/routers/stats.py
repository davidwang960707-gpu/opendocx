"""仪表盘统计路由 — P1-段1 W1 D-1 扩字段 (Admin 4 紧凑数据点 + 7d 趋势)"""
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import Project, Document, User, BuildLog
from app.schemas import ApiResponse
from app.utils.auth import get_current_user

router = APIRouter(prefix="/api/v1/stats", tags=["统计"])


def _utc_now() -> datetime:
    """UTC 当前时间 (避免 PG tz aware 报错)"""
    return datetime.now(timezone.utc).replace(tzinfo=None)


@router.get("", response_model=ApiResponse)
async def get_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """仪表盘统计数据 — P1-段1 W1 D-1 扩 4 字段 + 7d 趋势

    字段 (Admin P1 段 1 §1.2 设计):
      project_count       — 项目总数
      document_count      — 文档总数
      published_count     — 已发布
      today_builds        — 今日构建数
      today_doc_updates   — 今日文档更新
      pending_drafts      — 草稿待审
      online_editors      — 在线编辑者 (mock: 1 = Admin)
      trend_7d            — 7d 折线趋势: {projects, docs, builds} 各 7 元素
    """
    # === 1. 基础 3 字段 (1.0 保留) ===
    project_count = (await db.execute(select(func.count(Project.id)))).scalar() or 0
    doc_count = (await db.execute(select(func.count(Document.id)))).scalar() or 0
    published_count = (
        await db.execute(
            select(func.count(Document.id)).where(Document.status == "published")
        )
    ).scalar() or 0

    # === 2. Admin 4 紧凑数据点 (新加) ===
    today_start = _utc_now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_builds = (
        await db.execute(
            select(func.count(BuildLog.id)).where(BuildLog.created_at >= today_start)
        )
    ).scalar() or 0

    today_doc_updates = (
        await db.execute(
            select(func.count(Document.id)).where(Document.updated_at >= today_start)
        )
    ).scalar() or 0

    pending_drafts = (
        await db.execute(
            select(func.count(Document.id)).where(Document.status == "draft")
        )
    ).scalar() or 0

    # online_editors: P1 段 1 mock 返 1 (Admin), 真 WebSocket 推 P2
    online_editors = 1

    # === 3. 7d 趋势 (新加, D-2 sparkline 数据源) ===
    seven_days_ago = today_start - timedelta(days=6)
    trend_projects: list[int] = []
    trend_docs: list[int] = []
    trend_builds: list[int] = []
    for i in range(7):
        day_start = seven_days_ago + timedelta(days=i)
        day_end = day_start + timedelta(days=1)
        # 项目累计: 当日创建数 (但 sparkline 看趋势, 用每日新增)
        p_today = (
            await db.execute(
                select(func.count(Project.id)).where(
                    and_(Project.created_at >= day_start, Project.created_at < day_end)
                )
            )
        ).scalar() or 0
        d_today = (
            await db.execute(
                select(func.count(Document.id)).where(
                    and_(Document.created_at >= day_start, Document.created_at < day_end)
                )
            )
        ).scalar() or 0
        b_today = (
            await db.execute(
                select(func.count(BuildLog.id)).where(
                    and_(BuildLog.created_at >= day_start, BuildLog.created_at < day_end)
                )
            )
        ).scalar() or 0
        trend_projects.append(p_today)
        trend_docs.append(d_today)
        trend_builds.append(b_today)

    return ApiResponse(data={
        # 1.0 基础 3 字段 (保留, 不破坏现有调用)
        "project_count": project_count,
        "document_count": doc_count,
        "published_count": published_count,
        # Admin P1 段 1 §1.2 4 紧凑数据点
        "today_builds": today_builds,
        "today_doc_updates": today_doc_updates,
        "pending_drafts": pending_drafts,
        "online_editors": online_editors,
        # Admin P1 段 1 §1.3 趋势 sparkline 数据源 (3 维度)
        "trend_7d": {
            "projects": trend_projects,
            "docs": trend_docs,
            "builds": trend_builds,
        },
    })
