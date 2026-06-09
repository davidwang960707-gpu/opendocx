"""构建 Schema"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class BuildOut(BaseModel):
    id: str
    project_id: str
    version_id: str
    status: str
    output: Optional[str]
    duration: Optional[int]
    triggered_by: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
