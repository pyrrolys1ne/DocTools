"""PyInstaller 打包入口：启动无头本地 API 服务（复用 web/__main__.main）。"""

# 显式导入 web.app，让 PyInstaller 静态分析把整个 FastAPI 应用打进包；
# uvicorn 通过字符串 "web.app:app" 在运行时导入，静态分析发现不了。
import web.app  # noqa: F401
from web.__main__ import main

if __name__ == "__main__":
    main()
