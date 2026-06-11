"""文档资产模型"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AssetKind(str, enum.Enum):
    image = "image"
    video = "video"
    file = "file"


class DocumentAsset(Base):
    __tablename__ = "document_assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    version_id: Mapped[str] = mapped_column(String(36), ForeignKey("versions.id", ondelete="CASCADE"), nullable=False, index=True)
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(260), nullable=False)
    content_type: Mapped[str] = mapped_column(String(120), nullable=False, default="application/octet-stream")
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    kind: Mapped[AssetKind] = mapped_column(SAEnum(AssetKind), nullable=False, default=AssetKind.file)
    storage_path: Mapped[str] = mapped_column(String(800), nullable=False)
    public_path: Mapped[str] = mapped_column(String(800), nullable=False)
    uploaded_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
