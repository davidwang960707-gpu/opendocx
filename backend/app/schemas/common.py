"""通用 Pydantic 响应包装"""
from typing import Optional
from pydantic import BaseModel


class ApiResponse(BaseModel):
    success: bool = True
    data: object = None
    meta: Optional[dict] = None


class PaginatedMeta(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int


class ErrorResponse(BaseModel):
    success: bool = False
    error: dict
