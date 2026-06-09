"""请求频率限制中间件"""
import os
import time
from collections import defaultdict
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class RateLimitMiddleware(BaseHTTPMiddleware):
    """滑动窗口频率限制（内存实现）"""

    def __init__(self, app, max_requests: int = 60, window_seconds: int = 60):
        super().__init__(app)
        # 测试环境自动禁用：env DISABLE_RATE_LIMIT=1
        self.enabled = os.environ.get("DISABLE_RATE_LIMIT") != "1"
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next) -> Response:
        # 每次请求都读 env（支持测试动态启用/禁用）
        if os.environ.get("DISABLE_RATE_LIMIT") == "1":
            return await call_next(request)
        # 健康检查和构建不限流
        if request.url.path in ("/api/v1/health",) or request.url.path.startswith("/api/v1/build") or request.url.path.startswith("/api/v1/search/reindex"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        window_start = now - self.window_seconds

        # 清理过期记录
        self.requests[client_ip] = [
            t for t in self.requests[client_ip] if t > window_start
        ]

        if len(self.requests[client_ip]) >= self.max_requests:
            return JSONResponse(
                status_code=429,
                content={"error": {"code": 429, "message": "请求过于频繁，请稍后再试"}},
                headers={"Retry-After": str(self.window_seconds)},
            )

        self.requests[client_ip].append(now)
        return await call_next(request)
