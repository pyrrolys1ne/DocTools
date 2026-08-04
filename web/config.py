"""DocTools Web 后端配置。

环境变量前缀 ``DOCTOOLS_``，支持 ``.env`` 文件。例如：
``DOCTOOLS_HOST=0.0.0.0``、``DOCTOOLS_SERVE_FRONTEND=false``。
"""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# 所有接口统一挂在版本前缀下，演进时可在其后增加 /v2 等。
API_PREFIX = "/api/v1"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="DOCTOOLS_",
        env_file=".env",
        extra="ignore",
    )

    host: str = "127.0.0.1"
    port: int = 8000
    reload: bool = True

    # 本地工具默认由后端一并托管前端构建产物；
    # 前后端分离部署时置 False（前端由独立静态站 / 对象存储提供）。
    serve_frontend: bool = True
    frontend_dir: str = str(Path(__file__).resolve().parent.parent / "frontend" / "dist")

    # 前后端分离部署时允许的跨域来源（逗号分隔）。
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"


settings = Settings()


def cors_origin_list() -> list[str]:
    """把逗号分隔的 CORS 配置解析成列表（空配置返回空列表）。"""
    return [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
