"""OpenDocX backend config"""
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List
import os


DEFAULT_DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "data"))


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://opendocx:opendocx@localhost:5432/opendocx"

    # Redis
    redis_url: str = "redis://localhost:6380"

    # Security
    secret_key: str = "opendocx-secret-key-change-in-production"
    jwt_secret_key: str = "opendocx-jwt-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440

    # CORS
    cors_origins: str = "http://localhost:3077,http://localhost:8001"

    # Data directory
    data_dir: str = DEFAULT_DATA_DIR

    # Embedding
    embedding_model: str = "BAAI/bge-m3"
    embedding_device: str = "cpu"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache()
def get_settings() -> Settings:
    return Settings()
