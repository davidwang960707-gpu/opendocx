"""版本模型"""
import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, Enum as SAEnum, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base
import enum


class VersionStatus(str, enum.Enum):
    draft = "draft"
    published = "published"
    archived = "archived"


class Version(Base):
    __tablename__ = "versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[VersionStatus] = mapped_column(SAEnum(VersionStatus), default=VersionStatus.draft)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    project = relationship("Project", back_populates="versions")
    documents = relationship("Document", back_populates="version", cascade="all, delete-orphan")
