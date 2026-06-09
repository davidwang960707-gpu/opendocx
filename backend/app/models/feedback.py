"""文档反馈模型 — 点赞/点踩/收藏/评论 统一存储"""
import uuid
from datetime import datetime
from sqlalchemy import String, Text, Integer, Enum as SAEnum, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base
import enum


class FeedbackKind(str, enum.Enum):
    like = "like"
    dislike = "dislike"
    bookmark = "bookmark"
    comment = "comment"


class DocumentFeedback(Base):
    """读者反馈 / 评论表

    - kind=like/dislike/bookmark: 一行算一次 (visitor_id 维度), 同一人切换会更新
    - kind=comment: parent_id 字段支持嵌套回复, body 必填
    """
    __tablename__ = "document_feedbacks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[FeedbackKind] = mapped_column(
        SAEnum(FeedbackKind, name='feedback_kind'),
        nullable=False,
        index=True,
    )
    # 匿名访客: 用浏览器 uuid 保存在 localStorage; 注册用户可填 user_id
    visitor_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"))
    user_name: Mapped[str | None] = mapped_column(String(100))  # 评论时填的署名, 没登录就手填
    body: Mapped[str | None] = mapped_column(Text)  # only for kind=comment
    parent_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("document_feedbacks.id", ondelete="CASCADE")
    )
    # 点赞/点踩的计数 (冗余字段, 减少 COUNT 查询; 反应 kind 切换时原值-1, 新值+1)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
