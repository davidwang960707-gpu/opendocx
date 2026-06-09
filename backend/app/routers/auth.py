"""认证路由 (P1-W3-A1: 登录写 last_login_at + 校验 is_active; P1-W3-A3: PATCH /me 改 name)"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.user import User
from app.schemas import LoginRequest, LoginResponse, ApiResponse
from app.schemas.user import UserOut as UserOutFull  # 8 字段完整版
from app.utils.auth import verify_password, create_access_token, get_current_user
from app.utils.audit import write_audit

router = APIRouter(prefix="/api/v1/auth", tags=["认证"])


# P1-W3-A3: PATCH /me 改自己 — 只允许 name, role/is_active 是 admin 管辖
class UpdateMeRequest(BaseModel):
    name: str | None = None


@router.post("/login", response_model=ApiResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    """用户登录 (P1-W3-A1: 校验 is_active, 写 last_login_at)"""
    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="邮箱或密码错误")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被禁用")

    # P1-W3-A1: 写最后登录时间
    user.last_login_at = datetime.utcnow()
    await db.commit()

    token = create_access_token({"sub": user.id, "role": user.role.value})
    return ApiResponse(data={"access_token": token, "token_type": "bearer"})


@router.get("/me", response_model=ApiResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """获取当前用户信息 (P1-W3-A1: 返完整 8 字段含 is_active/last_login_at)"""
    return ApiResponse(data=UserOutFull.model_validate(current_user))


@router.patch("/me", response_model=ApiResponse)
async def update_me(
    req: UpdateMeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """修改自己的姓名 (P1-W3-A3)

    只允许改 name, role/is_active 由 admin 在 /admin/users 改
    写 audit log (action=user.update 但 actor=自己, 不在 /admin/users 列表显示)
    """
    if req.name is None:
        return ApiResponse(data=UserOutFull.model_validate(current_user))
    new_name = req.name.strip()
    if not new_name:
        raise HTTPException(status_code=400, detail="姓名不能为空")
    if len(new_name) > 50:
        raise HTTPException(status_code=400, detail="姓名最长 50 字符")

    before = current_user.name
    current_user.name = new_name
    await db.commit()
    await db.refresh(current_user)

    await write_audit(
        actor=current_user, action="user.update_self",
        target_type="user", target_id=str(current_user.id),
        payload={"field": "name", "before": before, "after": new_name},
    )
    return ApiResponse(data=UserOutFull.model_validate(current_user))
