"""项目与版本 Schema"""
from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, ConfigDict


class ProjectCreate(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None
    brand_color: str = "#4F46E5"


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    brand_color: Optional[str] = None
    logo_url: Optional[str] = None
    status: Optional[Literal["active", "paused", "draft", "archived"]] = None  # P1-W2-P2


class ProjectOut(BaseModel):
    id: str
    name: str
    slug: str
    description: Optional[str]
    brand_color: str
    logo_url: Optional[str]
    created_by: str
    created_at: datetime
    updated_at: datetime
    # P1-UI-2: 从默认版本推导 (active/paused/draft)，后端不存这个字段
    status: Optional[str] = None
    # P1-UI-1: 默认版本的 id，前端 Dashboard 用
    default_version_id: Optional[str] = None
    # P1-UI-2: 文档数（从 version + documents 聚合）
    doc_count: Optional[int] = None
    # P1-UI-1: 最近更新时间（从版本/文档）
    last_activity_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class VersionCreate(BaseModel):
    version: str
    is_default: bool = False


class VersionOut(BaseModel):
    id: str
    project_id: str
    version: str
    is_default: bool
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
