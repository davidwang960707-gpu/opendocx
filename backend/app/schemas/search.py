"""搜索 Schema"""
from typing import Optional
from pydantic import BaseModel


class SearchRequest(BaseModel):
    query: str
    project_id: Optional[str] = None
    limit: int = 10


class SearchResult(BaseModel):
    document_id: str
    title: str
    content_snippet: str
    score: float
    project_slug: str
    version: str
