"""资产 Schema"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AssetOut(BaseModel):
    id: str
    version_id: str
    original_filename: str
    stored_filename: str
    content_type: str
    size_bytes: int
    kind: str
    public_path: str
    file_url: str
    markdown: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
