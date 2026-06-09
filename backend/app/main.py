"""OpenDocX 后端入口"""
import logging
import os
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.database import engine
from app.middleware.rate_limit import RateLimitMiddleware
from app.routers import auth, projects, documents, search, build, stats, editor, feedback, users  # P1-W3-A1

settings = get_settings()
logger = logging.getLogger("opendocx")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期"""
    # 尝试启用 pgvector 扩展（独立连接，失败不影响启动）
    try:
        async with engine.begin() as conn:
            from sqlalchemy import text
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    except Exception:
        pass
    yield
    await engine.dispose()
    # 注：数据库迁移通过 alembic upgrade head 管理，不再使用 create_all


app = FastAPI(
    title="OpenDocX",
    description="AI 项目文档与发布平台 API",
    version="1.0.0",
    lifespan=lifespan,
    # /docs 留给静态站索引页 (列出所有已发布项目), swagger UI 改到 /api-doc
    docs_url="/api-doc",
    redoc_url="/api-redoc",
    openapi_url="/openapi.json",
)


# Admin R8 反馈: 主入口没有 exception_handler, 任何未处理异常都暴露为 500 给前端,
# 用户看到 'Request failed with status code 500' 完全无信息
# 这里 catch 所有未处理异常, log 详细 traceback, 返更友好 500 响应
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # HTTPException 应该走 FastAPI 默认 handler
    from fastapi import HTTPException
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail, "success": False},
        )
    logger.error(f"Unhandled exception: {type(exc).__name__}: {exc}\n{traceback.format_exc()}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "detail": f"服务器内部错误: {type(exc).__name__}: {str(exc)[:200]}",
            "error_type": type(exc).__name__,
        },
    )

# CORS - 使用配置中的允许来源
# 公开反馈 API (reader feedback) 允许 file:// / null origin, 用 allow_origin_regex
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    # file:// 协议 fetch 时 Origin header 是 "null", null origin 放行
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$|^null$",
    allow_credentials=False,  # 公开 API 不需要 credentials
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Visitor-Id"],
)

# Rate Limiting - 每 IP 每分钟 300 请求
# Admin R11 反馈: "操作过程中用户信息丢失, 重新登录显示请求过于频繁"
# 真因: Vite proxy 把所有前端 fetch 都代理到 127.0.0.1, 单 IP 60/分钟太严
# 修法: 60 → 300 (正常浏览器 mount 4 API × 5 跳 = 20, 调试 200+ 也不触)
# 仍保留健康检查 / 构建 / 搜索 reindex 白名单
app.add_middleware(RateLimitMiddleware, max_requests=300, window_seconds=60)

# 注册路由
app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(documents.router)
app.include_router(search.router)
app.include_router(build.router)
app.include_router(stats.router)
app.include_router(editor.router)
app.include_router(feedback.router)
app.include_router(users.router)  # P1-W3-A1: 用户管理 (含 /users + /auth/change-password + /audit-logs)


@app.get("/api/v1/health")
async def health():
    return {"status": "ok", "service": "opendocx-backend"}


# 静态文件服务 — 构建产物预览
# /docs 根：自定义索引页（列出所有已发布项目 + 版本）
# /docs/{slug}/{ver}/... : 静态文件（由 build_service 生成的 HTML）
builds_path = os.path.join(settings.data_dir, "builds")
os.makedirs(builds_path, exist_ok=True)


def _scan_builds() -> list[dict]:
    """扫描 data/builds/ 返回已发布项目列表"""
    import time
    out = []
    if not os.path.isdir(builds_path):
        return out
    for slug in sorted(os.listdir(builds_path)):
        slug_dir = os.path.join(builds_path, slug)
        if not os.path.isdir(slug_dir):
            continue
        for ver in sorted(os.listdir(slug_dir)):
            ver_dir = os.path.join(slug_dir, ver)
            if not os.path.isdir(ver_dir):
                continue
            # 找最新的 HTML 修改时间
            mtime = 0
            doc_count = 0
            for fn in os.listdir(ver_dir):
                if fn.endswith(".html"):
                    doc_count += 1
                    fp = os.path.join(ver_dir, fn)
                    mtime = max(mtime, os.path.getmtime(fp))
            out.append({
                "slug": slug,
                "version": ver,
                "url": f"/docs/{slug}/{ver}/index.html",
                "doc_count": doc_count,
                "mtime": mtime,
                "mtime_iso": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mtime)) if mtime else "—",
            })
    # 最新构建在前
    out.sort(key=lambda x: x["mtime"], reverse=True)
    return out


_INDEX_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>OpenDocX — 已发布站点</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "PingFang SC", sans-serif; color: #1d1d1f; background: #fbfbfd; line-height: 1.6; }}
.wrap {{ max-width: 860px; margin: 0 auto; padding: 80px 32px; }}
h1 {{ font-size: 48px; font-weight: 700; letter-spacing: -1px; margin-bottom: 8px; }}
.sub {{ color: #6e6e73; font-size: 17px; margin-bottom: 48px; }}
.list {{ display: grid; gap: 16px; }}
.card {{ background: #fff; border: 1px solid #e5e5ea; border-radius: 12px; padding: 24px 28px; display: flex; align-items: center; justify-content: space-between; transition: transform 0.15s, box-shadow 0.15s; text-decoration: none; color: inherit; }}
.card:hover {{ transform: translateY(-1px); box-shadow: 0 8px 24px rgba(0,0,0,.06); }}
.left {{ flex: 1; }}
.title {{ font-size: 19px; font-weight: 600; margin-bottom: 4px; }}
.meta {{ color: #6e6e73; font-size: 13px; }}
.badge {{ display: inline-block; padding: 2px 8px; background: #f5f5f7; border-radius: 4px; font-size: 12px; margin-left: 8px; color: #424245; }}
.arrow {{ color: #86868b; font-size: 24px; padding-left: 24px; }}
.empty {{ text-align: center; padding: 80px 0; color: #86868b; }}
.empty h2 {{ font-size: 22px; color: #424245; margin-bottom: 8px; }}
</style>
</head>
<body>
<div class="wrap">
  <h1>已发布站点</h1>
  <p class="sub">由 OpenDocX 生成 · 共 {count} 个站点</p>
  {body}
</div>
</body>
</html>"""


@app.get("/docs", response_class=HTMLResponse)
@app.get("/docs/", response_class=HTMLResponse)
async def docs_index():
    """已发布站点目录页 — 替代原先 404 的根"""
    items = _scan_builds()
    if not items:
        body = '''<div class="empty">
            <h2>还没有发布的站点</h2>
            <p>请在 OpenDocX 管理后台编辑文档后点击"构建"按钮</p>
            <p style="margin-top:16px"><a href="/" style="color:#0071e3;text-decoration:none">前往管理后台 →</a></p>
        </div>'''
    else:
        cards = []
        for it in items:
            cards.append(f'''
            <a class="card" href="{it["url"]}">
                <div class="left">
                    <div class="title">{it["slug"]} <span class="badge">{it["version"]}</span></div>
                    <div class="meta">{it["doc_count"]} 篇文档 · 构建于 {it["mtime_iso"]}</div>
                </div>
                <div class="arrow">→</div>
            </a>''')
        body = f'<div class="list">{"".join(cards)}</div>'
    return _INDEX_HTML.format(count=len(items), body=body)


# 子路径静态文件（必须放在 /docs 索引之后，否则 mount 会抢走 / 路径）
app.mount("/docs", StaticFiles(directory=builds_path, html=True), name="docs")
