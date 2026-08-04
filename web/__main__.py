"""``python -m web`` 启动本地服务（配置见 web/config.py，环境变量前缀 DOCTOOLS_）。"""

from __future__ import annotations

import uvicorn

from web.config import settings


def main() -> None:
    uvicorn.run(
        "web.app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
    )


if __name__ == "__main__":
    main()
