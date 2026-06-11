"""Pydantic Schemas — 请求/响应模型

按业务域拆分子模块（auth / project / document / search / build / common），
本文件仅做 re-export 以保持路由层 `from app.schemas import X` 的接口稳定。
"""
from app.schemas.common import ApiResponse, PaginatedMeta, ErrorResponse
from app.schemas.auth import LoginRequest, LoginResponse, UserOut
from app.schemas.project import (
    ProjectCreate, ProjectUpdate, ProjectOut,
    VersionCreate, VersionOut,
)
from app.schemas.document import (
    DocumentCreate, DocumentUpdate, DocumentOut, DocumentTreeOut,
    ReorderRequest, ReorderItem,
)
from app.schemas.asset import AssetOut
from app.schemas.search import SearchRequest, SearchResult
from app.schemas.build import BuildOut
from app.schemas.feedback import FeedbackCreate, CommentOut, FeedbackReactionOut, CommentsListOut

__all__ = [
    # common
    "ApiResponse", "PaginatedMeta", "ErrorResponse",
    # auth
    "LoginRequest", "LoginResponse", "UserOut",
    # project
    "ProjectCreate", "ProjectUpdate", "ProjectOut",
    "VersionCreate", "VersionOut",
    # document
    "DocumentCreate", "DocumentUpdate", "DocumentOut", "DocumentTreeOut",
    "ReorderRequest", "ReorderItem",
    "AssetOut",
    # search
    "SearchRequest", "SearchResult",
    # build
    "BuildOut",
    # feedback
    "FeedbackCreate", "CommentOut", "FeedbackReactionOut", "CommentsListOut",
]
