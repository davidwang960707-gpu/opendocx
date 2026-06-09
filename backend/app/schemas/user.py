"""用户与认证 Schema (P1-W3-A1)"""
from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, ConfigDict, Field


class UserOut(BaseModel):
    """用户输出 (admin 列表/详情)"""
    id: str
    email: str
    name: str
    role: str  # admin / editor / viewer
    is_active: bool
    last_login_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    """创建用户 (admin) — 自动生成 12 位临时密码"""
    email: str = Field(..., min_length=3, max_length=255)
    name: str = Field(..., min_length=1, max_length=100)
    role: Literal["admin", "editor", "viewer"] = "viewer"


class UserUpdate(BaseModel):
    """更新用户 (admin) — 改 role / is_active / name"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    role: Optional[Literal["admin", "editor", "viewer"]] = None
    is_active: Optional[bool] = None


class UserCreateResponse(BaseModel):
    """建账号响应 — 包含一次性显示的临时密码 (前端用 message 显示)"""
    user: UserOut
    temporary_password: str


class UserListResponse(BaseModel):
    """用户列表 (分页)"""
    items: list[UserOut]
    total: int
    page: int
    page_size: int


class PasswordChangeRequest(BaseModel):
    """改密码 (任何人)"""
    old_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=128)


class AuditLogOut(BaseModel):
    """审计日志输出"""
    id: str
    actor_id: Optional[str] = None  # 公开操作 (feedback) 可为 None
    actor_email: str
    action: str
    target_type: Optional[str] = None
    target_id: Optional[str] = None
    payload: Optional[dict] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuditLogListResponse(BaseModel):
    items: list[AuditLogOut]
    total: int
    page: int
    page_size: int
