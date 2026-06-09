"""JWT 认证工具"""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models.user import User

settings = get_settings()
# auto_error=False：未提供 token 时不要让 HTTPBearer 抢跑抛 403，
# 我们自己在下面抛 401（语义更准确：无凭据=401，有凭据但权限不足=403）
security = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    """使用 PBKDF2-SHA256 哈希密码（兼容性好）"""
    salt = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
    return f"pbkdf2:sha256:100000${salt}${h.hex()}"


def verify_password(plain: str, hashed: str) -> bool:
    """验证密码"""
    try:
        parts = hashed.split("$")
        salt = parts[1]
        h = hashlib.pbkdf2_hmac('sha256', plain.encode(), salt.encode(), 100000)
        return h.hex() == parts[2]
    except Exception:
        return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(hours=24))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm="HS256")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """FastAPI 依赖：解析 JWT 获取当前用户"""
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未提供 Token")
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=["HS256"])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的 Token")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的 Token")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")
    return user


def require_role(*roles: str):
    """角色守卫"""
    async def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role.value not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="权限不足")
        return current_user
    return role_checker
