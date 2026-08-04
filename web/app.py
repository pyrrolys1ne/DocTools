"""DocTools Web 后端（FastAPI）。

本地工具：绑定 127.0.0.1，可托管前端构建产物（``DOCTOOLS_SERVE_FRONTEND=true``）。
前后端分离部署：仅提供 /api/v1 接口，前端由独立静态站托管，配合 CORS。
交互模型是"目录路径"而非文件上传——后端直接按用户给出的路径读盘处理。
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from web.config import API_PREFIX, cors_origin_list, settings
from web.routers import explore, jobs

app = FastAPI(title="DocTools Web", description="批量文档处理本地 Web 界面")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origin_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(explore.router, prefix=API_PREFIX)
app.include_router(jobs.router, prefix=API_PREFIX)


@app.get("/api/health")
def health() -> JSONResponse:
    """健康检查（部署探测 / 运维用），返回服务信息与接口文档地址。"""
    return JSONResponse(
        {
            "status": "ok",
            "name": "DocTools API",
            "docs": "/docs",
            "openapi": "/openapi.json",
        }
    )


# 本地工具形态：后端一并托管前端构建产物，"/" 由前端接管。
# 纯 API 部署或 dist 尚未构建时，"/" 返回服务信息。
if not (settings.serve_frontend and Path(settings.frontend_dir).is_dir()):

    @app.get("/")
    def index() -> JSONResponse:
        """服务信息（未托管前端时的根路径）。"""
        return JSONResponse(
            {
                "name": "DocTools API",
                "docs": "/docs",
                "openapi": "/openapi.json",
            }
        )

if settings.serve_frontend:
    # API 路由已先注册，不会被静态挂载遮蔽
    frontend = Path(settings.frontend_dir)
    if frontend.is_dir():
        app.mount("/", StaticFiles(directory=str(frontend), html=True), name="frontend")
