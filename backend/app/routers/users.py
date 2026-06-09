"""用户管理路由 (P1-W3-A1) — admin 才能管理

端点:
  GET    /api/v1/users                 (admin)  列表+分页+搜索
  GET    /api/v1/users/{id}            (admin)  详情
  POST   /api/v1/users                 (admin)  建账号 (自动 12 位临时密码)
  PATCH  /api/v1/users/{id}            (admin)  改 role/is_active/name
  DELETE /api/v1/users/{id}            (admin)  软删 (is_active=false)
  POST   /api/v1/auth/change-password  (任何人)  改自己密码
"""
import secrets
import string
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.database import get_db
from app.models import User, AuditLog
from app.models.user import UserRole
from app.schemas.user import (
    UserOut, UserCreate, UserUpdate, UserCreateResponse, UserListResponse,
    PasswordChangeRequest, AuditLogOut, AuditLogListResponse,
)
from app.schemas import ApiResponse
from app.utils.auth import get_current_user, require_role, verify_password, hash_password
from app.utils.audit import write_audit

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["用户管理"])


def _gen_temp_password(length: int = 12) -> str:
    """生成 12 位临时密码: 字母 (大小写) + 数字"""
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


# ── /users 端点 ──

@router.get("/users", response_model=ApiResponse)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """用户列表 (admin)"""
    query = select(User)
    count_q = select(func.count(User.id))

    if search:
        s = f"%{search.lower()}%"
        cond = or_(func.lower(User.email).like(s), func.lower(User.name).like(s))
        query = query.where(cond)
        count_q = count_q.where(cond)
    if role:
        query = query.where(User.role == UserRole(role))
        count_q = count_q.where(User.role == UserRole(role))
    if is_active is not None:
        query = query.where(User.is_active == is_active)
        count_q = count_q.where(User.is_active == is_active)

    total = (await db.execute(count_q)).scalar() or 0
    query = query.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    users = (await db.execute(query)).scalars().all()

    return ApiResponse(data=UserListResponse(
        items=[UserOut.model_validate(u) for u in users],
        total=total, page=page, page_size=page_size,
    ))


@router.get("/users/{user_id}", response_model=ApiResponse)
async def get_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    r = await db.execute(select(User).where(User.id == user_id))
    u = r.scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=404, detail="用户不存在")
    return ApiResponse(data=UserOut.model_validate(u))


@router.post("/users", response_model=ApiResponse, status_code=201)
async def create_user(
    req: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """建账号 — 自动生成 12 位临时密码"""
    existing = await db.execute(select(User).where(User.email == req.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="邮箱已存在")

    temp_pwd = _gen_temp_password(12)
    user = User(
        email=req.email,
        name=req.name,
        password_hash=hash_password(temp_pwd),
        role=UserRole(req.role),
        is_active=True,
    )
    db.add(user)
    await db.flush()

    await write_audit(current_user, "user.create",
        target_type="user", target_id=user.id,
        payload={"email": user.email, "role": user.role.value},
    )
    await db.commit()
    await db.refresh(user)

    return ApiResponse(data=UserCreateResponse(
        user=UserOut.model_validate(user),
        temporary_password=temp_pwd,
    ))


@router.patch("/users/{user_id}", response_model=ApiResponse)
async def update_user(
    user_id: str,
    req: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    r = await db.execute(select(User).where(User.id == user_id))
    u = r.scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=404, detail="用户不存在")

    payload_before = {"name": u.name, "role": u.role.value, "is_active": u.is_active}
    update_data = req.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if key == "role":
            u.role = UserRole(value)
        else:
            setattr(u, key, value)
    await db.flush()

    payload_after = {"name": u.name, "role": u.role.value, "is_active": u.is_active}
    await write_audit(current_user, "user.update",
        target_type="user", target_id=u.id,
        payload={"before": payload_before, "after": payload_after, "diff": update_data},
    )
    await db.commit()
    await db.refresh(u)
    return ApiResponse(data=UserOut.model_validate(u))


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """软删 — 设 is_active=false (保留审计)"""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="不能禁用自己的账号")
    r = await db.execute(select(User).where(User.id == user_id))
    u = r.scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=404, detail="用户不存在")

    u.is_active = False
    await db.flush()
    await write_audit(current_user, "user.delete",
        target_type="user", target_id=u.id,
        payload={"email": u.email, "soft_delete": True},
    )
    await db.commit()
    return None


# ── /auth/change-password (任何人可调) ──

@router.post("/auth/change-password", response_model=ApiResponse)
async def change_password(
    req: PasswordChangeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """改自己密码 (editor/viewer/admin 都能调)"""
    if not verify_password(req.old_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="旧密码错误")
    if req.old_password == req.new_password:
        raise HTTPException(status_code=400, detail="新密码不能跟旧密码相同")

    current_user.password_hash = hash_password(req.new_password)
    await db.flush()
    await write_audit(current_user, "user.change_password",
        target_type="user", target_id=current_user.id,
    )
    await db.commit()
    return ApiResponse(data={"ok": True})


# ── /audit-logs (admin) ──

@router.get("/audit-logs", response_model=ApiResponse)
async def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    actor_id: Optional[str] = None,
    actor_email: Optional[str] = None,
    action: Optional[str] = None,
    target_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """审计日志查询 (admin)"""
    query = select(AuditLog)
    count_q = select(func.count(AuditLog.id))
    if actor_id:
        query = query.where(AuditLog.actor_id == actor_id)
        count_q = count_q.where(AuditLog.actor_id == actor_id)
    if actor_email:
        actor_email_like = f"%{actor_email}%"
        query = query.where(AuditLog.actor_email.ilike(actor_email_like))
        count_q = count_q.where(AuditLog.actor_email.ilike(actor_email_like))
    if action:
        query = query.where(AuditLog.action == action)
        count_q = count_q.where(AuditLog.action == action)
    if target_type:
        query = query.where(AuditLog.target_type == target_type)
        count_q = count_q.where(AuditLog.target_type == target_type)

    total = (await db.execute(count_q)).scalar() or 0
    query = query.order_by(AuditLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    logs = (await db.execute(query)).scalars().all()

    return ApiResponse(data=AuditLogListResponse(
        items=[AuditLogOut.model_validate(l) for l in logs],
        total=total, page=page, page_size=page_size,
    ))
