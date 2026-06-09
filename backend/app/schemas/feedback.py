"""反馈 / 评论 Schema"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


class FeedbackCreate(BaseModel):
    """创建反馈 (like/dislike/bookmark/comment)"""
    document_id: str
    version_id: str
    kind: str = Field(..., description="like | dislike | bookmark | comment")
    body: Optional[str] = Field(None, description="评论内容, kind=comment 时必填")
    user_name: Optional[str] = Field(None, description="署名 (匿名时手填)")
    parent_id: Optional[str] = Field(None, description="回复某条评论的 id")


class CommentOut(BaseModel):
    """单条评论 (含回复) 的输出"""
    id: str
    document_id: str
    parent_id: Optional[str] = None
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    body: Optional[str] = None
    created_at: datetime
    replies: List["CommentOut"] = []

    model_config = ConfigDict(from_attributes=True)


class FeedbackReactionOut(BaseModel):
    """某个 doc 的 like/dislike/bookmark 汇总 + 当前用户的状态"""
    like_count: int
    dislike_count: int
    bookmark_count: int
    my_reaction: Optional[str] = None  # 'like' | 'dislike' | 'bookmark' | None
    my_reaction_id: Optional[str] = None  # 当前访客 reaction 的 id (用于 toggle DELETE)


class CommentsListOut(BaseModel):
    """某 doc 的评论列表 (按 created_at 升序)"""
    items: List[CommentOut]
    total: int
