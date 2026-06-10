"""文档 Schema"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class DocumentCreate(BaseModel):
    title: str
    slug: str
    content: Optional[str] = None
    parent_id: Optional[str] = None
    sort_order: int = 0


class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    slug: Optional[str] = None
    content: Optional[str] = None
    status: Optional[str] = None
    parent_id: Optional[str] = None
    sort_order: Optional[int] = None
    # 编辑器打开时拿到的文档版本号。保存正文时带回, 后端用它防止覆盖别人刚保存的内容。
    base_revision: Optional[int] = None


class DocumentOut(BaseModel):
    id: str
    version_id: str
    parent_id: Optional[str]
    title: str
    slug: str
    content: Optional[str]
    revision: int
    file_path: Optional[str]
    status: str
    sort_order: int
    created_by: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentTreeOut(BaseModel):
    id: str
    title: str
    slug: str
    status: str
    sort_order: int
    is_folder: bool = False  # 计算字段: content 为空 + 有子节点 (folder-only doc)
    # R7 反馈: list 端点暴露 content 体积而非全文 (省带宽 + 排查"导入是否真存上")
    content_len: int = 0
    has_content: bool = False
    children: list["DocumentTreeOut"] = []

    model_config = ConfigDict(from_attributes=True)


# R6 反馈 5: 拖拽排序 — 客户端把整棵树的新位置打平发上来
class ReorderItem(BaseModel):
    id: str
    parent_id: Optional[str] = None
    sort_order: int


class ReorderRequest(BaseModel):
    version_id: str
    items: list[ReorderItem]
