"""用户模型"""
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Enum as SAEnum, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base
import enum


class UserRole(str, enum.Enum):
    admin = "admin"
    editor = "editor"
    viewer = "viewer"


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole), default=UserRole.viewer)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False, server_default="true")  # P1-W3-A1: 软删标志 (禁用)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)  # P1-W3-A1: 最后活跃时间
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
