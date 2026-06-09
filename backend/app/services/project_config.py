"""项目级配置 — 读 data/projects/{slug}/_config.yml

设计:
- 不入库, 走文件 (跟 Docusaurus 风格一致, 跟项目走)
- 字段全 Optional, 缺啥 fallback 走 Project model 字段
- Pydantic 兜底, yaml 解析失败 / 字段类型错不阻塞构建 (warning 日志, 用默认值)
- 构建时缓存 (lru_cache), 同一项目多次构建不重读
"""
import os
import logging
from functools import lru_cache
from typing import Optional

import yaml
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)

CONFIG_FILENAME = "_config.yml"


class NavConfig(BaseModel):
    """侧栏 / 顶部导航标题"""
    title: Optional[str] = None
    logo: Optional[str] = None  # URL or 相对路径


class I18nConfig(BaseModel):
    """i18n 配置 (留 C5 推迟项)"""
    default_locale: str = "zh-CN"
    locales: list[str] = Field(default_factory=lambda: ["zh-CN"])


class ThemeConfig(BaseModel):
    """主题 token 覆盖 (浅色优先)"""
    primary_color: Optional[str] = None
    font_sans: Optional[str] = None


class ProjectConfig(BaseModel):
    """项目级 _config.yml 顶层结构"""
    nav: NavConfig = Field(default_factory=NavConfig)
    i18n: I18nConfig = Field(default_factory=I18nConfig)
    theme: ThemeConfig = Field(default_factory=ThemeConfig)
    # 自定义标签 (展示在 meta / 标题)
    tagline: Optional[str] = None
    # 站点 URL (用于 SEO og:url, 不带尾斜杠)
    url: Optional[str] = None

    @field_validator("i18n", mode="before")
    @classmethod
    def _normalize_i18n(cls, v):
        if v is None:
            return {}
        if isinstance(v, dict):
            # locales 字段空走 default
            return v
        return v


def _config_path(project_slug: str, data_dir: str) -> str:
    return os.path.join(data_dir, "projects", project_slug, CONFIG_FILENAME)


@lru_cache(maxsize=128)
def _load_config_cached(project_slug: str, data_dir: str) -> ProjectConfig:
    """lru_cache 缓存 (同 slug + data_dir 不重读)"""
    path = _config_path(project_slug, data_dir)
    if not os.path.isfile(path):
        return ProjectConfig()
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        cfg = ProjectConfig.model_validate(raw)
        logger.info(f"[project_config] loaded {path} (nav.title={cfg.nav.title})")
        return cfg
    except (yaml.YAMLError, ValueError) as e:
        logger.warning(f"[project_config] {path} parse failed: {e}, using defaults")
        return ProjectConfig()
    except Exception as e:
        logger.warning(f"[project_config] {path} read failed: {e}, using defaults")
        return ProjectConfig()


def load_project_config(project_slug: str, data_dir: str) -> ProjectConfig:
    """读项目配置, 缓存 — 不存在或解析失败返默认值"""
    # 显式 type 守卫, 避免 lru_cache 收到 dict 把 cache 污染
    if not isinstance(data_dir, str):
        raise TypeError(f"data_dir must be str, got {type(data_dir).__name__}")
    return _load_config_cached(project_slug, data_dir)


def clear_cache() -> None:
    """测试用, 清缓存"""
    _load_config_cached.cache_clear()
