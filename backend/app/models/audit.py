"""审计日志模型 (P1-W3-A1)

记录管理操作 (project create/update/delete, user create/update/delete,
doc create/update/delete, version create/delete, feedback delete) —
用于 admin 排查 "谁在什么时间改了什么"。
"""
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, JSON, func
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    actor_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)  # 公开操作 (feedback) 可为 None
    actor_email: Mapped[str] = mapped_column(String(255), nullable=False)  # 冗余存 (删 user 后审计仍可读)
    action: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # 动作: user.create / user.update / user.delete / project.create / project.update / project.delete /
    #       doc.create / doc.update / doc.delete / version.create / version.delete / feedback.delete
    target_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)  # 目标实体类型
    target_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)  # 目标实体 id
    payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # 操作的 payload (e.g. 改前/改后 diff)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
