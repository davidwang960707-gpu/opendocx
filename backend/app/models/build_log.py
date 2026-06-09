"""构建日志模型"""
import uuid
from datetime import datetime
from sqlalchemy import String, Text, Integer, Enum as SAEnum, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base
from typing import Optional
import enum


class BuildStatus(str, enum.Enum):
    pending = "pending"
    building = "building"
    success = "success"
    failed = "failed"


class BuildLog(Base):
    __tablename__ = "build_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    version_id: Mapped[str] = mapped_column(String(36), ForeignKey("versions.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[BuildStatus] = mapped_column(SAEnum(BuildStatus), default=BuildStatus.pending)
    output: Mapped[Optional[str]] = mapped_column(Text)
    duration: Mapped[Optional[int]] = mapped_column(Integer)
    triggered_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
