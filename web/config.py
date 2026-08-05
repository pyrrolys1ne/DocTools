"""DocTools Web 后端配置。

环境变量前缀 ``DOCTOOLS_``，支持 ``.env`` 文件。例如：
``DOCTOOLS_HOST=0.0.0.0``、``DOCTOOLS_PORT=9000``、``DOCTOOLS_RELOAD=true``。
"""

from __future__ import annotations

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
    # 打包后的桌面客户端以子进程方式拉起本服务，必须关闭 reload；
    # 个人开发调试时可用 DOCTOOLS_RELOAD=true 开启热重载。
    reload: bool = False

    # 开发调试时浏览器跨域访问 API 的来源（逗号分隔）；桌面客户端不走 CORS。
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"


settings = Settings()


def cors_origin_list() -> list[str]:
    """把逗号分隔的 CORS 配置解析成列表（空配置返回空列表）。"""
    return [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
